from google.cloud import firestore
import os
from dotenv import load_dotenv

load_dotenv()

db = firestore.Client(
    project=os.environ.get("GCP_PROJECT_ID", "project-9ed97ef0-254a-4ec3-975"),
    database=os.environ.get("FIRESTORE_DATABASE", "dangenai-skills"),
)

def get_store(store_id: str) -> dict:
    doc = db.collection("stores").document(store_id).get()
    if not doc.exists:
        raise ValueError(f"가게 없음: {store_id}")
    return doc.to_dict()

def save_skill(store_id: str, spec: dict):
    skill_entry = {
        "tool_name": spec["tool_name"],
        "description": spec["description"],
        "parameters": spec.get("parameters", {}),
        "examples": spec.get("examples", []),
        "response_template": spec.get("response_template", ""),
        "webhook_url": spec.get("webhook_url", ""),
    }
    db.collection("stores").document(store_id).update({
        "skills": firestore.ArrayUnion([skill_entry])
    })

def save_order(store_id: str, skill_name: str, parameters: dict) -> str:
    order_ref = db.collection("orders").document()
    order_ref.set({
        "store_id": store_id,
        "skill_name": skill_name,
        "parameters": parameters,
        "status": "pending",
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return order_ref.id