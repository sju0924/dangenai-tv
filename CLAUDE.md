# 당그나이TV 해커톤 프로젝트

> GCP + Vertex AI Agent Builder 기반 로컬 커머스 플랫폼  
> 해커톤 현장 7시간 — 연동·디버깅·발표 연습만 합니다. 핵심 코드와 GCP 환경은 미리 완성된 상태로 진입합니다.

---

## 프로젝트 한 줄 요약

- **사장님**: 자연어로 말하면 AI가 Agent Skill(API)을 자동 생성
- **사용자**: 거실 TV 화면에서 음성으로 로컬 서비스 주문

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| AI / NLU | Vertex AI Agent Builder, gemini-2.5-flash-lite |
| 스킬 생성 엔진 | Python / FastAPI → Cloud Run (`skill-engine`) |
| 동적 Tool 등록 | `google-cloud-dialogflow-cx` SDK |
| DB | Firestore (Native mode, `asia-northeast-3`) |
| 알림 | FCM (Firebase Cloud Messaging) |
| 범용 Webhook | Cloud Functions (Python 3.11) |
| TV UI | React (Tizen TV 풀스크린 웹앱, Web Speech API) |

---

## GCP 환경

| 항목 | 값 |
|---|---|
| Project ID | `project-9ed97ef0-254a-4ec3-975` |
| Firestore | Native mode, 미국 리전 |
| Agent 리소스 경로 | `projects/{PROJECT}/locations/asia-northeast3/agents/{AGENT_ID}` |

### 필요 API 활성화 명령어

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudfunctions.googleapis.com \
  firestore.googleapis.com \
  firebase.googleapis.com
```

---

## 폴더 구조

```
dangnai-tv/
├── CLAUDE.md                  # ← 이 파일
├── skill-engine/              # Cloud Run — Skill 자동 생성 엔진 (핵심)
│   ├── main.py                # FastAPI 진입점
│   ├── skill_gen.py           # Gemini → OpenAPI Spec 변환
│   ├── agent_binder.py        # Agent Builder Tool 동적 등록
│   ├── firestore_client.py    # Firestore 저장
│   ├── requirements.txt
│   └── Dockerfile
├── functions/                 # Cloud Functions — Universal Webhook
│   └── main.py                # FCM 알림 발송 핸들러
└── tv-ui/                     # React 풀스크린 TV 앱
    └── src/
        ├── App.jsx
        └── components/
            ├── TVHome.jsx         # 시청 화면 (맥락 감지)
            ├── AgentBubble.jsx    # 선제적 제안 말풍선
            ├── OrderConfirmCard.jsx
            └── VoiceIndicator.jsx
```

---

## 핵심 아키텍처 흐름

```
[사장님 자연어 입력]
       ↓
gemini-2.5-flash-lite (skill_gen.py)
— 자연어 → OpenAPI 3.0 Spec(JSON) 자동 생성
       ↓
Agent Builder API (agent_binder.py)
— Spec을 Agent의 Tool로 동적 등록
       ↓
Firestore에 Skill 메타 저장
       ↓
[TV 사용자 음성 입력 "수거해줘"]
       ↓
Vertex AI Agent (Function Calling)
— 등록된 Skill 식별 → 파라미터 수집
       ↓
Universal Webhook (Cloud Functions)
— FCM으로 사장님 폰에 실시간 알림
```

---

## 핵심 파일 설명

### `skill_gen.py` — Gemini로 OpenAPI Spec 생성

- `generate_skill_spec(owner_input, store_id)` 함수가 핵심
- Gemini에게 JSON만 출력하도록 System Prompt로 강제
- `webhook_url`을 spec에 자동 주입 (`https://YOUR_WEBHOOK_URL/handle?store_id={store_id}`)
- JSON 블록 파싱 실패 시 `re.search(r'\{.*\}', raw, re.DOTALL)`로 안전하게 추출

### `agent_binder.py` — Agent에 Tool 동적 등록

- `register_tool(spec)` → `cx.ToolsClient().create_tool()` 호출
- OpenAPI 3.0 JSON 스키마를 `cx.Tool.OpenApiTool(text_schema=...)`로 래핑
- 반환값: tool resource name (Firestore에 저장)

### `functions/main.py` — Universal Webhook

- 모든 Skill 호출의 단일 엔드포인트
- `store_id`로 Firestore에서 FCM 토큰 조회 → FCM 알림 발송
- `skill_name`, `parameters`를 알림 body에 포함

### `tv-ui/src/components/AgentBubble.jsx`

- 우하단 고정 말풍선 (position: fixed, bottom: 80, right: 60)
- "네, 주문할게요" / "괜찮아요" 버튼
- fontSize: 28px (TV 시청 거리 대응)

---

## Firestore 데이터 구조

```js
// stores/{store_id}
{
  name: '당그나이 세탁소',
  owner_fcm_token: 'FCM_TOKEN_HERE',
  category: 'laundry',          // laundry | beauty | hospital | restaurant
  menus: [
    { id: 'm1', name: '일반 세탁', price: 5000 },
    { id: 'm2', name: '드라이클리닝', price: 12000 }
  ],
  skills: []    // Skill Engine이 동적으로 채움
                // [{ tool_name, description, tool_resource_name }]
}
```

---

## 배포 명령어

### skill-engine (Cloud Run)

```bash
cd skill-engine
gcloud run deploy skill-engine \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=dangnai-tv-demo
```

### Universal Webhook (Cloud Functions)

```bash
gcloud functions deploy handle-skill \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --region asia-northeast3 \
  --source functions/
```

---

## 데모 시나리오 (5분)

### A. 사장님 Skill 생성 (2분)
1. 태블릿에 **"수거 서비스 스킬 만들어줘, 주소랑 시간 받아야 해"** 입력
2. Gemini가 OpenAPI Spec 실시간 생성 → UI에 타이핑 효과로 표시
3. "Skill 등록 완료!" → GCP 콘솔에서 Tool 추가 확인

### B. TV 음성 주문 (2분)
1. TV에 야구 중계 이미지 표시
2. AgentBubble: **"치킨 시킬까요? 근처 당그나이치킨이 있어요"**
3. 음성/"응, 주문해줘" → OrderConfirmCard 표시
4. 사장님 폰에 FCM 알림 도착 (화면 미러링 시연)

### C. 메뉴판 사진 입점 (1분)
1. 메뉴판 사진 업로드
2. Gemini Vision 5초 안에 메뉴 자동 추출
3. 확인 후 TV 서비스 즉시 노출

---

## 실패 대비 플랜 (필수 준비)

| 장애 상황 | 대응 방법 |
|---|---|
| GCP API 장애 | `mock_skill_engine.py` (하드코딩 응답) 로컬 실행 |
| FCM 알림 불발 | 화면 캡처 이미지로 대체 |
| 음성 인식 실패 | 버튼 클릭으로 동일 플로우 트리거 |
| Gemini 응답 느림 | 스트리밍 UI + 응답 캐싱으로 체감 시간 단축 |
| 전체 시스템 다운 | 사전 녹화 데모 영상 재생 |

---

## 자주 쓰는 질문 패턴 (Claude Code에서)

```
# 특정 파일 기준으로 질문할 때
@skill_gen.py Gemini 응답이 JSON 파싱 실패할 때 fallback 로직 추가해줘

# 에러 발생 시
이 에러 고쳐줘: [에러 메시지 붙여넣기]

# 새 기능 추가
메뉴판 이미지 업로드 → Gemini Vision으로 메뉴 추출하는 엔드포인트 /extract-menu 만들어줘

# 배포 전 체크
Cloud Run 배포 전 로컬 테스트 방법 알려줘
```
