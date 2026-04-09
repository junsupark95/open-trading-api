import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from .models import Base

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # 로컬 SQLite 기본값
    DATABASE_URL = "sqlite:///trades.db"
elif DATABASE_URL.startswith("postgres://"):
    # SQLAlchemy는 postgresql:// 형식을 권장함
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 하위 호환성 및 편의성을 위한 래퍼 함수들
def log_scan(db: Session, stock_code: str, scan_reason: str, ai_decision: str, ai_reason: str):
    from .models import Scan
    new_scan = Scan(
        stock_code=stock_code,
        scan_reason=scan_reason,
        ai_decision=ai_decision,
        ai_reason=ai_reason
    )
    db.add(new_scan)
    db.commit()
    db.refresh(new_scan)
    return new_scan.id

def log_trade(db: Session, stock_code: str, stock_name: str, action: str, price: float, qty: int, status: str, ai_reason: str, order_no=None):
    from .models import Trade
    new_trade = Trade(
        stock_code=stock_code,
        stock_name=stock_name,
        action=action,
        price=price,
        qty=qty,
        status=status,
        ai_reason=ai_reason,
        order_no=order_no
    )
    db.add(new_trade)
    db.commit()
    db.refresh(new_trade)
    return new_trade.id

def get_recent_scans(db: Session, limit: int = 50):
    from .models import Scan
    return db.query(Scan).order_by(Scan.timestamp.desc()).limit(limit).all()

def get_recent_trades(db: Session, limit: int = 50):
    from .models import Trade
    return db.query(Trade).order_by(Trade.timestamp.desc()).limit(limit).all()
