from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Trade(Base):
    """주문 및 체결 내역 레코드"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(100))
    action = Column(String(10), nullable=False) # BUY, SELL
    price = Column(Float)
    qty = Column(Integer)
    status = Column(String(20), default='PENDING') # PENDING, SUCCESS, FAILED, CANCELLED
    order_no = Column(String(50), index=True)
    ai_reason = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Scan(Base):
    """AI 스캐닝 및 분석 이력 레코드"""
    __tablename__ = 'scans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    scan_reason = Column(String(200))
    ai_decision = Column(String(10)) # BUY, HOLD
    ai_reason = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class DailyPnL(Base):
    """일별 손익 통계 레코드"""
    __tablename__ = 'daily_pnl'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True)
    seed_money = Column(Float)
    final_asset = Column(Float)
    pnl_amt = Column(Float)
    pnl_ratio = Column(Float)
    trade_count = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class RiskEvent(Base):
    """리스크 관리 차단 이벤트 레코드"""
    __tablename__ = 'risk_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50)) # DAY_LOSS_LIMIT, VI_PROTECTION, etc.
    symbol = Column(String(10))
    reason = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
