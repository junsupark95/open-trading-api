import logging
from typing import Dict, Any, Optional
from .models import TradingState

logger = logging.getLogger(__name__)

class TradingStateMachine:
    """전략 실행 및 상태 전이 관리기 (Ross Momentum 전략 맞춤형)"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.state = TradingState.IDLE
        self.last_transition_time = None
        
        # 거래 추적 필드
        self.entry_price: float = 0
        self.qty: int = 0
        self.order_no: Optional[str] = None
        self.pnl_pct: float = 0.0
        
    def transition_to(self, new_state: TradingState):
        """명시적 상태 전이"""
        old_state = self.state
        self.state = new_state
        logger.info(f"🔄 [{self.symbol}] 상태 전이: {old_state} -> {new_state}")
        
    def update(self, event: str, data: Optional[Dict[str, Any]] = None):
        """이벤트 수신 및 상태 머신 구동"""
        # (IDLE) -> MARKET_OPEN -> (SCANNING)
        if self.state == TradingState.IDLE:
             if event == "MARKET_OPEN":
                 self.transition_to(TradingState.SCANNING)

        # (SCANNING) -> SIGNAL_DETECTED -> (WATCHING)
        elif self.state == TradingState.SCANNING:
             if event == "SIGNAL_DETECTED":
                 self.transition_to(TradingState.WATCHING)

        # (WATCHING) -> AI_CONFIRMED -> (READY_TO_BUY)
        elif self.state == TradingState.WATCHING:
             if event == "AI_BUY":
                 self.transition_to(TradingState.READY_TO_BUY)
             elif event == "AI_HOLD":
                 self.transition_to(TradingState.SCANNING)

        # (READY_TO_BUY) -> ORDER_SENT -> (BUY_ORDER_SENT)
        elif self.state == TradingState.READY_TO_BUY:
             if event == "ORDER_PLACED":
                 self.transition_to(TradingState.BUY_ORDER_SENT)

        # (BUY_ORDER_SENT) -> FILLED -> (POSITION_OPEN)
        elif self.state == TradingState.BUY_ORDER_SENT:
             if event == "ORDER_FILLED":
                 self.transition_to(TradingState.POSITION_OPEN)
             elif event == "ORDER_FAILED":
                 self.transition_to(TradingState.ERROR)

        # (POSITION_OPEN) -> STOP_LOSS / TAKE_PROFIT -> (SELL_ORDER_SENT)
        elif self.state == TradingState.POSITION_OPEN:
             if event in ["STOP_LOSS", "TAKE_PROFIT", "TIME_EXIT"]:
                 self.transition_to(TradingState.SELL_ORDER_SENT)

        # (SELL_ORDER_SENT) -> FILLED -> (CLOSED)
        elif self.state == TradingState.SELL_ORDER_SENT:
             if event == "ORDER_FILLED":
                 self.transition_to(TradingState.CLOSED)
                 
        # 리스크 및 에러 예외 처리
        if event == "RISK_BLOCK":
             self.transition_to(TradingState.HALTED)
        elif event == "ERROR":
             self.transition_to(TradingState.ERROR)
             
    def can_trade(self) -> bool:
        """현재 매매가 가능한 상태인지 확인"""
        return self.state not in [TradingState.HALTED, TradingState.ERROR]
