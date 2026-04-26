"""
GCP 없이 TV UI를 데모할 수 있는 목업 서버.
실행: uvicorn mock_skill_engine:app --port 8080 --reload
"""
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Mock Skill Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    session_id: str = "default"


MOCK_SKILL_MAP = {
    "수거": "laundry_pickup",
    "예약": "appointment_booking",
    "주문": "menu_order",
    "배달": "delivery_request",
}


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "mock"}


@app.post("/create-skill")
async def create_skill(req: SkillRequest):
    await asyncio.sleep(1.5)
    tool_name = next(
        (v for k, v in MOCK_SKILL_MAP.items() if k in req.owner_input),
        "custom_service",
    )
    print(f"[MOCK] 스킬 생성: store={req.store_id} tool={tool_name}")
    return {"status": "success", "skill": tool_name}


@app.post("/order")
async def place_order(req: OrderRequest):
    await asyncio.sleep(1.0)
    print(f"[MOCK] 주문 완료: store={req.store_id} skill={req.skill_name} params={req.parameters}")
    return {"status": "success", "order_id": "mock-order-001"}


@app.post("/chat")
async def chat(req: ChatRequest):
    await asyncio.sleep(0.5)
    text = req.text
    if any(k in text for k in ["주문", "시켜", "응", "네", "좋아"]):
        return {"reply": "네, 주문 도와드릴게요! 무엇을 주문하실까요?", "action": "menu_order", "parameters": {}}
    return {"reply": f'"{text}"를 이해했어요. 더 자세히 말씀해 주세요.', "action": None, "parameters": {}}
