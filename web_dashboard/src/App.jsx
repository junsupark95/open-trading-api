import { useState, useEffect } from 'react';

function App() {
  const [status, setStatus] = useState({
    is_running: false,
    market_mode: "INITIALIZING",
    is_market_open: false,
    total_asset: 0,
    p_l_amt: 0,
    p_l_ratio: 0,
    seed_money: 0,
    total_scans: 0,
    last_scan_time: null
  });
  const [scans, setScans] = useState([]);
  const [trades, setTrades] = useState([]);
  const [logs, setLogs] = useState("AI Engine starting up...");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [resStatus, resScans, resTrades, resLogs] = await Promise.all([
          fetch('/api/status'),
          fetch('/api/scans?limit=10'),
          fetch('/api/trades?limit=5'),
          fetch('/api/logs')
        ]);

        if (resStatus.ok) setStatus(await resStatus.json());
        if (resScans.ok) setScans(await resScans.json());
        if (resTrades.ok) setTrades(await resTrades.json());
        if (resLogs.ok) setLogs(await resLogs.text());
      } catch (err) {
        console.error("Fetch Error:", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getMarketStatusLabel = () => {
    switch (status.market_mode) {
      case "OPEN": return { label: "한국 장중", className: "status-open" };
      case "PRE_MARKET": return { label: "장전 대기", className: "status-ready" };
      case "WEEKEND_REST": return { label: "주말 휴식", className: "status-closed" };
      default: return { label: "장마감/휴장", className: "status-closed" };
    }
  };

  const marketInfo = getMarketStatusLabel();

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div style={{ padding: '8px 0', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '32px', height: '32px', background: 'var(--brand-blue)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ fontSize: '1.2rem' }}>⚡</span>
          </div>
          <h1>NeuroTrade <span style={{ color: 'var(--brand-blue)' }}>AI</span></h1>
        </div>

        <div className="glass-panel">
          <h3>시스템 상태</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '16px 0 24px' }}>
            {status.is_running && <div className="pulse"></div>}
            <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>
              {status.is_running ? "엔진 가동중" : "엔진 정지"}
            </span>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="stat-label">시장 세션</span>
              <span className={`status-badge ${marketInfo.className}`}>{marketInfo.label}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="stat-label">AI 스캔</span>
              <span style={{ fontWeight: 600 }}>{status.total_scans}회</span>
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3>최근 체결</h3>
            <span style={{ fontSize: '0.7rem', color: 'var(--brand-blue)', fontWeight: 700 }}>LIVE</span>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
            {trades.map((t, idx) => (
              <div key={idx} className="trade-item">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 700 }}>{t.stock_name || t.stock_code}</span>
                  <span style={{ color: t.action === 'BUY' ? 'var(--brand-red)' : 'var(--brand-blue)', fontSize: '0.75rem', fontWeight: 800 }}>
                    {t.action === 'BUY' ? '매수' : '매도'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <span className="stat-label">{t.timestamp?.substring(11, 16)}</span>
                  <span style={{ fontWeight: 700 }}>{t.qty}주 · {(t.price || 0).toLocaleString()}원</span>
                </div>
              </div>
            ))}
            {trades.length === 0 && <div style={{ color: 'var(--text-tertiary)', fontSize: '0.8rem', textAlign: 'center', marginTop: '40px' }}>데이터가 없습니다.</div>}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div className="glass-panel">
            <span className="stat-label">총 평가 자산</span>
            <div className="stat-value">₩{(status.total_asset || 0).toLocaleString()}</div>
            <div style={{ color: status.p_l_amt >= 0 ? 'var(--brand-red)' : 'var(--brand-blue)', fontWeight: 700, fontSize: '0.9rem' }}>
              {status.p_l_amt >= 0 ? '+' : ''}{status.p_l_amt?.toLocaleString()}원 ({status.p_l_ratio}%)
            </div>
          </div>
          <div className="glass-panel">
            <span className="stat-label">투자 원금 (Seed)</span>
            <div className="stat-value" style={{ fontSize: '1.5rem', marginTop: '16px' }}>₩{(status.seed_money || 0).toLocaleString()}</div>
            <div className="stat-label" style={{ marginTop: '8px' }}>매수 대기 자금 포함</div>
          </div>
        </div>

        {!status.is_market_open && (
          <div className="glass-panel" style={{ background: 'hsla(214, 91%, 60%, 0.05)', borderColor: 'hsla(214, 91%, 60%, 0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '1.5rem' }}>🌙</span>
              <div>
                <p style={{ fontWeight: 700 }}>현재는 시장 휴식 시간입니다.</p>
                <p className="stat-label">엔진이 대기 상태이며, 오전 08:30에 자동으로 활동을 시작합니다.</p>
              </div>
            </div>
          </div>
        )}

        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>AI 실시간 스캐너</h2>
            <div style={{ background: 'hsla(0, 0%, 100%, 0.05)', padding: '6px 12px', borderRadius: '8px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              알고리즘: Ross Cameron Momentum
            </div>
          </div>
          
          <div style={{ flex: 1, overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>종목</th>
                  <th>시간</th>
                  <th>판단</th>
                  <th>AI 리포트</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((scan, idx) => (
                  <tr key={idx}>
                    <td data-label="종목" style={{ fontWeight: 800 }}>{scan.stock_code}</td>
                    <td data-label="시간" style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                      {new Date(scan.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td data-label="판단">
                      <span className={`badge ${scan.ai_decision === 'BUY' ? 'badge-buy' : 'badge-hold'}`}>
                        {scan.ai_decision === 'BUY' ? '적극 매수' : '관망'}
                      </span>
                    </td>
                    <td data-label="리포트" className="stat-label" style={{ maxWidth: '400px', lineHeight: '1.5' }}>
                      {scan.ai_reason}
                    </td>
                  </tr>
                ))}
                {scans.length === 0 && <tr><td colSpan="4" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>스캔 내역이 없습니다.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
             <h3>System Engine Console</h3>
             <button onClick={() => setLogs("")} style={{ background: 'none', border: 'none', color: 'var(--brand-blue)', fontSize: '0.7rem', cursor: 'pointer', fontWeight: 700 }}>CLEAR</button>
          </div>
          <pre className="console">{logs}</pre>
        </div>
      </main>
    </div>
  );
}

export default App;
