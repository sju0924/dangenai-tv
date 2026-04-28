"""
Vertex AI Agent Platform (ADK) 호환 버전.
Dialogflow CX ToolsClient 대신 Firestore 기반 스킬 레지스트리를 사용.
대화 시 Gemini Function Calling으로 스킬을 동적 라우팅.
"""
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "qwiklabs-gcp-04-4818f049b9ca")
LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")


def register_tool(spec: dict) -> None:
    """스펙 유효성 검사. 실제 등록은 firestore_client.save_skill()에서 처리."""
    required = ["tool_name", "description", "parameters", "webhook_url"]
    missing = [f for f in required if f not in spec]
    if missing:
        raise ValueError(f"스펙에 필수 필드 없음: {missing}")
