import os
import json
import logging
import asyncio
from typing import Dict, Any
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class AIEvaluator:
    """Gemini AI를 이용한 종목 매매 판단기"""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-3.1-flash-lite-preview'
        
    async def evaluate(self, symbol: str, name: str, price: float, vol_ratio: str) -> Dict[str, Any]:
        """로스 카메론 모멘텀 전략 기준 AI 평가"""
        prompt = f"""
        당신은 상위 1% '로스 카메론(Ross Cameron)' 스타일 모멘텀 트레이더입니다.
        
        종목: {name} ({symbol})
        현재가: {price}원
        거래량 급증률: {vol_ratio}%
        
        시가 갭 돌파, 상대거래율 10배 이상, 낮은 부동주식수 등 모멘텀 원칙에 따라 매수(BUY) 또는 관망(HOLD)을 결정하세요.
        반드시 아래 JSON 형식으로만 응답하세요.
        {{"action": "BUY" 또는 "HOLD", "reason": "이유 요약 (한국어)"}}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"❌ AI 분석 실패 ({symbol}): {e}")
            return {"action": "HOLD", "reason": f"AI 분석 오류: {str(e)}"}
