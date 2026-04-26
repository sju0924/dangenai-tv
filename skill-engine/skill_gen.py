import vertexai, json, re, os
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "project-9ed97ef0-254a-4ec3-975")
VERTEX_LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://YOUR_WEBHOOK_URL")

vertexai.init(project=PROJECT_ID, location=VERTEX_LOCATION)

SYSTEM_PROMPT = '''
당신은 소상공인의 자연어 요청을 분석하여 TV 주문 서비스용 스킬 스펙(JSON)을 생성합니다.
반드시 JSON만 출력하고 다른 텍스트는 절대 포함하지 마세요.

형식:
{
  "tool_name": "snake_case_영문_이름",
  "description": "이 스킬이 하는 일을 한 문장으로 설명 (Gemini가 언제 이 스킬을 호출할지 판단하는 기준)",
  "parameters": {
    "type": "object",
    "properties": {
      "param1": {
        "type": "string",
        "description": "파라미터 설명 (예시 값 포함, 예: 수거 주소, 예: 서울시 강남구 역삼동 123)"
      }
    },
    "required": ["param1"]
  },
  "examples": [
    "사용자가 이 서비스를 요청할 때 쓸 법한 자연어 문장 3~5개 (한국어)"
  ],
  "response_template": "스킬 호출 성공 후 사용자에게 보여줄 응답 템플릿 (파라미터는 {param_name} 형식으로 참조)"
}

작성 원칙:
- tool_name은 영문 snake_case (예: laundry_pickup, appointment_booking)
- description은 Gemini가 트리거 여부를 판단하는 핵심 문장 — 명확하고 구체적으로
- parameters는 서비스에 실제로 필요한 정보만 (과도하게 많지 않게)
- examples는 실제 사용자가 TV 앞에서 말할 법한 구어체 문장
- response_template은 친근하고 간결하게 (TV 화면 기준 2문장 이내)
'''


def generate_skill_spec(owner_input: str, store_id: str) -> dict:
    model = GenerativeModel(
        "gemini-2.5-flash-lite",
        system_instruction=SYSTEM_PROMPT,
    )
    response = model.generate_content(owner_input)
    raw = response.text.strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    spec = json.loads(match.group()) if match else json.loads(raw)
    spec["webhook_url"] = f"{WEBHOOK_URL}/handle?store_id={store_id}"
    return spec
