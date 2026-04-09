from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import time

class TradingState(str, Enum):
    IDLE = "IDLE"
    SCANNING = "SCANNING"
    WATCHING = "WATCHING"
    READY_TO_BUY = "READY_TO_BUY"
    BUY_ORDER_SENT = "BUY_ORDER_SENT"
    POSITION_OPEN = "POSITION_OPEN"
    SELL_ORDER_SENT = "SELL_ORDER_SENT"
    CLOSED = "CLOSED"
    HALTED = "HALTED"
    ERROR = "ERROR"

class PositionStatus(str, Enum):
    NONE = "NONE"
    ENTRY_PENDING = "ENTRY_PENDING"
    OPEN = "OPEN"
    EXIT_PENDING = "EXIT_PENDING"
    CLOSED = "CLOSED"

class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class StrategyConfig:
    """전략 파라미터 모델"""
    name: str = "Ross Momentum"
    min_volume_ratio: float = 50.0 # 전일대비 거래량 최소 비율
    min_price_gap: float = 2.0     # 시가 갭 최소 비율
    max_holding_count: int = 3      # 최대 보유 종목 수
    scan_limit: int = 10           # 스캔 대상 수
    
    # 시간 조건 (KST 기준)
    market_open_time: time = time(9, 0)
    market_close_time: time = time(15, 20)
    stop_new_entry_time: time = time(15, 0)

@dataclass
class RiskConfig:
    """리스크 관리 파라미터 모델"""
    stop_loss_pct: float = -3.0     # 일괄 손절비율
    take_profit_pct: float = 5.0    # 익절비율
    max_day_loss_pct: float = -2.0  # 일일 최대 손실 제한
    max_symbol_risk_pct: float = 1.0 # 종목당 자산 대비 최대 리스크
    vi_protection_enabled: bool = True # VI 발동 시 진입 제한
