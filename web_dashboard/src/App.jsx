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
        <div style={{ marginBottom: '16px' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            NEUROTRADE <span className="text-green">AI</span>
          </h2>
        </div>

        <div className="glass-panel">
          <h3 className="text-sm text-dim" style={{ marginBottom: '16px', textTransform: 'uppercase' }}>
            AI Trading Status
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
            <span className="pulse"></span>
            <span className="text-green" style={{ fontWeight: 600 }}>{status.is_running ? "Active" : "Stopped"}</span>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-sm text-dim">Strategy</span>
              <span className="text-sm" style={{ fontWeight: 500 }}>MOMENTUM</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-sm text-dim">Total Scans</span>
              <span className="text-sm text-green">{status.total_scans}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-sm text-dim">Last Scan</span>
              <span className="text-sm">{status.last_scan_time?.substring(11, 19) || "-"}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="text-sm text-dim">Mode</span>
              <span className="badge-green" style={{ fontSize: '10px' }}>{status.market_mode || "STANDBY"}</span>
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ flex: 1 }}>
          <h3 className="text-sm text-dim" style={{ marginBottom: '16px', textTransform: 'uppercase' }}>
            Recent Trades
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {trades.map((t, idx) => {
              const getStatusLael = (status, action) => {
                if (status === 'PENDING') return action === 'BUY' ? '매수중' : '매매중';
                if (status === 'SUCCESS') return action === 'BUY' ? '매수완료' : '매도완료';
                if (status === 'FAILED') return '실패';
                return status;
              };
              const getStatusClass = (status) => {
                if (status === 'PENDING') return 'badge-orange pulse';
                if (status === 'SUCCESS') return 'badge-green';
                return 'badge-red';
              };
              
              return (
                <div key={idx} style={{ paddingBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600 }}>{t.stock_name}</span>
                    <span className={getStatusClass(t.status)}>{getStatusLael(t.status, t.action)}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="text-xs text-dim">{(t.price || 0).toLocaleString()}원</span>
                    <span className="text-xs text-dim">{t.qty}주</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <h1 className="text-2xl" style={{ marginBottom: '8px' }}>Overview</h1>
        
        <div className="grid-2">
          {/* Portfolio Card */}
          <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <span className="text-sm text-dim" style={{ marginBottom: '8px' }}>Total Portfolio Value (Mock)</span>
            <div className="text-3xl" style={{ marginBottom: '8px' }}>₩10,000,000</div>
            <div className="text-sm text-green" style={{ fontWeight: 500 }}>
              +0.00% (+₩0) today
            </div>
          </div>

          {/* Today's Net P/L */}
          <div className="glass-panel" style={{ background: 'rgba(0, 255, 157, 0.05)', borderColor: 'rgba(0, 255, 157, 0.2)' }}>
            <span className="text-sm text-dim" style={{ marginBottom: '8px' }}>Executed Trades</span>
            <div className="text-3xl text-green" style={{ marginBottom: '8px' }}>{status.total_trades}</div>
            <div className="text-sm text-green" style={{ opacity: 0.8 }}>
              Active positions controlled by AI
            </div>
          </div>
        </div>

        {/* AI Scanner Feed Table */}
        <div className="glass-panel" style={{ flex: 1, overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
            <h2 className="text-lg">Gemini AI Scanned Stocks | <span className="text-dim text-sm" style={{ fontWeight: 400 }}>Ross Cameron Analysis</span></h2>
          </div>
          
          <table>
            <thead>
              <tr>
                <th>SYMBOL</th>
                <th>TIME</th>
                <th>AI DECISION</th>
                <th>AI REASONING</th>
              </tr>
            </thead>
            <tbody>
              {scans.map((scan, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 600 }}>{scan.stock_code}</td>
                  <td className="text-dim">{scan.timestamp?.substring(11, 19) || scan.timestamp}</td>
                  <td>
                    <span className={scan.ai_decision === 'BUY' ? 'badge-green' : (scan.ai_decision === 'HOLD' ? 'badge-red' : 'badge-red')}>
                      {scan.ai_decision}
                    </span>
                  </td>
                  <td className="text-dim" style={{ fontSize: '0.8rem', lineHeight: '1.4', padding: '12px 0' }}>
                    {scan.ai_reason}
                  </td>
                </tr>
              ))}
              {scans.length === 0 && (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', color: '#888', paddingTop: '32px' }}>
                    No scanned stocks yet. Waiting for KIS Condition Search...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
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
