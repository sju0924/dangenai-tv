import { useState, useEffect } from 'react'

const SCORE = { home: '두산', away: 'LG', h: 3, a: 2, inning: '7회 말' }

export default function TVHome() {
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#0d1f14' }}>
      {/* 야구장 배경 */}
      <div style={{
        width: '100%', height: '100%',
        background: 'radial-gradient(ellipse at 50% 70%, #2d7a4f 0%, #1a4a2e 55%, #0d1f14 100%)',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        {/* 다이아몬드 */}
        <div style={{ position: 'relative', width: 220, height: 220, marginBottom: 32 }}>
          <div style={diamond('#8B6914', 85, 85, 50, 50)} />
          <div style={base(88, 0)} />
          <div style={base(170, 88)} />
          <div style={base(88, 170)} />
          <div style={base(6, 88)} />
        </div>

        <div style={{ color: '#fff', fontSize: 22, letterSpacing: 6, opacity: 0.6, marginBottom: 12 }}>
          KBO 리그 LIVE
        </div>

        {/* 점수판 */}
        <div style={{
          display: 'flex', gap: 32, alignItems: 'center',
          background: 'rgba(0,0,0,0.6)', padding: '18px 48px', borderRadius: 16,
        }}>
          <TeamScore name={SCORE.home} score={SCORE.h} />
          <span style={{ color: '#aaa', fontSize: 32 }}>:</span>
          <TeamScore name={SCORE.away} score={SCORE.a} />
        </div>
        <div style={{ color: '#aaa', fontSize: 22, marginTop: 12 }}>{SCORE.inning}</div>
      </div>

      {/* 좌상단 — 채널/시간 */}
      <div style={{
        position: 'absolute', top: 28, left: 36,
        background: 'rgba(0,0,0,0.7)', color: '#fff',
        padding: '10px 22px', borderRadius: 8, fontSize: 22,
      }}>
        📺 KBO TV &nbsp;|&nbsp; {time.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
      </div>

      {/* 우상단 — LIVE 뱃지 */}
      <div style={{
        position: 'absolute', top: 28, right: 36,
        background: '#e53935', color: '#fff',
        padding: '10px 22px', borderRadius: 8, fontSize: 22, fontWeight: 'bold',
        animation: 'pulse 2s ease-in-out infinite',
      }}>
        ● LIVE
      </div>
    </div>
  )
}

function TeamScore({ name, score }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ color: '#ccc', fontSize: 24, marginBottom: 4 }}>{name}</div>
      <div style={{ color: '#fff', fontSize: 56, fontWeight: 'bold', lineHeight: 1 }}>{score}</div>
    </div>
  )
}

function diamond(color, top, left, w, h) {
  return {
    position: 'absolute', top, left, width: w, height: h,
    background: color, transform: 'rotate(45deg)', borderRadius: 4,
  }
}
function base(top, left) {
  return {
    position: 'absolute', top, left, width: 18, height: 18,
    background: '#fff', transform: 'rotate(45deg)', borderRadius: 2,
  }
}
