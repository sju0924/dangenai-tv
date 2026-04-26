const BAR_DELAYS = ['0s', '0.1s', '0.2s', '0.15s', '0.05s']

export default function VoiceIndicator({ active, transcript }) {
  return (
    <div style={{
      position: 'fixed', bottom: 28, left: '50%',
      transform: 'translateX(-50%)',
      background: active ? '#FF6B35' : 'rgba(20,20,20,0.75)',
      color: '#fff', padding: '14px 30px', borderRadius: 40,
      fontSize: 22, display: 'flex', alignItems: 'center', gap: 12,
      transition: 'background 0.3s', zIndex: 150,
      backdropFilter: 'blur(6px)',
      whiteSpace: 'nowrap',
    }}>
      <span style={{ fontSize: 26 }}>{active ? '🎤' : '🎙️'}</span>

      <span>
        {active
          ? (transcript || '듣고 있어요...')
          : '마이크를 눌러 말씀해 주세요'}
      </span>

      {active && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 3, height: 28 }}>
          {BAR_DELAYS.map((delay, i) => (
            <div key={i} style={{
              width: 4, background: '#fff', borderRadius: 2,
              animation: `wave 0.5s ease-in-out ${delay} infinite alternate`,
            }} />
          ))}
        </div>
      )}
    </div>
  )
}
