export default function AgentBubble({ message, onOrder, onDismiss }) {
  return (
    <div style={{
      position: 'fixed', bottom: 80, right: 60,
      background: '#fff', borderRadius: 20, padding: '28px 36px',
      boxShadow: '0 12px 40px rgba(0,0,0,0.35)',
      maxWidth: 440, zIndex: 100,
      animation: 'slideInRight 0.45s cubic-bezier(.22,.68,0,1.2)',
    }}>
      {/* 말풍선 꼬리 */}
      <div style={{
        position: 'absolute', bottom: -14, right: 60,
        width: 0, height: 0,
        borderLeft: '14px solid transparent',
        borderRight: '14px solid transparent',
        borderTop: '14px solid #fff',
      }} />

      {/* AI 아이콘 + 텍스트 */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 22 }}>
        <div style={{
          width: 46, height: 46, borderRadius: '50%', flexShrink: 0,
          background: 'linear-gradient(135deg, #FF6B35, #FF8C42)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22,
        }}>
          🤖
        </div>
        <p style={{ fontSize: 26, lineHeight: 1.5, margin: 0, color: '#1a1a1a' }}>
          {message}
        </p>
      </div>

      {/* 버튼 */}
      <div style={{ display: 'flex', gap: 12 }}>
        <button onClick={onOrder} style={{
          flex: 2, padding: '14px 0', fontSize: 24, fontWeight: 'bold',
          background: '#FF6B35', color: '#fff', border: 'none',
          borderRadius: 10, cursor: 'pointer',
        }}>
          네, 주문할게요
        </button>
        <button onClick={onDismiss} style={{
          flex: 1, padding: '14px 0', fontSize: 24,
          background: '#f0f0f0', color: '#555', border: 'none',
          borderRadius: 10, cursor: 'pointer',
        }}>
          괜찮아요
        </button>
      </div>
    </div>
  )
}
