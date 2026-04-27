# 당그나이TV 해커톤 프로젝트

> GCP + Gemini Function Calling 기반 로컬 커머스 플랫폼  
> 해커톤 현장 7시간 — 연동·디버깅·발표 연습만 합니다. 핵심 코드와 GCP 환경은 미리 완성된 상태로 진입합니다.

---

## 프로젝트 한 줄 요약

- **사장님**: 자연어로 말하면 AI가 서비스 스킬(주문 API)을 자동 생성
- **사용자**: 거실 TV 화면에서 음성으로 근처 가게에 주문 → 사장님 폰에 FCM 알림

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| AI / NLU | Gemini 2.5-flash-lite (Function Calling) |
| 스킬 생성 엔진 | Python / FastAPI → Cloud Run (`skill-engine`) |
| DB | Firestore (Native mode, `dangenai-skills`, nam5) |
| 알림 | FCM (Firebase Cloud Messaging) |
| 범용 Webhook | Cloud Functions Python 3.11 (`webhook/`) |
| TV UI | React + Vite (풀스크린 웹앱, Web Speech API) |
| 사장님 앱 | 정적 HTML (`owner-app/`) — FCM 토큰 등록 |

> **Dialogflow CX / Agent Builder는 사용하지 않습니다.**  
> 인텐트 파악·파라미터 추출 모두 skill-engine 내 Gemini Function Calling으로 처리합니다.

---

## GCP 환경

| 항목 | 값 |
|---|---|
| Project ID | `project-9ed97ef0-254a-4ec3-975` |
| Firestore DB | `dangenai-skills` (Native mode, nam5) |
| Cloud Run | `skill-engine` — `asia-northeast3` |
| Cloud Functions | `handle-skill` — `asia-northeast3` |

### 필요 API 활성화

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudfunctions.googleapis.com \
  firestore.googleapis.com \
  firebase.googleapis.com
```

### 인증 — SA 키 없이 ADC 사용

조직 정책(`iam.disableServiceAccountKeyCreation`)으로 SA 키 발급이 차단되어 있습니다.

```bash
gcloud auth application-default login
```

---

## 폴더 구조

```
dangenai-tv/
├── CLAUDE.md                      # ← 이 파일
├── SETUP.md                       # 팀원 온보딩 가이드
├── skill-engine/                  # Cloud Run — 스킬 생성 + 채팅 엔진
│   ├── main.py                    # FastAPI 엔드포인트
│   ├── skill_gen.py               # Gemini → 스킬 스펙(JSON) 자동 생성
│   ├── agent_binder.py            # 스펙 유효성 검사 (필수 필드 확인)
│   ├── firestore_client.py        # Firestore CRUD (upsert 방식)
│   ├── test_create_skill.py       # 스킬 생성 단계별 테스트
│   ├── requirements.txt
│   └── Dockerfile
├── webhook/                       # Cloud Functions — FCM 알림 발송
│   ├── main.py
│   └── requirements.txt
├── owner-app/                     # 사장님 FCM 토큰 등록 페이지 (정적 HTML)
│   ├── index.html
│   └── firebase-messaging-sw.js
├── tv-ui/                         # React 풀스크린 TV 앱
│   └── src/
│       ├── App.jsx
│       └── components/
│           ├── TVHome.jsx
│           ├── AgentBubble.jsx
│           ├── OrderConfirmCard.jsx
│           └── VoiceIndicator.jsx
├── mock_skill_engine.py           # GCP 없이 로컬 데모용 목업 서버
└── test_consumer_flow.py          # 소비자 주문 흐름 E2E 테스트 (5개 시나리오)
```

---

## 핵심 아키텍처 흐름

```
[사장님 자연어 입력]
       ↓
skill_gen.py — Gemini가 스킬 스펙(JSON) 자동 생성
  { tool_name, description, parameters, examples,
    response_template, webhook_url }
       ↓
agent_binder.py — 필수 필드 유효성 검사
       ↓
firestore_client.save_skill() — Firestore upsert
  stores/{store_id}.skills[] 에 저장 (중복 방지)
       ↓
[TV 사용자 음성 입력 "수거해줘"]
       ↓
/chat 엔드포인트
  Firestore에서 해당 가게 스킬 로드
  → FunctionDeclaration 변환
  → Gemini Function Calling (Mode.ANY 강제)
  → 스킬 매칭 + 파라미터 추출
       ↓
skill.webhook_url POST 호출 (webhook/main.py)
  → Firestore에서 owner_fcm_token 조회
  → FCM으로 사장님 폰에 실시간 알림
```

---

## 핵심 파일 설명

### `skill_gen.py` — 스킬 스펙 자동 생성

- `generate_skill_spec(owner_input, store_id)` 가 핵심
- System Prompt로 JSON만 출력하도록 강제
- 생성 스펙에 `examples`(트리거 예시 발화 3~5개), `response_template`(파라미터 치환 응답) 포함
- `webhook_url = f"{WEBHOOK_URL}?store_id={store_id}"` 자동 주입

### `agent_binder.py` — 스펙 유효성 검사

- `register_tool(spec)` — `tool_name`, `description`, `parameters`, `webhook_url` 필수 필드 확인
- Dialogflow CX 미사용. 검사 통과 시 Firestore 저장으로 바로 이어짐

### `firestore_client.py` — Firestore CRUD

- `save_skill()`: 같은 `tool_name`이 이미 있으면 덮어쓰기 (ArrayUnion 미사용 — 중복 방지)
- `save_order()`: `orders` 컬렉션에 주문 저장, `store_id` 필드로 쿼리
- Firestore 쿼리 시 `FieldFilter` 사용 (`where(filter=FieldFilter(...))`)

### `main.py` — FastAPI 엔드포인트

| 엔드포인트 | 역할 |
|---|---|
| `GET /health` | 헬스체크 |
| `POST /create-skill` | 스킬 생성 (Gemini → Firestore) |
| `POST /chat` | 자연어 → Gemini Function Calling → webhook |
| `POST /order` | 직접 주문 접수 + webhook 호출 |
| `POST /extract-menu` | 메뉴판 이미지 → Gemini Vision → Firestore |
| `POST /register-fcm-token` | 사장님 FCM 토큰 저장 |

### `webhook/main.py` — FCM 알림 발송

- `store_id`로 Firestore에서 `owner_fcm_token` 조회
- `firebase_admin.messaging.send()` 로 푸시 알림 전송
- 토큰 없으면 400 반환 (`"FCM 토큰 없음"`)

### `owner-app/index.html` — 사장님 FCM 토큰 등록

- 브라우저 알림 권한 요청 → FCM 토큰 발급
- `/register-fcm-token` 호출로 Firestore 자동 저장
- Service Worker(`firebase-messaging-sw.js`) 필요 — HTTPS 또는 localhost에서만 동작

---

## Firestore 데이터 구조

```js
// stores/{store_id}
{
  name: '당그나이 세탁소',
  owner_fcm_token: 'FCM_TOKEN_HERE',   // owner-app에서 등록
  category: 'laundry',                 // laundry | beauty | hospital | restaurant
  menus: [                             // /extract-menu 가 채움
    { name: '일반 세탁', price: 5000 },
    { name: '드라이클리닝', price: 12000 }
  ],
  skills: [                            // /create-skill 이 채움 (upsert)
    {
      tool_name: 'laundry_pickup',
      description: '세탁물 수거 신청 서비스',
      parameters: { type: 'object', properties: { address: ..., pickup_date: ... } },
      examples: ['세탁물 가져가 주세요', ...],
      response_template: '{address}로 {pickup_date}에 수거 예약했어요!',
      webhook_url: 'https://.../handle-skill?store_id=store_demo'
    }
  ]
}

// orders/{order_id}
{
  store_id: 'store_demo',
  skill_name: 'laundry_pickup',
  parameters: { address: '...', pickup_date: '...' },
  status: 'pending',
  created_at: Timestamp
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
  --set-env-vars GCP_PROJECT_ID=project-9ed97ef0-254a-4ec3-975,VERTEX_LOCATION=us-central1,FIRESTORE_DATABASE=dangenai-skills,WEBHOOK_URL=https://asia-northeast3-project-9ed97ef0-254a-4ec3-975.cloudfunctions.net/handle-skill
```

### webhook (Cloud Functions)

```bash
gcloud functions deploy handle-skill \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --region asia-northeast3 \
  --source webhook/ \
  --set-env-vars GCP_PROJECT_ID=project-9ed97ef0-254a-4ec3-975,FIRESTORE_DATABASE=dangenai-skills
```

---

## 테스트 시나리오 (test_consumer_flow.py)

```bash
python test_consumer_flow.py                          # 전체 (4개 단일 점포 + 근처 라우팅)
python test_consumer_flow.py --scenario laundry       # 세탁소
python test_consumer_flow.py --scenario restaurant    # 음식 배달
python test_consumer_flow.py --scenario beauty        # 미용실
python test_consumer_flow.py --scenario hospital      # 병원
python test_consumer_flow.py --scenario nearby        # 지역별 멀티 점포 라우팅 데모
python test_consumer_flow.py --skip-create-skill      # 스킬 생성 건너뜀
```

`nearby` 시나리오는 강남·마포·종로 세 점포를 동시에 Gemini에 올려서,  
사용자 발화의 지역명만으로 올바른 점포로 라우팅되는지 검증합니다.

---

## 데모 시나리오 (5분)

### A. 사장님 Skill 생성 (1분)
1. `POST /create-skill` — `"세탁물 수거 신청, 주소랑 날짜 받아야 해"` 입력
2. Gemini가 스킬 스펙 실시간 생성 → Firestore 저장 확인

### B. TV 음성 주문 + 근처 점포 라우팅 (2분)
1. TV에 야구 중계 화면
2. AgentBubble: **"치킨 시킬까요? 근처 당그나이치킨이 있어요"**
3. "응, 주문해줘" → Gemini Function Calling → 점포 자동 매칭
4. 사장님 폰에 FCM 알림 도착

### C. 메뉴판 사진 입점 (1분)
1. `POST /extract-menu` — 메뉴판 이미지 업로드
2. Gemini Vision 5초 안에 메뉴 자동 추출 → Firestore 저장

### D. 멀티 점포 라우팅 강조 (1분)
- `python test_consumer_flow.py --scenario nearby` 출력 화면 공유
- "강남구 역삼동" → 강남 세탁소, "합정동" → 마포 세탁소 라우팅 시연

---

## 실패 대비 플랜

| 장애 상황 | 대응 방법 |
|---|---|
| GCP API 장애 | `mock_skill_engine.py` 로컬 실행 (`uvicorn mock_skill_engine:app --port 8080`) |
| FCM 알림 불발 | `owner-app/` 에서 토큰 재등록 또는 화면 캡처로 대체 |
| 음성 인식 실패 | 버튼 클릭으로 동일 플로우 트리거 |
| Gemini 응답 느림 | 스트리밍 UI + 응답 캐싱으로 체감 시간 단축 |
| 전체 시스템 다운 | 사전 녹화 데모 영상 재생 |

---

## 자주 쓰는 질문 패턴

```
# 에러 발생 시
이 에러 고쳐줘: [에러 메시지 붙여넣기]

# 스킬 스펙 조정
skill_gen.py의 SYSTEM_PROMPT에서 파라미터 개수 제한 방식 바꿔줘

# 새 시나리오 추가
test_consumer_flow.py에 꽃배달 시나리오 추가해줘

# 배포
skill-engine Cloud Run 재배포해줘
```
