import sqlite3
import os
import json
from datetime import datetime

DB_NAME = 'trades.db'
# Render Persistent Disk / 컨테이너 환경 고려
if os.path.exists('/app/data'):
    DB_NAME = '/app/data/trades.db'
elif os.environ.get("DATABASE_PATH"):
    DB_NAME = os.environ.get("DATABASE_PATH")

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 진행한 거래 로깅
    c.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        action TEXT NOT NULL,  -- 'BUY' or 'SELL'
        price REAL,
        qty INTEGER,
        status TEXT, -- 'PENDING', 'SUCCESS', 'FAILED', 'CANCELLED'
        order_no TEXT, -- KIS 주문번호
        ai_reason TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 조건검색 스캐너 및 AI 판독 결과 로깅
    c.execute('''CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT NOT NULL,
        scan_reason TEXT,
        ai_decision TEXT, -- 'PASS', 'BUY', 'HOLD'
        ai_reason TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

def log_scan(stock_code, scan_reason, ai_decision, ai_reason):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO scans (stock_code, scan_reason, ai_decision, ai_reason) 
                 VALUES (?, ?, ?, ?)''', (stock_code, scan_reason, ai_decision, ai_reason))
    conn.commit()
    scan_id = c.lastrowid
    conn.close()
    return scan_id

def log_trade(stock_code, stock_name, action, price, qty, status, ai_reason, order_no=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO trades (stock_code, stock_name, action, price, qty, status, ai_reason, order_no) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (stock_code, stock_name, action, price, qty, status, ai_reason, order_no))
    conn.commit()
    trade_id = c.lastrowid
    conn.close()
    return trade_id

def update_trade_status(trade_id, status, price=None):
    conn = get_connection()
    c = conn.cursor()
    if price:
        c.execute('UPDATE trades SET status = ?, price = ? WHERE id = ?', (status, price, trade_id))
    else:
        c.execute('UPDATE trades SET status = ? WHERE id = ?', (status, trade_id))
    conn.commit()
    conn.close()

def get_recent_scans(limit=50):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM scans ORDER BY timestamp DESC LIMIT ?', (limit,))
    columns = [column[0] for column in c.description]
    results = []
    for row in c.fetchall():
        results.append(dict(zip(columns, row)))
    conn.close()
    return results

def get_recent_trades(limit=50):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?', (limit,))
    columns = [column[0] for column in c.description]
    results = []
    for row in c.fetchall():
        results.append(dict(zip(columns, row)))
    conn.close()
    return results

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
