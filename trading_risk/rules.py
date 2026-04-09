from typing import List, Dict, Optional
import logging
from trading_strategy.models import RiskConfig

logger = logging.getLogger(__name__)

class RiskRule:
    """개별 리스크 규칙 인터페이스"""
    def check(self, context: dict) -> bool:
        raise NotImplementedError

class DailyLossLimitRule(RiskRule):
    """일일 최대 손실 제한 규칙"""
    def __init__(self, limit_pct: float):
        self.limit_pct = limit_pct
        
    def check(self, context: dict) -> bool:
        current_pnl_pct = context.get('day_pnl_pct', 0.0)
        if current_pnl_pct < self.limit_pct:
            logger.warning(f"🚨 일일 손실 한도({self.limit_pct}%) 초과: {current_pnl_pct}%")
            return False
        return True

class MaxPositionRule(RiskRule):
    """최대 보유 종목 수 제한 규칙"""
    def __init__(self, max_count: int):
        self.max_count = max_count
        
    def check(self, context: dict) -> bool:
        current_positions = context.get('open_positions', 0)
        if current_positions >= self.max_count:
            logger.warning(f"🚨 최대 보유 종목 수({self.max_count}) 초과: {current_positions}")
            return False
        return True

class RiskManager:
    """리스크 관리 통합 클래스"""
    def __init__(self, config: RiskConfig):
        self.config = config
        self.rules: List[RiskRule] = [
            DailyLossLimitRule(config.max_day_loss_pct),
            MaxPositionRule(config.max_symbol_risk_pct) # 실제로는 config 필드에 따라 조정
        ]
        
    def validate_new_entry(self, symbol: str, context: dict) -> bool:
        """신규 진입 가능 여부 검증"""
        for rule in self.rules:
            if not rule.check(context):
                return False
        return True

    def calculate_order_qty(self, price: float, total_balance: float) -> int:
        """한 종목당 자산 대비 최대 리스크를 고려한 수량 산출"""
        # (예시) 자산의 10%를 한 종목에 배정
        allocation = total_balance * 0.1
        qty = int(allocation / price) if price > 0 else 0
        return qty
