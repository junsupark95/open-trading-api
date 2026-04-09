import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any

from brokers.kis.adapters import KISAdapter
from strategy.models import TradingState, StrategyConfig, RiskConfig
from strategy.state_machine import TradingStateMachine
from strategy.ai_evaluator import AIEvaluator
from risk.rules import RiskManager
from data.db import SessionLocal, log_scan, log_trade

logger = logging.getLogger(__name__)

class TradingEngine:
    """전략 실행 및 모니터링 통합 엔진"""
    
    def __init__(self, adapter: KISAdapter, ai_eval: AIEvaluator, config: StrategyConfig, risk_config: RiskConfig):
        self.adapter = adapter
        self.ai_eval = ai_eval
        self.config = config
        self.risk_manager = RiskManager(risk_config)
        self.state_machines: Dict[str, TradingStateMachine] = {}
        self.is_running = False
        self.balance = {"total_asset": 0, "pnl_amt": 0, "cash": 0}
        
    async def start(self):
        """엔진 구동 시작"""
        self.is_running = True
        logger.info("🚀 NeuroTrade 엔진 구동 시작")
        
        # 잔고 초기 동기화
        await self.sync_balance()
        
        # 주기적 매매 루프 루프 실행
        while self.is_running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"❌ 매매 루프 오류: {e}")
            await asyncio.sleep(60) # 최적화된 1분 주기

    async def sync_balance(self):
        """실시간 잔고 동기화"""
        try:
            self.balance = await asyncio.to_thread(self.adapter.get_balance)
            logger.info(f"📊 잔고 동기화 완료: 자산 {self.balance['total_asset']:,}원")
        except Exception as e:
            logger.error(f"❌ 잔고 동기화 에러: {e}")

    async def run_cycle(self):
        """단일 매매 사이클 (스캔 -> 분석 -> 리스크 -> 주문)"""
        now = datetime.now()
        
        # 0. 장중 모니터링: 10분마다 잔고 동기화
        if now.minute % 10 == 0:
            await self.sync_balance()

        # 1. 상위 종목 스캔
        rank_list = await asyncio.to_thread(self.adapter.get_volume_rank)
        
        for item in rank_list[:self.config.scan_limit]:
            symbol = item['mksc_shrn_iscd']
            name = item['hts_kor_isnm']
            price = float(item['stck_prpr'])
            vol_ratio = item['vol_inrt']
            
            # 상태 머신 초기화 및 업데이트
            if symbol not in self.state_machines:
                self.state_machines[symbol] = TradingStateMachine(symbol)
                self.state_machines[symbol].update("MARKET_OPEN")
            
            sm = self.state_machines[symbol]
            
            # (SCANNING) -> (WATCHING) 신호 감지
            if sm.state == TradingState.SCANNING:
                sm.update("SIGNAL_DETECTED")
                
                # (WATCHING) AI 평가 수행
                if sm.state == TradingState.WATCHING:
                    ai_res = await self.ai_eval.evaluate(symbol, name, price, vol_ratio)
                    
                    # DB 기록 (Supabase)
                    with SessionLocal() as db:
                        log_scan(db, symbol, f"증가율 {vol_ratio}%", ai_res['action'], ai_res['reason'])
                    
                    if ai_res['action'] == "BUY":
                        sm.update("AI_BUY")
                        
                        # (READY_TO_BUY) -> 리스크 검증 및 주문
                        if sm.state == TradingState.READY_TO_BUY:
                            context = {
                                "day_pnl_pct": (self.balance['pnl_amt'] / self.balance['total_asset'] * 100) if self.balance['total_asset'] > 0 else 0,
                                "open_positions": len(self.balance.get('holdings', []))
                            }
                            
                            if self.risk_manager.validate_new_entry(symbol, context):
                                qty = self.risk_manager.calculate_order_qty(price, self.balance['total_asset'])
                                if qty > 0:
                                    res = await asyncio.to_thread(self.adapter.place_order, symbol, qty, price, "BUY")
                                    if res['status'] == "SUCCESS":
                                        sm.update("ORDER_PLACED")
                                        # 주문 DB 기록
                                        with SessionLocal() as db:
                                             log_trade(db, symbol, name, "BUY", price, qty, "SUCCESS", ai_res['reason'], res['order_no'])
                                        sm.update("ORDER_FILLED")
                                    else:
                                        sm.update("ORDER_FAILED")
                                else:
                                    sm.update("ERROR")
                            else:
                                sm.update("RISK_BLOCK")
                    else:
                        sm.update("AI_HOLD")

    def stop(self):
        self.is_running = False
        logger.info("🛑 NeuroTrade 엔진 종료")

    def get_status(self) -> Dict[str, Any]:
        """API용 시스템 상태 데이터 반환"""
        # 자산 가치 및 수익률 계산
        asset = self.balance.get('total_asset', 0)
        pnl = self.balance.get('pnl_amt', 0)
        seed = asset - pnl
        ratio = round((pnl / seed * 100), 2) if seed > 0 else 0.0
        
        return {
            "is_running": self.is_running,
            "market_mode": "ACTIVE" if self.is_running else "IDLE",
            "last_scan_time": datetime.now().isoformat(), # 실시간 데이터
            "total_scans": len(self.state_machines), # 간단 지표
            "total_trades": 0, # 추후 DB 카운트 연동 가능
            "current_balance": asset,
            "seed_money": seed,
            "total_asset": asset,
            "p_l_amt": pnl,
            "p_l_ratio": ratio
        }
