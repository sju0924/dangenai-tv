import { useState, useEffect, useRef } from 'react'
import TVHome from './components/TVHome'
import AgentBubble from './components/AgentBubble'
import OrderConfirmCard from './components/OrderConfirmCard'
import VoiceIndicator from './components/VoiceIndicator'

// 데모용 가게 정보
const DEMO_STORE = {
  id: 'store_dangnai_chicken',
  name: '당그나이치킨',
  description: '후라이드 + 양념 반반 세트',
  suggestion: '치킨 시킬까요? 근처 당그나이치킨이 영업 중이에요 🍗',
  items: [
    { name: '후라이드 치킨 (반)', price: 9000 },
    { name: '양념 치킨 (반)', price: 10000 },
    { name: '콜라 1.25L', price: 2500 },
  ],
}

const SKILL_ENGINE_URL = import.meta.env.VITE_SKILL_ENGINE_URL || 'http://localhost:8080'
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE !== 'false'

// 음성 인식 트리거 키워드
const ORDER_KEYWORDS = /주문|시켜|응|네|좋아|할게|부탁/

export default function App() {
  // phase: watching → bubble → confirm → success | error
  const [phase, setPhase] = useState('watching')
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [loading, setLoading] = useState(false)
  const recRef = useRef(null)

  // 4초 후 AgentBubble 표시
  useEffect(() => {
    const t = setTimeout(() => setPhase(p => p === 'watching' ? 'bubble' : p), 4000)
    return () => clearTimeout(t)
  }, [])

  // Web Speech API 초기화
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    const r = new SR()
    r.lang = 'ko-KR'
    r.continuous = false
    r.interimResults = true
    r.onresult = e => {
      const text = Array.from(e.results).map(r => r[0].transcript).join('')
      setTranscript(text)
      if (e.results[e.results.length - 1].isFinal) {
        setListening(false)
        if (ORDER_KEYWORDS.test(text)) setPhase('confirm')
      }
    }
    r.onerror = () => setListening(false)
    r.onend = () => setListening(false)
    recRef.current = r
  }, [])

  const startListening = () => {
    if (!recRef.current || listening) return
    setTranscript('')
    setListening(true)
    try { recRef.current.start() } catch { setListening(false) }
  }

  const handleConfirmOrder = async () => {
    setLoading(true)
    if (DEMO_MODE) {
      await new Promise(r => setTimeout(r, 1500))
      setPhase('success')
      setLoading(false)
      return
    }
    try {
      const res = await fetch(`${SKILL_ENGINE_URL}/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          store_id: DEMO_STORE.id,
          skill_name: 'chicken_order',
          parameters: {
            items: DEMO_STORE.items.map(i => i.name),
            total: DEMO_STORE.items.reduce((s, i) => s + i.price, 0),
          },
        }),
      })
      setPhase(res.ok ? 'success' : 'error')
    } catch {
      setPhase('error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', position: 'relative' }}>
      <TVHome />

      {phase === 'bubble' && (
        <>
          <AgentBubble
            message={DEMO_STORE.suggestion}
            onOrder={() => setPhase('confirm')}
            onDismiss={() => setPhase('watching')}
          />
          <div onClick={startListening} style={{ cursor: 'pointer' }}>
            <VoiceIndicator active={listening} transcript={transcript} />
          </div>
        </>
      )}

      {phase === 'confirm' && (
        <OrderConfirmCard
          store={DEMO_STORE}
          loading={loading}
          onConfirm={handleConfirmOrder}
          onCancel={() => setPhase('bubble')}
        />
      )}

      {phase === 'success' && (
        <div style={overlay}>
          <div style={card}>
            <div style={{ fontSize: 72 }}>✅</div>
            <h2 style={{ fontSize: 40, margin: '16px 0 8px' }}>주문 완료!</h2>
            <p style={{ fontSize: 26, color: '#666' }}>사장님 폰으로 알림을 보냈어요</p>
            <button
              onClick={() => { setPhase('watching'); setTimeout(() => setPhase('bubble'), 3000) }}
              style={btnPrimary}
            >
              확인
            </button>
          </div>
        </div>
      )}

      {phase === 'error' && (
        <div style={overlay}>
          <div style={card}>
            <div style={{ fontSize: 72 }}>⚠️</div>
            <h2 style={{ fontSize: 36, margin: '16px 0 8px' }}>연결 오류</h2>
            <p style={{ fontSize: 24, color: '#666' }}>백엔드 서버를 확인해주세요</p>
            <button onClick={() => setPhase('bubble')} style={btnPrimary}>돌아가기</button>
          </div>
        </div>
      )}
    </div>
  )
}

const overlay = {
  position: 'fixed', inset: 0,
  background: 'rgba(0,0,0,0.75)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 300, animation: 'fadeIn 0.3s ease',
}
const card = {
  background: '#fff', borderRadius: 24, padding: '52px 60px',
  textAlign: 'center', minWidth: 380,
}
const btnPrimary = {
  marginTop: 32, padding: '16px 52px', fontSize: 26, fontWeight: 'bold',
  background: '#FF6B35', color: '#fff', border: 'none',
  borderRadius: 12, cursor: 'pointer',
}
