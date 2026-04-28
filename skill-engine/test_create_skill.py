"""
스킬 생성 단계별 테스트
  1단계: Gemini로 OpenAPI 스펙 생성 (skill_gen)
  2단계: 스펙 유효성 검사 (agent_binder)
  3단계: Firestore 저장 (firestore_client) — 선택적

실행:
  python test_create_skill.py           # 1~2단계만
  python test_create_skill.py --full    # Firestore 포함
"""
import json, sys
import vertexai

# ── 실제 프로젝트로 Vertex AI 초기화 ──────────────────────
PROJECT_ID = "qwiklabs-gcp-04-4818f049b9ca"
vertexai.init(project=PROJECT_ID, location="us-central1")

from skill_gen import generate_skill_spec  # noqa: E402 (init 이후 import 필수)
from agent_binder import register_tool     # noqa: E402

FULL_MODE = "--full" in sys.argv

TEST_CASES = [
    {
        "store_id": "test_store_001",
        "owner_input": "손님이 세탁물 수거를 신청할 수 있게 해줘. 주소랑 날짜 받아야 해.",
    },
    {
        "store_id": "test_store_002",
        "owner_input": "오늘 예약 가능한 시간대를 조회하는 기능 만들어줘.",
    },
]


def sep(title=""):
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def run_test(tc: dict):
    store_id = tc["store_id"]
    user_input = tc["owner_input"]

    print(f"\n[입력] store_id={store_id}")
    print(f"       owner_input={user_input}")
    print("-" * 60)

    # ── 1단계: Gemini → OpenAPI 스펙 ────────────────────
    print("1단계: Gemini 스펙 생성 중...")
    try:
        spec = generate_skill_spec(user_input, store_id)
        print("  결과:")
        print(json.dumps(spec, ensure_ascii=False, indent=4))
        assert "tool_name" in spec,    "tool_name 없음"
        assert "description" in spec,  "description 없음"
        assert "parameters" in spec,   "parameters 없음"
        assert "webhook_url" in spec,  "webhook_url 없음"
        print("  [PASS] 1단계 — 스펙 생성 성공")
    except Exception as e:
        print(f"  [FAIL] 1단계 — {type(e).__name__}: {e}")
        return

    # ── 2단계: 스펙 유효성 검사 ─────────────────────────
    print("\n2단계: 스펙 유효성 검사 중...")
    try:
        register_tool(spec)
        print("  [PASS] 2단계 — 유효성 검사 통과")
    except Exception as e:
        print(f"  [FAIL] 2단계 — {type(e).__name__}: {e}")
        return

    # ── 3단계: Firestore 저장 (--full 옵션 시만) ─────────
    if not FULL_MODE:
        print("\n3단계: Firestore 저장 건너뜀 (--full 옵션 없음)")
        return

    print("\n3단계: Firestore 저장 중...")
    try:
        from firestore_client import db, save_skill

        # 테스트 가게 문서 없으면 먼저 생성
        store_ref = db.collection("stores").document(store_id)
        if not store_ref.get().exists:
            store_ref.set({"name": "테스트 가게", "skills": []})
            print(f"  테스트 문서 생성: stores/{store_id}")

        save_skill(store_id, spec)

        saved = store_ref.get().to_dict()
        skill_names = [s["tool_name"] for s in saved.get("skills", [])]
        assert spec["tool_name"] in skill_names, "저장된 스킬 없음"
        print(f"  저장된 스킬: {skill_names}")
        print("  [PASS] 3단계 — Firestore 저장 성공")
    except Exception as e:
        print(f"  [FAIL] 3단계 — {type(e).__name__}: {e}")


if __name__ == "__main__":
    mode = "전체 (Firestore 포함)" if FULL_MODE else "부분 (Gemini + 검증만)"
    sep(f"스킬 생성 테스트 — {mode}")

    for i, tc in enumerate(TEST_CASES, 1):
        sep(f"테스트 케이스 {i}/{len(TEST_CASES)}")
        run_test(tc)

    sep("완료")
