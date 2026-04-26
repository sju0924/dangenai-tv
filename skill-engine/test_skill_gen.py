"""
skill_gen.py 단독 테스트.
실제 Vertex AI를 호출하며, gcloud 인증이 되어 있어야 합니다.
"""
import vertexai

# 1) 먼저 skill_gen을 임포트 → 내부 vertexai.init(project='YOUR_PROJECT_ID') 실행
from skill_gen import generate_skill_spec  # noqa: E402

# 2) 실제 프로젝트로 다시 init → 직전 호출을 덮어씀
_REAL_PROJECT = "project-9ed97ef0-254a-4ec3-975"
# gemini-1.5-pro-001 은 asia-northeast3 미지원 → us-central1 사용
vertexai.init(project=_REAL_PROJECT, location="us-central1")

TEST_CASES = [
    {
        "store_id": "store_001",
        "owner_input": "손님이 오늘 예약 가능한 시간대를 조회할 수 있게 해줘",
    },
    {
        "store_id": "store_002",
        "owner_input": "메뉴판에서 특정 메뉴의 가격을 검색하는 기능을 만들어줘",
    },
]

if __name__ == "__main__":
    import json

    for i, tc in enumerate(TEST_CASES, 1):
        print(f"\n{'='*60}")
        print(f"[TEST {i}] store_id={tc['store_id']}")
        print(f"  input: {tc['owner_input']}")
        print("-" * 60)
        try:
            spec = generate_skill_spec(tc["owner_input"], tc["store_id"])
            print("  결과:")
            print(json.dumps(spec, ensure_ascii=False, indent=2))
            # 기본 필드 검증
            assert "tool_name" in spec, "tool_name 없음"
            assert "description" in spec, "description 없음"
            assert "parameters" in spec, "parameters 없음"
            assert "webhook_url" in spec, "webhook_url 없음"
            print("  [PASS] 필수 필드 검증 통과")
        except Exception as e:
            print(f"  [FAIL] {type(e).__name__}: {e}")

    print(f"\n{'='*60}")
    print("테스트 완료")
