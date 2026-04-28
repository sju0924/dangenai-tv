# 당그나이TV 개발환경 설정 가이드

> 팀원 온보딩용. GCP 인프라(Cloud Run, Cloud Functions, Firestore)는 이미 배포 완료 상태.  
> 로컬 개발환경 세팅 + TV UI 실행까지가 목표.

---

## 사전 준비

| 도구 | 버전 | 설치 |
|---|---|---|
| Python | 3.11+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| gcloud CLI | 최신 | https://cloud.google.com/sdk/docs/install |
| Git | 최신 | https://git-scm.com |

---

## 1. 레포 클론

```bash
git clone https://github.com/sju0924/dangenai-tv.git
cd dangenai-tv
```

---

## 2. GCP 인증 설정

> ⚠️ 조직 정책(`iam.disableServiceAccountKeyCreation`)으로 SA 키 발급이 차단되어 있습니다.  
> SA 키 파일 대신 **Application Default Credentials(ADC)** 방식을 사용합니다.

```bash
gcloud auth login
gcloud config set project qwiklabs-gcp-04-4818f049b9ca

# ADC 설정 — Vertex AI·Firestore SDK 인증에 필요 (이 명령어가 핵심)
gcloud auth application-default login
```

브라우저에서 Google 계정 로그인하면 완료입니다.

### GCP 프로젝트 접근 권한

대회 당일 받으면 거기다 올려요

---

## 3. Python 환경 설정

```bash
cd skill-engine
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 4. 환경변수 설정

```bash
cd skill-engine
cp .env.example .env
```

`.env` 내용:

```env
GCP_PROJECT_ID=qwiklabs-gcp-04-4818f049b9ca
VERTEX_LOCATION=us-central1
FIRESTORE_DATABASE=dangenai-skills
WEBHOOK_URL=https://us-central1-qwiklabs-gcp-04-4818f049b9ca.cloudfunctions.net/handle-skill
SKILL_ENGINE_URL=https://skill-engine-314814367176.us-central1.run.app

# SA 키 대신 ADC 사용: gcloud auth application-default login
# GOOGLE_APPLICATION_CREDENTIALS=../sa-key.json
```

---

## 5. 배포된 인프라 확인

이미 배포 완료된 GCP 리소스입니다. 별도 배포 불필요.

| 리소스 | URL |
|---|---|
| skill-engine (Cloud Run) | `https://skill-engine-314814367176.us-central1.run.app` |
| webhook (Cloud Functions) | `https://us-central1-qwiklabs-gcp-04-4818f049b9ca.cloudfunctions.net/handle-skill` |
| dashboard-agent (Cloud Run) | `https://dashboard-agent-314814367176.us-central1.run.app` |
| Firestore DB | `dangenai-skills` (nam5) |

헬스체크:
```bash
curl https://skill-engine-314814367176.us-central1.run.app/health
# → {"status":"ok"}
```

---

## 6. 스킬 생성 테스트 (로컬)

```bash
cd skill-engine

# Gemini + 유효성 검사만 (Firestore 저장 없음)
python test_create_skill.py

# Firestore 저장까지 전체 테스트
python test_create_skill.py --full
```

성공 출력:
```
[PASS] 1단계 — 스펙 생성 성공
[PASS] 2단계 — 유효성 검사 통과
[PASS] 3단계 — Firestore 저장 성공
```

---

## 7. 소비자 주문 흐름 E2E 테스트

프로젝트 루트에서 실행합니다.

```bash
# 전체 시나리오 (단일 점포 4개 + 근처 라우팅 1개)
python test_consumer_flow.py

# 특정 시나리오만
python test_consumer_flow.py --scenario laundry      # 세탁소
python test_consumer_flow.py --scenario restaurant   # 음식 배달
python test_consumer_flow.py --scenario beauty       # 미용실
python test_consumer_flow.py --scenario hospital     # 병원
python test_consumer_flow.py --scenario nearby       # 지역별 멀티 점포 라우팅

# 스킬이 Firestore에 이미 있으면 생성 건너뜀
python test_consumer_flow.py --skip-create-skill
```

정상 흐름 (단일 점포):
```
✅ 스킬 저장: [laundry_pickup] → stores/store_laundry
✅ 스킬 매칭 성공
   ▶ 매칭 스킬 : [laundry_pickup]
     파라미터  : {"address": "강남구 역삼동", "pickup_date": "내일"}
✅ Firestore 주문 저장: order_id=...
```

`nearby` 시나리오 출력 예시:
```
  [1] 강남구 역삼동으로 내일 세탁물 수거해줘
         ▶ 매칭 스킬 : [gangnam_laundry_pickup]
         점포명   : 강남 당그나이 세탁소 (강남구·서초구·송파구)

  [2] 합정동인데 세탁물 수거 신청하고 싶어요
         ▶ 매칭 스킬 : [mapo_laundry_pickup]
         점포명   : 마포 당그나이 세탁소 (마포구·서대문구·은평구)
```

> **FCM 알림까지 받으려면**: 아래 8단계에서 `owner_fcm_token`을 등록해야 합니다.  
> 토큰 없으면 webhook이 `400 FCM 토큰 없음`을 반환합니다 — 주문 저장은 정상입니다.

---

## 8. FCM 토큰 등록 (사장님 알림 설정)

### 8-1. Firebase Console 설정

1. [Firebase Console](https://console.firebase.google.com) → 프로젝트 추가 → **기존 Google Cloud 프로젝트 사용** → `qwiklabs-gcp-04-4818f049b9ca`
2. **웹 앱 추가** (`</>`) → 앱 닉네임: `dangenai-owner` → Firebase 설정 객체 복사
3. **프로젝트 설정** → **클라우드 메시징** 탭 → **웹 푸시 인증서** → **키 쌍 생성** (VAPID 키 복사)

### 8-2. owner-app 환경변수 설정

민감 정보는 `config.js` / `sw-env.js`로 분리해 관리합니다 (두 파일 모두 git-ignored).

```bash
cd owner-app
cp config.js.example config.js
cp sw-env.js.example sw-env.js
```

`config.js` 에 실제 값 채우기:

```js
window.ENV = {
  FIREBASE_API_KEY:  "Firebase 설정의 apiKey",
  FIREBASE_APP_ID:   "Firebase 설정의 appId",
  VAPID_KEY:         "8-1에서 복사한 VAPID 키",
  SKILL_ENGINE_URL:  "https://skill-engine-314814367176.us-central1.run.app",
};
```

`sw-env.js` 에 실제 값 채우기:

```js
const SW_ENV = {
  FIREBASE_API_KEY: "Firebase 설정의 apiKey",
  FIREBASE_APP_ID:  "Firebase 설정의 appId",
};
```

### 8-3. 로컬 서버 실행 및 토큰 발급

Service Worker는 HTTPS 또는 localhost에서만 동작합니다.

```bash
cd owner-app
python -m http.server 8081
```

브라우저에서 `http://localhost:8081` 열기 → **알림 허용 및 토큰 등록** 클릭  
→ `stores/{store_id}.owner_fcm_token` 에 자동 저장됩니다.

---

## 9. 로컬 skill-engine 실행 (선택)

```bash
# 목업 서버 — GCP 인증 불필요, TV UI 데모용
uvicorn mock_skill_engine:app --port 8080 --reload

# 실제 서버 — GCP 인증(ADC) 필요
cd skill-engine
uvicorn main:app --port 8080 --reload
```

---

## 10. TV UI 실행

```bash
cd tv-ui
npm install
cp .env.example .env
```

`tv-ui/.env`:
```env
# 목업 서버 사용 시 (기본값)
VITE_SKILL_ENGINE_URL=http://localhost:8080
VITE_DEMO_MODE=true

# 실제 Cloud Run 연결 시
# VITE_SKILL_ENGINE_URL=https://skill-engine-314814367176.us-central1.run.app
# VITE_DEMO_MODE=false
```

```bash
npm run dev
# → http://localhost:3000
```

브라우저에서 열면:
1. 야구 중계 화면 표시
2. 4초 후 치킨 주문 말풍선 등장
3. "네, 주문할게요" 클릭 → 주문 확인 카드
4. "주문하기" → 완료

---

## 프로젝트 구조

```
dangenai-tv/
├── skill-engine/              # Cloud Run — FastAPI 백엔드
│   ├── main.py                # /create-skill /chat /order /extract-menu /register-fcm-token
│   ├── skill_gen.py           # Gemini로 스킬 스펙 자동 생성
│   ├── agent_binder.py        # 스펙 유효성 검사
│   ├── firestore_client.py    # Firestore CRUD (save_skill은 upsert)
│   ├── test_create_skill.py   # 스킬 생성 단계별 테스트
│   └── requirements.txt
├── webhook/                   # Cloud Functions — FCM 알림 발송
│   ├── main.py
│   └── requirements.txt
├── owner-app/                 # 사장님 FCM 토큰 등록 페이지
│   ├── index.html
│   └── firebase-messaging-sw.js
├── tv-ui/                     # React TV 앱 (Vite)
│   └── src/
│       ├── App.jsx
│       └── components/
├── mock_skill_engine.py       # GCP 없이 로컬 데모용 목업 서버
└── test_consumer_flow.py      # 소비자 주문 흐름 E2E 테스트 (5개 시나리오)
```

---

## 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `DefaultCredentialsError` | ADC 미설정 | `gcloud auth application-default login` 실행 |
| `스킬 생성 실패 HTTP 500` | Firestore 문서 없음 또는 Vertex AI 권한 없음 | Cloud Run 로그 확인: `gcloud run services logs read skill-engine --region us-central1` |
| `NotFound: 404 database does not exist` | Firestore DB 이름 불일치 | `.env`의 `FIRESTORE_DATABASE=dangenai-skills` 확인 |
| `400 FCM 토큰 없음` | `owner_fcm_token` 필드 없음 | `owner-app/` 에서 토큰 등록 (8단계) |
| `400 Duplicate function declaration` | Firestore에 같은 tool_name 중복 저장됨 | `--skip-create-skill` 없이 재실행 (upsert로 자동 정리) |
| `ValueError: Filter must be provided` | 구버전 Firestore 쿼리 문법 | `FieldFilter("store_id", "==", ...)` 사용 확인 |
| `Permission denied` | GCP IAM 권한 없음 | 팀장에게 IAM 추가 요청 |
| TV UI 빈 화면 | `npm install` 누락 | `tv-ui/` 에서 `npm install` 실행 |
| SA 키 발급 불가 | 조직 정책 `iam.disableServiceAccountKeyCreation` | ADC 방식 사용 (`gcloud auth application-default login`) |
