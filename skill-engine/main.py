import base64, json, os, re
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from skill_gen import generate_skill_spec
from agent_binder import register_tool
from firestore_client import save_skill, save_order, db

app = FastAPI(title="Dangnai Skill Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "project-9ed97ef0-254a-4ec3-975")
VERTEX_LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")


# ── 요청 모델 ────────────────────────────────────────────

class SkillRequest(BaseModel):
    store_id: str
    owner_input: str

class OrderRequest(BaseModel):
    store_id: str
    skill_name: str
    parameters: dict = {}

class ChatRequest(BaseModel):
    store_id: str
    text: str
    session_id: Optional[str] = "default"

class ExtractMenuRequest(BaseModel):
    store_id: str
    image_base64: str
    mime_type: str = "image/jpeg"


# ── 헬스체크 ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── 스킬 생성 ────────────────────────────────────────────

@app.post("/create-skill")
async def create_skill(req: SkillRequest):
    spec = generate_skill_spec(req.owner_input, req.store_id)
    register_tool(spec)  # 유효성 검사
    save_skill(req.store_id, spec)
    return {"status": "success", "skill": spec["tool_name"]}


# ── 주문 처리 ─────────────────────────────────────────────

@app.post("/order")
async def place_order(req: OrderRequest):
    order_id = save_order(req.store_id, req.skill_name, req.parameters)
    if WEBHOOK_URL:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{WEBHOOK_URL}/handle",
                params={"store_id": req.store_id},
                json={"skill_name": req.skill_name, "parameters": req.parameters},
                timeout=10.0,
            )
            if r.status_code != 200:
                raise HTTPException(502, f"Webhook error: {r.text}")
    return {"status": "success", "order_id": order_id}


# ── TV 대화 (Gemini Function Calling) ────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Firestore에서 등록된 스킬을 로드 →
    Gemini Function Calling으로 인텐트 파악 →
    해당 스킬의 webhook_url 직접 호출.
    """
    import vertexai
    from vertexai.generative_models import (
        FunctionDeclaration,
        GenerativeModel,
        Tool,
    )

    vertexai.init(project=PROJECT_ID, location=VERTEX_LOCATION)

    # Firestore에서 가게 정보 + 등록된 스킬 로드
    store_doc = db.collection("stores").document(req.store_id).get()
    store = store_doc.to_dict() if store_doc.exists else {}
    skills = store.get("skills", [])

    # 스킬 → Gemini FunctionDeclaration 변환 (examples를 description에 포함)
    declarations = []
    for skill in skills:
        examples = skill.get("examples", [])
        desc = skill["description"]
        if examples:
            desc += f"\n사용 예시: {' / '.join(examples)}"
        declarations.append(
            FunctionDeclaration(
                name=skill["tool_name"],
                description=desc,
                parameters=skill.get(
                    "parameters",
                    {"type": "object", "properties": {}},
                ),
            )
        )

    # response_template 맵 (function call 후 응답 생성에 사용)
    response_templates = {
        s["tool_name"]: s.get("response_template", "")
        for s in skills
    }

    model = GenerativeModel(
        "gemini-2.5-flash-lite",
        system_instruction=(
            f"당신은 {store.get('name', '당그나이TV')} TV 주문 어시스턴트입니다. "
            "사용자의 말을 파악하고 적절한 서비스를 연결하세요. "
            "응답은 항상 2문장 이내로 간결하게 유지하세요."
        ),
        tools=[Tool(function_declarations=declarations)] if declarations else [],
    )

    response = model.generate_content(req.text)
    part = response.candidates[0].content.parts[0]

    # Function Calling 응답
    if hasattr(part, "function_call") and part.function_call.name:
        fc = part.function_call
        skill_meta = next(
            (s for s in skills if s["tool_name"] == fc.name), None
        )
        webhook_target = (
            skill_meta.get("webhook_url") if skill_meta else None
        ) or (f"{WEBHOOK_URL}/handle" if WEBHOOK_URL else None)

        if webhook_target:
            async with httpx.AsyncClient() as client:
                await client.post(
                    webhook_target,
                    params={"store_id": req.store_id},
                    json={
                        "skill_name": fc.name,
                        "parameters": dict(fc.args),
                    },
                    timeout=10.0,
                )

        # response_template에 파라미터 채워서 응답 생성
        template = response_templates.get(fc.name, "")
        try:
            reply = template.format(**dict(fc.args)) if template else f"{fc.name} 서비스를 연결했어요!"
        except KeyError:
            reply = template or f"{fc.name} 서비스를 연결했어요!"

        return {
            "reply": reply,
            "action": fc.name,
            "parameters": dict(fc.args),
        }

    # 일반 텍스트 응답
    return {
        "reply": part.text if hasattr(part, "text") else "죄송해요, 다시 말씀해주세요.",
        "action": None,
        "parameters": {},
    }


# ── 메뉴판 이미지 → 메뉴 자동 추출 ─────────────────────

@app.post("/extract-menu")
async def extract_menu(req: ExtractMenuRequest):
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part

    vertexai.init(project=PROJECT_ID, location=VERTEX_LOCATION)
    model = GenerativeModel("gemini-2.0-flash")
    image_part = Part.from_data(
        base64.b64decode(req.image_base64), mime_type=req.mime_type
    )
    response = model.generate_content(
        [
            image_part,
            "이 메뉴판에서 메뉴명과 가격을 추출해 JSON 배열로만 반환하세요. "
            '형식: [{"name": "메뉴명", "price": 가격숫자}]',
        ]
    )
    raw = response.text.strip()
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    menus = json.loads(match.group()) if match else json.loads(raw)
    db.collection("stores").document(req.store_id).update({"menus": menus})
    return {"menus": menus}
