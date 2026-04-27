"""
소비자 주문 흐름 E2E 테스트 — 직접 함수 호출 방식
  서버 실행 불필요. skill-engine 모듈을 직접 import해서 실행.

실행:
  python test_consumer_flow.py                          # 전체 시나리오 + 근처 라우팅
  python test_consumer_flow.py --scenario laundry       # 특정 시나리오만
  python test_consumer_flow.py --scenario nearby        # 근처 점포 라우팅 데모만
  python test_consumer_flow.py --skip-create-skill      # 스킬 생성 건너뜀

사용 가능 시나리오: laundry | restaurant | beauty | hospital | nearby
"""
import sys, json, asyncio, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skill-engine"))

import vertexai
from dotenv import load_dotenv
from vertexai.generative_models import FunctionDeclaration, GenerativeModel, Tool, ToolConfig

load_dotenv("skill-engine/.env")

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "project-9ed97ef0-254a-4ec3-975")
vertexai.init(project=PROJECT_ID, location=os.environ.get("VERTEX_LOCATION", "us-central1"))

from skill_gen import generate_skill_spec  # type: ignore
from agent_binder import register_tool  # type: ignore
from firestore_client import db, save_skill, save_order  # type: ignore


# ── CLI 파싱 ───────────────────────────────────────────────
SKIP_CREATE = "--skip-create-skill" in sys.argv
_scenario_arg = None
if "--scenario" in sys.argv:
    _idx = sys.argv.index("--scenario")
    _scenario_arg = sys.argv[_idx + 1] if _idx + 1 < len(sys.argv) else None
elif len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
    _scenario_arg = sys.argv[1]


# ── 단일 점포 시나리오 ─────────────────────────────────────
SCENARIOS = {
    "laundry": {
        "label": "세탁소 — 수거 신청",
        "store_id": "store_laundry",
        "store_name": "당그나이 세탁소",
        "skill_input": "손님이 세탁물 수거를 신청할 수 있게 해줘. 주소랑 수거 날짜를 받아야 해.",
        "chat_cases": [
            "서울시 강남구 역삼동으로 내일 세탁물 수거해줘",
            "세탁물 가져가 주세요. 마포구 합정동이에요",
            "오늘 저녁 6시에 수거 부탁드려요. 주소는 용산구 한남동 123이요",
        ],
        "order_skill": "laundry_pickup",
        "order_params": {"address": "서울시 강남구 역삼동 123", "pickup_date": "내일"},
    },
    "restaurant": {
        "label": "식당 — 배달 주문",
        "store_id": "store_restaurant",
        "store_name": "당그나이 치킨",
        "skill_input": "손님이 배달 주문할 수 있게 해줘. 메뉴 이름이랑 수량, 배달 주소를 받아야 해.",
        "chat_cases": [
            "후라이드 치킨 두 마리 강남구 삼성동으로 배달해줘",
            "양념치킨 한 마리랑 콜라 하나 주문할게요. 서초구 방배동이에요",
            "간장치킨 한 마리, 마포구 연남동 배달이야",
        ],
        "order_skill": "delivery_order",
        "order_params": {"menu": "후라이드 치킨", "quantity": "2", "address": "강남구 삼성동 100"},
    },
    "beauty": {
        "label": "미용실 — 예약",
        "store_id": "store_beauty",
        "store_name": "당그나이 헤어샵",
        "skill_input": "손님이 미용실 예약을 할 수 있게 해줘. 서비스 종류(커트·염색·펌)랑 날짜, 시간을 받아야 해.",
        "chat_cases": [
            "내일 오후 2시에 커트 예약하고 싶어요",
            "이번 주 토요일 오전 11시에 염색 예약 가능할까요?",
            "펌 하려고 하는데 금요일 저녁 6시로 잡을 수 있어요?",
        ],
        "order_skill": "salon_booking",
        "order_params": {"service": "커트", "date": "내일", "time": "오후 2시"},
    },
    "hospital": {
        "label": "병원 — 진료 예약",
        "store_id": "store_hospital",
        "store_name": "당그나이 의원",
        "skill_input": "환자가 진료 예약을 할 수 있게 해줘. 이름이랑 증상, 원하는 날짜와 시간을 받아야 해.",
        "chat_cases": [
            "내일 오전 10시에 감기 진료 예약하고 싶어요. 김철수예요",
            "허리가 아픈데 이번 주 목요일 오후 3시로 예약할 수 있을까요? 이영희입니다",
            "두통이 있어서 오늘 오후 5시 진료 원해요. 박지민이에요",
        ],
        "order_skill": "appointment_booking",
        "order_params": {"name": "김철수", "symptom": "감기", "date": "내일", "time": "오전 10시"},
    },
}


# ── 근처 점포 라우팅 시나리오 ──────────────────────────────
#
#   같은 업종(세탁소·치킨)의 점포가 지역별로 여럿 있을 때
#   사용자의 위치 발화만으로 Gemini가 알아서 맞는 점포로 라우팅합니다.
#
#   tool_name 충돌을 막기 위해 멀티점포 등록 시 "{prefix}_{tool_name}" 형식을 씁니다.
#   (예: gangnam_laundry_pickup, mapo_laundry_pickup)
#
NEARBY_STORES = [
    {
        "store_id":   "store_gangnam_laundry",
        "store_name": "강남 당그나이 세탁소",
        "prefix":     "gangnam",
        "area":       "강남구·서초구·송파구",
        "skill_input": (
            "세탁물 수거 신청 서비스야. 주소랑 날짜를 받아야 해. "
            "이 점포는 강남구·서초구·송파구 지역만 담당해."
        ),
        "order_params": {"address": "강남구 역삼동 123", "pickup_date": "내일"},
    },
    {
        "store_id":   "store_mapo_laundry",
        "store_name": "마포 당그나이 세탁소",
        "prefix":     "mapo",
        "area":       "마포구·서대문구·은평구",
        "skill_input": (
            "세탁물 수거 신청 서비스야. 주소랑 날짜를 받아야 해. "
            "이 점포는 마포구·서대문구·은평구 지역만 담당해."
        ),
        "order_params": {"address": "마포구 합정동 77", "pickup_date": "오늘"},
    },
    {
        "store_id":   "store_jongno_chicken",
        "store_name": "종로 당그나이 치킨",
        "prefix":     "jongno",
        "area":       "종로구·중구·용산구",
        "skill_input": (
            "치킨 배달 주문 서비스야. 메뉴·수량·배달 주소를 받아야 해. "
            "이 점포는 종로구·중구·용산구 지역만 배달해."
        ),
        "order_params": {"menu": "후라이드", "quantity": "1", "address": "종로구 관철동 5"},
    },
]

# 근처 라우팅 테스트용 발화 — 지역명을 포함해서 Gemini가 점포를 구분하도록
NEARBY_CHAT_CASES = [
    ("강남구 역삼동으로 내일 세탁물 수거해줘",          "강남 세탁소 라우팅 기대"),
    ("합정동인데 세탁물 수거 신청하고 싶어요",           "마포 세탁소 라우팅 기대"),
    ("종로구에서 후라이드 치킨 한 마리 시킬게요. 관철동이요", "종로 치킨 라우팅 기대"),
    ("서초구 방배동 세탁물 수거 부탁해요",              "강남 세탁소 라우팅 기대 (서초구 포함)"),
]


# ── 출력 헬퍼 ──────────────────────────────────────────────
def sep(title=""):
    print("\n" + "=" * 65)
    if title:
        print(f"  {title}")
        print("=" * 65)

def ok(msg):   print(f"  ✅ {msg}")
def fail(msg): print(f"  ❌ {msg}")
def info(msg): print(f"  ℹ  {msg}")


# ── 공통: 스킬 생성 ───────────────────────────────────────
def _create_skill(store_id: str, store_name: str, skill_input: str,
                  tool_name_prefix: str = "") -> dict | None:
    try:
        spec = generate_skill_spec(skill_input, store_id)

        # 멀티점포 모드: tool_name에 지역 prefix 추가
        if tool_name_prefix and not spec["tool_name"].startswith(tool_name_prefix):
            spec["tool_name"] = f"{tool_name_prefix}_{spec['tool_name']}"

        register_tool(spec)

        store_ref = db.collection("stores").document(store_id)
        if not store_ref.get().exists:
            store_ref.set({"name": store_name, "skills": []})
        save_skill(store_id, spec)
        ok(f"스킬 저장: [{spec['tool_name']}] → stores/{store_id}")
        return spec
    except Exception as e:
        fail(f"{type(e).__name__}: {e}")
        return None


# ── 단일 점포 시나리오 실행 ────────────────────────────────
async def run_scenario(sc: dict):
    sep(f"【{sc['label']}】")

    # 1. 스킬 생성
    if not SKIP_CREATE:
        info(f"스킬 입력: \"{sc['skill_input']}\"")
        _create_skill(sc["store_id"], sc["store_name"], sc["skill_input"])
    else:
        info("스킬 생성 건너뜀")

    # 2. 자연어 → 스킬 매칭
    store = db.collection("stores").document(sc["store_id"]).get().to_dict() or {}
    skills = store.get("skills", [])
    if not skills:
        fail("등록된 스킬 없음 — 스킬 생성 후 재실행하세요"); return

    declarations = _build_declarations(skills)
    model = _build_model(declarations, sc["store_name"])

    print(f"\n  ─ 자연어 → 스킬 매칭 테스트 ─")
    for i, text in enumerate(sc["chat_cases"], 1):
        _run_chat(model, i, text)

    # 3. 주문 저장 + webhook
    print(f"\n  ─ 주문 접수 ─")
    await _place_order(sc["store_id"], sc["order_skill"], sc["order_params"])

    # 4. Firestore 확인
    print(f"\n  ─ Firestore 확인 ─")
    _check_firestore(sc["store_id"])


# ── 근처 점포 라우팅 데모 ──────────────────────────────────
async def run_nearby():
    sep("【근처 점포 라우팅 데모】 — 지역 발화 → 올바른 점포 자동 연결")
    info(f"등록 점포 {len(NEARBY_STORES)}개: " +
         " / ".join(f"{s['store_name']}({s['area']})" for s in NEARBY_STORES))

    # 1. 각 점포 스킬 생성
    if not SKIP_CREATE:
        print()
        for s in NEARBY_STORES:
            info(f"점포 등록: {s['store_name']}")
            _create_skill(s["store_id"], s["store_name"], s["skill_input"], s["prefix"])
    else:
        info("스킬 생성 건너뜀")

    # 2. 전 점포 스킬을 한 번에 로드 → Gemini에 전달
    all_skills = []       # (store_meta, skill_entry)
    store_map = {}        # tool_name → store_meta  (역방향 조회용)
    for s in NEARBY_STORES:
        store_doc = db.collection("stores").document(s["store_id"]).get()
        skills = (store_doc.to_dict() or {}).get("skills", [])
        for sk in skills:
            all_skills.append((s, sk))
            store_map[sk["tool_name"]] = s

    if not all_skills:
        fail("등록된 스킬이 없습니다. --skip-create-skill 없이 먼저 실행하세요")
        return

    declarations = _build_declarations([sk for _, sk in all_skills])
    model = _build_model(
        declarations,
        system_instruction=(
            "당신은 당그나이TV 지역 서비스 어시스턴트입니다. "
            "사용자의 위치(동·구 이름)를 파악해 가장 가까운 점포의 스킬을 반드시 호출하세요."
        ),
    )

    print(f"\n  ─ 위치 기반 라우팅 테스트 ─")
    for i, (text, hint) in enumerate(NEARBY_CHAT_CASES, 1):
        print(f"\n  [{i}] {hint}")
        fc = _run_chat(model, i, text, show_index=False)
        if fc:
            matched_store = store_map.get(fc)
            if matched_store:
                print(f"         점포명   : {matched_store['store_name']} ({matched_store['area']})")

    # 3. 점포별 Firestore 확인
    print(f"\n  ─ 점포별 Firestore 상태 ─")
    for s in NEARBY_STORES:
        doc = db.collection("stores").document(s["store_id"]).get().to_dict() or {}
        skill_names = [sk["tool_name"] for sk in doc.get("skills", [])]
        info(f"{s['store_name']}: {skill_names}")


# ── 내부 헬퍼 ─────────────────────────────────────────────
def _build_declarations(skills: list):
    decls = []
    for skill in skills:
        desc = skill["description"]
        examples = skill.get("examples", [])
        if examples:
            desc += f"\n사용 예시: {' / '.join(examples)}"
        decls.append(
            FunctionDeclaration(
                name=skill["tool_name"],
                description=desc,
                parameters=skill.get("parameters", {"type": "object", "properties": {}}),
            )
        )
    return decls


def _build_model(declarations, store_name: str = "", system_instruction: str = ""):
    if not system_instruction:
        system_instruction = (
            f"당신은 {store_name} TV 주문 어시스턴트입니다. "
            "반드시 제공된 함수를 호출해 서비스를 연결하세요."
        )
    tool = Tool(function_declarations=declarations)
    tool_config = ToolConfig(
        function_calling_config=ToolConfig.FunctionCallingConfig(
            mode=ToolConfig.FunctionCallingConfig.Mode.ANY
        )
    )
    return GenerativeModel(
        "gemini-2.5-flash-lite",
        system_instruction=system_instruction,
        tools=[tool],
        tool_config=tool_config,
    )


def _run_chat(model, index: int, text: str, show_index: bool = True) -> str | None:
    """발화 1개를 모델에 보내고 매칭된 tool_name을 반환 (없으면 None)."""
    if show_index:
        print(f"\n  [{index}] 입력: \"{text}\"")
    else:
        print(f"         입력   : \"{text}\"")
    try:
        response = model.generate_content(text)
        part = response.candidates[0].content.parts[0]
        fc = getattr(part, "function_call", None)
        if fc and getattr(fc, "name", None):
            print(f"         ▶ 매칭 스킬 : [{fc.name}]")
            print(f"           파라미터  : {json.dumps(dict(fc.args), ensure_ascii=False)}")
            ok("스킬 매칭 성공")
            return fc.name
        else:
            reply = getattr(part, "text", "(응답 없음)")
            print(f"         reply  : {reply}")
            info("스킬 미매칭")
            return None
    except Exception as e:
        fail(f"{type(e).__name__}: {e}")
        return None


async def _place_order(store_id: str, skill_name: str, params: dict):
    import httpx
    info(f"skill={skill_name}  params={json.dumps(params, ensure_ascii=False)}")
    try:
        order_id = save_order(store_id, skill_name, params)
        ok(f"Firestore 주문 저장: order_id={order_id}")
    except Exception as e:
        fail(f"Firestore 저장 실패: {type(e).__name__}: {e}"); return

    webhook_url = os.environ.get("WEBHOOK_URL", "")
    if not webhook_url:
        info("WEBHOOK_URL 미설정 — webhook 건너뜀"); return
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                webhook_url,
                params={"store_id": store_id},
                json={"skill_name": skill_name, "parameters": params},
                timeout=10.0,
            )
        if r.status_code == 200:
            ok("webhook 호출 성공 → FCM 알림 전송됨")
        else:
            info(f"webhook 응답 {r.status_code}: {r.text}")
    except Exception as e:
        info(f"webhook 호출 실패: {type(e).__name__}: {e}")


def _check_firestore(store_id: str):
    from google.cloud.firestore_v1.base_query import FieldFilter
    try:
        orders = (
            db.collection("orders")
            .where(filter=FieldFilter("store_id", "==", store_id))
            .limit(3)
            .get()
        )
        if orders:
            ok(f"최근 주문 {len(orders)}건:")
            for o in orders:
                d = o.to_dict()
                print(f"     ▶ 스킬: {d.get('skill_name')}  상태: {d.get('status')}")
                print(f"       파라미터: {json.dumps(d.get('parameters', {}), ensure_ascii=False)}")
        else:
            info("주문 기록 없음")
    except Exception as e:
        fail(f"{type(e).__name__}: {e}")


# ── 메인 ──────────────────────────────────────────────────
async def main():
    all_keys = list(SCENARIOS.keys()) + ["nearby"]

    if _scenario_arg == "nearby":
        sep("근처 점포 라우팅 단독 테스트")
        await run_nearby()

    elif _scenario_arg and _scenario_arg in SCENARIOS:
        sep(f"단일 시나리오: {_scenario_arg}")
        await run_scenario(SCENARIOS[_scenario_arg])

    elif _scenario_arg and _scenario_arg not in all_keys:
        print(f"알 수 없는 시나리오: '{_scenario_arg}'")
        print(f"사용 가능: {' | '.join(all_keys)}")
        return

    else:
        sep(f"전체 테스트 — 단일 점포 {len(SCENARIOS)}개 + 근처 라우팅")
        for sc in SCENARIOS.values():
            await run_scenario(sc)
        await run_nearby()

    sep("완료")


if __name__ == "__main__":
    asyncio.run(main())
