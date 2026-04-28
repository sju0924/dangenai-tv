import functions_framework, json, os
from google.cloud import firestore
import firebase_admin
from firebase_admin import messaging, credentials

# 로컬 테스트: GOOGLE_APPLICATION_CREDENTIALS 환경변수 또는 SA 키 경로
_cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if not firebase_admin._apps:
    if _cred_path:
        firebase_admin.initialize_app(credentials.Certificate(_cred_path))
    else:
        firebase_admin.initialize_app()

db = firestore.Client(
    project=os.environ.get("GCP_PROJECT_ID", "qwiklabs-gcp-04-4818f049b9ca"),
    database=os.environ.get("FIRESTORE_DATABASE", "dangenai-skills"),
)


@functions_framework.http
def handle_skill(request):
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return ("", 204, headers)

    store_id = request.args.get("store_id")
    if not store_id:
        return (json.dumps({"error": "store_id 필요"}), 400)

    data = request.get_json(silent=True) or {}
    skill_name = data.get("skill_name", "요청")
    params = data.get("parameters", {})

    store_doc = db.collection("stores").document(store_id).get()
    if not store_doc.exists:
        return (json.dumps({"error": f"가게 없음: {store_id}"}), 404)

    fcm_token = store_doc.to_dict().get("owner_fcm_token")
    if not fcm_token:
        return (json.dumps({"error": "FCM 토큰 없음"}), 400)

    message = messaging.Message(
        notification=messaging.Notification(
            title=f"새 요청: {skill_name}",
            body=json.dumps(params, ensure_ascii=False),
        ),
        token=fcm_token,
    )
    messaging.send(message)

    headers = {"Access-Control-Allow-Origin": "*"}
    return (json.dumps({"status": "success", "message": "알림 전송 완료"}), 200, headers)
