import sqlite3
import os
import json
from datetime import datetime

# PostgreSQL 지원을 위한 라이브러리 (선택적 로드)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = DATABASE_URL and DATABASE_URL.startswith("postgres")

def get_connection():
    if IS_POSTGRES:
        # Supabase/PostgreSQL 연결
        return psycopg2.connect(DATABASE_URL)
    else:
        # 로컬 SQLite 연결
        db_path = 'trades.db'
        if os.path.exists('/app/data'):
            db_path = '/app/data/trades.db'
        elif os.environ.get("DATABASE_PATH"):
            db_path = os.environ.get("DATABASE_PATH")
        return sqlite3.connect(db_path, check_same_thread=False)

def get_cursor(conn):
    if IS_POSTGRES:
        return conn.cursor(cursor_factory=RealDictCursor)
    return conn.cursor()

def get_placeholder():
    return "%s" if IS_POSTGRES else "?"

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # 테이블 생성 쿼리 (PostgreSQL/SQLite 호환 처리)
    id_type = "SERIAL PRIMARY KEY" if IS_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    # trades 테이블
    c.execute(f'''CREATE TABLE IF NOT EXISTS trades (
        id {id_type},
        stock_code TEXT NOT NULL,
        stock_name TEXT,
        action TEXT NOT NULL,
        price REAL,
        qty INTEGER,
        status TEXT,
        order_no TEXT,
        ai_reason TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # scans 테이블
    c.execute(f'''CREATE TABLE IF NOT EXISTS scans (
        id {id_type},
        stock_code TEXT NOT NULL,
        scan_reason TEXT,
        ai_decision TEXT,
        ai_reason TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

def log_scan(stock_code, scan_reason, ai_decision, ai_reason):
    conn = get_connection()
    c = conn.cursor()
    p = get_placeholder()
    query = f"INSERT INTO scans (stock_code, scan_reason, ai_decision, ai_reason) VALUES ({p}, {p}, {p}, {p})"
    if IS_POSTGRES:
        query += " RETURNING id"
        c.execute(query, (stock_code, scan_reason, ai_decision, ai_reason))
        scan_id = c.fetchone()[0]
    else:
        c.execute(query, (stock_code, scan_reason, ai_decision, ai_reason))
        scan_id = c.lastrowid
    
    conn.commit()
    conn.close()
    return scan_id

def log_trade(stock_code, stock_name, action, price, qty, status, ai_reason, order_no=None):
    conn = get_connection()
    c = conn.cursor()
    p = get_placeholder()
    query = f"INSERT INTO trades (stock_code, stock_name, action, price, qty, status, ai_reason, order_no) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})"
    
    if IS_POSTGRES:
        query += " RETURNING id"
        c.execute(query, (stock_code, stock_name, action, price, qty, status, ai_reason, order_no))
        trade_id = c.fetchone()[0]
    else:
        c.execute(query, (stock_code, stock_name, action, price, qty, status, ai_reason, order_no))
        trade_id = c.lastrowid
        
    conn.commit()
    conn.close()
    return trade_id

def update_trade_status(trade_id, status, price=None):
    conn = get_connection()
    c = conn.cursor()
    p = get_placeholder()
    if price:
        c.execute(f'UPDATE trades SET status = {p}, price = {p} WHERE id = {p}', (status, price, trade_id))
    else:
        c.execute(f'UPDATE trades SET status = {p} WHERE id = {p}', (status, trade_id))
    conn.commit()
    conn.close()

def get_recent_scans(limit=50):
    conn = get_connection()
    c = get_cursor(conn)
    p = get_placeholder()
    c.execute(f'SELECT * FROM scans ORDER BY timestamp DESC LIMIT {p}', (limit,))
    
    if IS_POSTGRES:
        results = [dict(row) for row in c.fetchall()]
    else:
        columns = [column[0] for column in c.description]
        results = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return results

def get_recent_trades(limit=50):
    conn = get_connection()
    c = get_cursor(conn)
    p = get_placeholder()
    c.execute(f'SELECT * FROM trades ORDER BY timestamp DESC LIMIT {p}', (limit,))
    
    if IS_POSTGRES:
        results = [dict(row) for row in c.fetchall()]
    else:
        columns = [column[0] for column in c.description]
        results = [dict(zip(columns, row)) for row in c.fetchall()]
    conn.close()
    return results

if __name__ == "__main__":
    init_db()
    print(f"Database initialized. (Mode: {'PostgreSQL' if IS_POSTGRES else 'SQLite'})")
