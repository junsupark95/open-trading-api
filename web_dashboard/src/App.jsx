import { useState, useEffect } from 'react';

function App() {
  const [status, setStatus] = useState({
    is_running: true,
    last_scan_time: "방금 전",
    total_scans: 124,
    total_trades: 3
  });
  const [scans, setScans] = useState([
    { id: 1, stock_code: "005930", scan_reason: "Condition Search Match", ai_decision: "BUY", ai_reason: "강한 거래량 동반 전고점 돌파 확인", timestamp: "10:15 AM" },
    { id: 2, stock_code: "035420", scan_reason: "Condition Search Match", ai_decision: "HOLD", ai_reason: "저항선에 부딪혀 모멘텀 둔화", timestamp: "10:13 AM" }
  ]);
  const [trades, setTrades] = useState([
    { id: 1, stock_name: "삼성전자", action: "BUY", price: 84500, qty: 10, status: "SUCCESS", timestamp: "10:15 AM" }
  ]);
  const [logs, setLogs] = useState("AI Engine Logs will appear here...");

  // 추후 FastAPI 연동 활성화
  useEffect(() => {
    const fetchData = async () => {
      try {
        const resStatus = await fetch('/api/status');
        if (resStatus.ok) setStatus(await resStatus.json());
        
        const resScans = await fetch('/api/scans?limit=5');
        if (resScans.ok) setScans(await resScans.json());

        const resTrades = await fetch('/api/trades?limit=5');
        if (resTrades.ok) setTrades(await resTrades.json());

        const resLogs = await fetch('/api/logs');
        if (resLogs.ok) setLogs(await resLogs.text());
      } catch (err) {
        console.warn("Backend not reachable or CORS issue. Displaying placeholder data.");
      }
    };
    
    fetchData();
    const intervalId = setInterval(fetchData, 3000);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <div className="sidebar">
        <div style={{ padding: '10px 0', marginBottom: '10px' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#3182F6', letterSpacing: '-0.03em' }}>
            NeuroTrade <span style={{ color: '#fff' }}>AI</span>
          </h2>
        </div>

        <div className="glass-panel">
          <h3 className="text-xs text-dim" style={{ marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            시스템 상태
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <div className="pulse" style={{ width: '10px', height: '10px' }}></div>
            <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>{status.is_running ? "운영 중" : "정지됨"}</span>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="text-sm text-dim">현재 모드</span>
              <span className="badge-green" style={{ background: '#3182F620', color: '#3182F6' }}>{status.market_mode || "대기"}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-sm text-dim">스캔 횟수</span>
              <span className="text-sm" style={{ fontWeight: 600 }}>{status.total_scans}회</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-sm text-dim">최근 스캔</span>
              <span className="text-sm">{status.last_scan_time ? new Date(status.last_scan_time).toLocaleTimeString() : "-"}</span>
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <h3 className="text-xs text-dim" style={{ marginBottom: '16px', textTransform: 'uppercase' }}>
            최근 체결 내역
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', paddingRight: '4px' }}>
            {trades.map((t, idx) => (
              <div key={idx} style={{ padding: '14px', background: 'var(--bg-card)', borderRadius: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 700 }}>{t.stock_name}</span>
                  <span className={t.status === 'SUCCESS' ? 'text-blue' : 'text-dim'} style={{ fontSize: '0.75rem', fontWeight: 600 }}>
                    {t.status === 'SUCCESS' ? '체결완료' : '대기중'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                  <span className="text-xs text-dim">{t.timestamp?.substring(11, 16)}</span>
                  <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>{t.qty}주 · {(t.price || 0).toLocaleString()}원</span>
                </div>
              </div>
            ))}
            {trades.length === 0 && <div className="text-dim text-xs" style={{ textAlign: 'center', marginTop: '20px' }}>매매 내역이 없습니다.</div>}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <div className="grid-2">
          {/* Asset Info Card */}
          <div className="glass-panel" style={{ background: 'var(--bg-card)', border: 'none' }}>
            <span className="text-sm text-dim" style={{ marginBottom: '12px', display: 'block' }}>총 평가 자산</span>
            <div className="text-3xl" style={{ marginBottom: '8px' }}>
              ₩{(status.total_asset || status.current_balance || 0).toLocaleString()}
            </div>
            <div className={`text-sm ${status.p_l_amt >= 0 ? 'text-red' : 'text-blue'}`} style={{ fontWeight: 700 }}>
              {status.p_l_amt >= 0 ? '▲' : '▼'} ₩{Math.abs(status.p_l_amt || 0).toLocaleString()} ({status.p_l_ratio || "0.00"}%)
            </div>
          </div>

          {/* Seed Info Card */}
          <div className="glass-panel">
            <span className="text-sm text-dim" style={{ marginBottom: '12px', display: 'block' }}>투자 원금 (Seed)</span>
            <div className="text-xl" style={{ fontWeight: 700, marginBottom: '4px' }}>
              ₩{(status.seed_money || 0).toLocaleString()}
            </div>
            <div className="text-xs text-dim">
              매수 대기 자금 포함
            </div>
          </div>
        </div>

        {/* AI Scanner Feed Table */}
        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2 className="text-lg">AI 실시간 포착 리스트</h2>
            <span className="badge-green" style={{ background: 'rgba(49, 130, 246, 0.1)', color: '#3182F6' }}>Ross Cameron 전략</span>
          </div>
          
          <div style={{ overflowX: 'auto', flex: 1 }}>
            <table style={{ minWidth: '600px' }}>
              <thead>
                <tr>
                  <th>종목코드</th>
                  <th>포착시간</th>
                  <th>AI 판단</th>
                  <th>분석 리포트</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((scan, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 700, color: '#fff' }}>{scan.stock_code}</td>
                    <td className="text-dim text-xs">{new Date(scan.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                    <td>
                      <span className={scan.ai_decision === 'BUY' ? 'badge-green' : 'badge-red'} 
                            style={scan.ai_decision === 'BUY' ? {background: 'rgba(240, 68, 82, 0.1)', color: '#F04452'} : {}}>
                        {scan.ai_decision === 'BUY' ? '매수 추천' : '관망(HOLD)'}
                      </span>
                    </td>
                    <td className="text-dim" style={{ fontSize: '0.85rem', maxWidth: '400px' }}>
                      {scan.ai_reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Logs Section */}
        <div className="glass-panel console-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
             <h3 className="text-xs text-dim" style={{ textTransform: 'uppercase' }}>Live System Logs</h3>
             <span className="text-xs text-dim">ai_engine.log</span>
          </div>
          <pre className="log-content">
            {logs}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default App;
