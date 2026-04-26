export default function OrderConfirmCard({ store, loading, onConfirm, onCancel }) {
  const total = store.items.reduce((s, i) => s + i.price, 0)

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.72)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 200, animation: 'fadeIn 0.3s ease',
    }}>
      <div style={{
        background: '#fff', borderRadius: 24, padding: '48px 56px',
        minWidth: 500, maxWidth: 620, width: '90vw',
      }}>
        {/* 헤더 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 28 }}>
          <span style={{ fontSize: 44 }}>🛍️</span>
          <div>
            <h2 style={{ fontSize: 36, margin: 0 }}>{store.name}</h2>
            <p style={{ fontSize: 22, color: '#888', margin: '4px 0 0' }}>{store.description}</p>
          </div>
        </div>

        {/* 주문 항목 */}
        <div style={{ borderTop: '2px solid #f0f0f0', borderBottom: '2px solid #f0f0f0', padding: '12px 0' }}>
          {store.items.map((item, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '10px 0', fontSize: 24, color: '#333',
            }}>
              <span>{item.name}</span>
              <span style={{ fontWeight: 600 }}>{item.price.toLocaleString()}원</span>
            </div>
          ))}
        </div>

        {/* 합계 */}
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          padding: '16px 0 28px', fontSize: 28, fontWeight: 'bold',
        }}>
          <span>합계</span>
          <span style={{ color: '#FF6B35' }}>{total.toLocaleString()}원</span>
        </div>

        {/* 버튼 */}
        <div style={{ display: 'flex', gap: 14 }}>
          <button onClick={onCancel} disabled={loading} style={{
            flex: 1, padding: '18px 0', fontSize: 26,
            background: '#f0f0f0', color: '#555', border: 'none',
            borderRadius: 12, cursor: loading ? 'default' : 'pointer',
          }}>
            취소
          </button>
          <button onClick={onConfirm} disabled={loading} style={{
            flex: 2, padding: '18px 0', fontSize: 26, fontWeight: 'bold',
            background: loading ? '#ccc' : '#FF6B35', color: '#fff', border: 'none',
            borderRadius: 12, cursor: loading ? 'default' : 'pointer',
            transition: 'background 0.2s',
          }}>
            {loading ? '주문 중...' : '주문하기'}
          </button>
        </div>
      </div>
    </div>
  )
}
