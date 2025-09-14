#!/usr/bin/env python3
"""
Crypto AI Analysis MCP Server

Provides AI-powered cryptocurrency analysis using local Ollama models including:
- Market sentiment analysis with LLMs
- Technical pattern recognition
- Multi-factor decision synthesis
- Price prediction models
- Trading signal generation
- Natural language market insights
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from shared_types import AIInsight, AIAnalysis, SignalAction
from utils import setup_logger, safe_float, utc_now, load_env_var, cache


# Initialize server and logger
server = Server("crypto-ai-mcp")
logger = setup_logger("crypto-ai-mcp", log_file="logs/ai_server.log")


class OllamaClient:
    """Client for interacting with local Ollama instance"""

    def __init__(self):
        self.base_url = load_env_var("OLLAMA_HOST", "http://localhost:11434")
        self.default_model = load_env_var("OLLAMA_MODEL", "llama2")
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def is_available(self) -> bool:
        """Check if Ollama is available and running"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Ollama not available: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available models"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return [model["name"] for model in data.get("models", [])]
                return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Generate text using Ollama model"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "")
                else:
                    error_text = await response.text()
                    logger.error(f"Ollama generation failed: {error_text}")
                    return None

        except Exception as e:
            logger.error(f"Error generating with Ollama: {e}")
            return None


class CryptoAIAnalyzer:
    """AI-powered cryptocurrency analysis"""

    def __init__(self):
        self.ollama = None

        # Analysis prompts
        self.prompts = {
            "sentiment_analysis": """
            You are a cryptocurrency market analyst. Analyze the following market data and provide a sentiment score from -1 (very bearish) to 1 (very bullish).

            Market Data:
            {data}

            Provide your analysis in this JSON format:
            {
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "key_factors": ["factor1", "factor2"],
                "reasoning": "explanation of your analysis"
            }
            """,

            "technical_analysis": """
            You are an expert technical analyst. Based on the following technical indicators, provide a trading signal and confidence assessment.

            Technical Indicators:
            {indicators}

            Provide your analysis in this JSON format:
            {
                "signal": "buy|sell|hold",
                "confidence": 0.0,
                "key_patterns": ["pattern1", "pattern2"],
                "reasoning": "detailed technical analysis"
            }
            """,

            "comprehensive_analysis": """
            You are a professional cryptocurrency trader and analyst. Synthesize the following multi-source market data to provide a comprehensive trading recommendation.

            Data Sources:
            - Technical Analysis: {technical}
            - News Sentiment: {news}
            - Social Sentiment: {social}
            - Market Data: {market}
            - Risk Assessment: {risk}

            Consider:
            1. Signal confluence across data sources
            2. Risk-reward potential
            3. Market timing
            4. Current market regime

            Provide your comprehensive analysis in this JSON format:
            {
                "recommendation": "buy|sell|hold",
                "confidence": 0.0,
                "target_price": 0.0,
                "stop_loss": 0.0,
                "timeframe": "short|medium|long",
                "key_insights": ["insight1", "insight2"],
                "risk_factors": ["risk1", "risk2"],
                "reasoning": "comprehensive explanation"
            }
            """,

            "price_prediction": """
            You are a quantitative analyst specializing in cryptocurrency price prediction. Based on the provided market data, technical indicators, and sentiment analysis, predict the likely price direction and magnitude.

            Market Data:
            {market_data}

            Provide your prediction in this JSON format:
            {
                "direction": "up|down|sideways",
                "magnitude": 0.0,
                "timeframe_hours": 0,
                "confidence": 0.0,
                "key_drivers": ["driver1", "driver2"],
                "scenarios": {
                    "bullish": {"probability": 0.0, "target": 0.0},
                    "bearish": {"probability": 0.0, "target": 0.0},
                    "neutral": {"probability": 0.0, "range": [0.0, 0.0]}
                }
            }
            """
        }

    async def __aenter__(self):
        self.ollama = OllamaClient()
        await self.ollama.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.ollama:
            await self.ollama.__aexit__(exc_type, exc_val, exc_tb)

    def parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response and extract JSON"""
        try:
            # Try to find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                # If no JSON found, create a basic response
                return {
                    "error": "Could not parse AI response",
                    "raw_response": response[:500]  # Limit length
                }

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing AI response JSON: {e}")
            return {
                "error": "Invalid JSON in AI response",
                "raw_response": response[:500]
            }

    async def analyze_sentiment(self, market_data: Dict[str, Any], model: Optional[str] = None) -> AIAnalysis:
        """Analyze market sentiment using AI"""
        try:
            if not model:
                model = self.ollama.default_model

            # Check if Ollama is available
            if not await self.ollama.is_available():
                return AIAnalysis(
                    model_used="unavailable",
                    insights=[],
                    prediction={},
                    confidence=0.0,
                    reasoning="Ollama service not available",
                    success=False,
                    error_message="AI analysis service unavailable"
                )

            prompt = self.prompts["sentiment_analysis"].format(data=json.dumps(market_data, indent=2))

            response = await self.ollama.generate(
                model=model,
                prompt=prompt,
                temperature=0.3,
                max_tokens=800
            )

            if not response:
                return AIAnalysis(
                    model_used=model,
                    insights=[],
                    prediction={},
                    confidence=0.0,
                    reasoning="No response from AI model",
                    success=False,
                    error_message="AI model did not generate response"
                )

            parsed_response = self.parse_ai_response(response)

            # Create insights from AI response
            insights = [
                AIInsight(
                    analysis_type="sentiment",
                    insight=parsed_response.get("reasoning", "AI sentiment analysis completed"),
                    confidence=safe_float(parsed_response.get("confidence", 0.5)),
                    weight=0.8
                )
            ]

            return AIAnalysis(
                model_used=model,
                insights=insights,
                prediction=parsed_response,
                confidence=safe_float(parsed_response.get("confidence", 0.5)),
                reasoning=parsed_response.get("reasoning", response[:200])
            )

        except Exception as e:
            logger.error(f"Error in AI sentiment analysis: {e}")
            return AIAnalysis(
                model_used=model or "unknown",
                insights=[],
                prediction={},
                confidence=0.0,
                reasoning="Analysis failed due to error",
                success=False,
                error_message=str(e)
            )

    async def analyze_technical_patterns(self, technical_data: Dict[str, Any], model: Optional[str] = None) -> AIAnalysis:
        """Analyze technical patterns using AI"""
        try:
            if not model:
                model = self.ollama.default_model

            if not await self.ollama.is_available():
                return AIAnalysis(
                    model_used="unavailable",
                    insights=[],
                    prediction={},
                    confidence=0.0,
                    reasoning="AI service unavailable",
                    success=False
                )

            prompt = self.prompts["technical_analysis"].format(indicators=json.dumps(technical_data, indent=2))

            response = await self.ollama.generate(
                model=model,
                prompt=prompt,
                temperature=0.2,  # Lower temperature for technical analysis
                max_tokens=800
            )

            if not response:
                return AIAnalysis(
                    model_used=model,
                    insights=[],
                    prediction={},
                    confidence=0.0,
                    reasoning="No AI response",
                    success=False
                )

            parsed_response = self.parse_ai_response(response)

            insights = [
                AIInsight(
                    analysis_type="technical",
                    insight=parsed_response.get("reasoning", "Technical analysis completed"),
                    confidence=safe_float(parsed_response.get("confidence", 0.5)),
                    weight=0.9
                )
            ]

            return AIAnalysis(
                model_used=model,
                insights=insights,
                prediction=parsed_response,
                confidence=safe_float(parsed_response.get("confidence", 0.5)),
                reasoning=parsed_response.get("reasoning", response[:200])
            )

        except Exception as e:
            logger.error(f"Error in AI technical analysis: {e}")
            return AIAnalysis(
                model_used=model or "unknown",
                insights=[],
                prediction={},
                confidence=0.0,
                reasoning="Technical analysis failed",
                success=False,
                error_message=str(e)
            )

    async def synthesize_analysis(
        self,
        technical: Dict[str, Any],
        news: Dict[str, Any],
        social: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any],
        model: Optional[str] = None
    ) -> AIAnalysis:
        """Synthesize comprehensive analysis from all data sources"""
        try:
            if not model:
                model = self.ollama.default_model

            if not await self.ollama.is_available():
                # Fallback to rule-based analysis if AI unavailable
                return self._fallback_analysis(technical, news, social, market, risk)

            prompt = self.prompts["comprehensive_analysis"].format(
                technical=json.dumps(technical, indent=2),
                news=json.dumps(news, indent=2),
                social=json.dumps(social, indent=2),
                market=json.dumps(market, indent=2),
                risk=json.dumps(risk, indent=2)
            )

            response = await self.ollama.generate(
                model=model,
                prompt=prompt,
                temperature=0.4,
                max_tokens=1200
            )

            if not response:
                return self._fallback_analysis(technical, news, social, market, risk)

            parsed_response = self.parse_ai_response(response)

            # Create comprehensive insights
            insights = [
                AIInsight(
                    analysis_type="comprehensive",
                    insight=parsed_response.get("reasoning", "Multi-factor analysis completed"),
                    confidence=safe_float(parsed_response.get("confidence", 0.5)),
                    weight=1.0
                )
            ]

            # Add specific insights for key factors
            if "key_insights" in parsed_response:
                for insight_text in parsed_response["key_insights"]:
                    insights.append(AIInsight(
                        analysis_type="insight",
                        insight=insight_text,
                        confidence=0.7,
                        weight=0.5
                    ))

            return AIAnalysis(
                model_used=model,
                insights=insights,
                prediction=parsed_response,
                confidence=safe_float(parsed_response.get("confidence", 0.5)),
                reasoning=parsed_response.get("reasoning", response[:300])
            )

        except Exception as e:
            logger.error(f"Error in AI comprehensive analysis: {e}")
            return self._fallback_analysis(technical, news, social, market, risk)

    def _fallback_analysis(
        self,
        technical: Dict[str, Any],
        news: Dict[str, Any],
        social: Dict[str, Any],
        market: Dict[str, Any],
        risk: Dict[str, Any]
    ) -> AIAnalysis:
        """Fallback rule-based analysis when AI is unavailable"""
        try:
            # Simple rule-based scoring
            scores = []

            # Technical score
            tech_signal = technical.get("overall_signal", "neutral")
            if tech_signal == "bullish":
                scores.append(0.6)
            elif tech_signal == "bearish":
                scores.append(-0.6)
            else:
                scores.append(0.0)

            # News sentiment score
            news_sentiment = news.get("overall_sentiment", 0.0)
            scores.append(news_sentiment * 0.5)

            # Social sentiment score
            social_sentiment = social.get("overall_sentiment", 0.0)
            scores.append(social_sentiment * 0.4)

            # Calculate overall score
            overall_score = sum(scores) / len(scores) if scores else 0.0

            # Determine recommendation
            if overall_score > 0.3:
                recommendation = "buy"
            elif overall_score < -0.3:
                recommendation = "sell"
            else:
                recommendation = "hold"

            confidence = min(0.8, abs(overall_score) + 0.3)

            insights = [
                AIInsight(
                    analysis_type="fallback",
                    insight="Rule-based analysis used due to AI unavailability",
                    confidence=confidence,
                    weight=0.6
                )
            ]

            return AIAnalysis(
                model_used="rule_based_fallback",
                insights=insights,
                prediction={
                    "recommendation": recommendation,
                    "confidence": confidence,
                    "reasoning": "Fallback rule-based analysis combining technical and sentiment signals"
                },
                confidence=confidence,
                reasoning="Rule-based analysis used as AI fallback"
            )

        except Exception as e:
            logger.error(f"Error in fallback analysis: {e}")
            return AIAnalysis(
                model_used="error",
                insights=[],
                prediction={},
                confidence=0.0,
                reasoning="Analysis failed completely",
                success=False,
                error_message=str(e)
            )


# MCP Server Tools
@server.call_tool()
async def analyze_with_llm(
    data: Dict[str, Any],
    analysis_type: str = "sentiment",
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze market data using local LLM (Ollama)

    Args:
        data: Market data to analyze
        analysis_type: Type of analysis (sentiment, technical, comprehensive)
        model: Specific model to use (optional)

    Returns:
        Dict containing AI analysis results
    """
    try:
        logger.info(f"Running {analysis_type} analysis with AI model")

        async with CryptoAIAnalyzer() as analyzer:
            if analysis_type == "sentiment":
                result = await analyzer.analyze_sentiment(data, model)
            elif analysis_type == "technical":
                result = await analyzer.analyze_technical_patterns(data, model)
            else:
                return {
                    "success": False,
                    "error": f"Invalid analysis_type: {analysis_type}"
                }

            return {
                "success": result.success,
                "model_used": result.model_used,
                "analysis_type": analysis_type,
                "insights": [insight.dict() for insight in result.insights],
                "prediction": result.prediction,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
                "error": result.error_message if not result.success else None,
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in analyze_with_llm: {e}")
        return {
            "success": False,
            "error": f"AI analysis failed: {str(e)}"
        }


@server.call_tool()
async def predict_price_movement(
    market_data: Dict[str, Any],
    timeframe_hours: int = 24,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Predict cryptocurrency price movement using AI

    Args:
        market_data: Current market data and indicators
        timeframe_hours: Prediction timeframe in hours
        model: AI model to use (optional)

    Returns:
        Dict containing price prediction
    """
    try:
        logger.info(f"Predicting price movement for {timeframe_hours}h timeframe")

        async with CryptoAIAnalyzer() as analyzer:
            if not await analyzer.ollama.is_available():
                # Simple rule-based prediction fallback
                current_price = market_data.get("current_price", 0)
                technical_signal = market_data.get("technical_signal", "neutral")

                if technical_signal == "bullish":
                    direction = "up"
                    magnitude = 0.05  # 5% expected move
                elif technical_signal == "bearish":
                    direction = "down"
                    magnitude = 0.05
                else:
                    direction = "sideways"
                    magnitude = 0.02

                return {
                    "success": True,
                    "model_used": "rule_based",
                    "prediction": {
                        "direction": direction,
                        "magnitude_percent": magnitude * 100,
                        "current_price": current_price,
                        "predicted_price": current_price * (1 + (magnitude if direction == "up" else -magnitude if direction == "down" else 0)),
                        "timeframe_hours": timeframe_hours,
                        "confidence": 0.6
                    },
                    "reasoning": "Rule-based prediction using technical signals",
                    "timestamp": utc_now().isoformat()
                }

            # Use AI for prediction
            if not model:
                model = analyzer.ollama.default_model

            prompt = analyzer.prompts["price_prediction"].format(
                market_data=json.dumps(market_data, indent=2)
            )

            response = await analyzer.ollama.generate(
                model=model,
                prompt=prompt,
                temperature=0.3,
                max_tokens=1000
            )

            if not response:
                return {
                    "success": False,
                    "error": "AI model did not generate prediction"
                }

            parsed_response = analyzer.parse_ai_response(response)

            return {
                "success": True,
                "model_used": model,
                "prediction": parsed_response,
                "reasoning": parsed_response.get("reasoning", "AI price prediction completed"),
                "timeframe_hours": timeframe_hours,
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in price prediction: {e}")
        return {
            "success": False,
            "error": f"Price prediction failed: {str(e)}"
        }


@server.call_tool()
async def generate_trading_signal(
    market_data: Dict[str, Any],
    risk_tolerance: str = "medium",
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive trading signal using AI synthesis

    Args:
        market_data: All available market data
        risk_tolerance: Risk tolerance level (low, medium, high)
        model: AI model to use (optional)

    Returns:
        Dict containing trading signal and recommendation
    """
    try:
        logger.info(f"Generating trading signal with {risk_tolerance} risk tolerance")

        # Extract data components
        technical = market_data.get("technical", {})
        news = market_data.get("news", {})
        social = market_data.get("social", {})
        market = market_data.get("market", {})
        risk = market_data.get("risk", {})

        async with CryptoAIAnalyzer() as analyzer:
            analysis = await analyzer.synthesize_analysis(
                technical=technical,
                news=news,
                social=social,
                market=market,
                risk=risk,
                model=model
            )

            if not analysis.success:
                return {
                    "success": False,
                    "error": analysis.error_message or "Signal generation failed"
                }

            prediction = analysis.prediction

            # Adjust confidence based on risk tolerance
            base_confidence = analysis.confidence
            if risk_tolerance == "low":
                min_confidence = 0.8
                adjusted_confidence = base_confidence * 0.8
            elif risk_tolerance == "high":
                min_confidence = 0.5
                adjusted_confidence = base_confidence * 1.2
            else:  # medium
                min_confidence = 0.7
                adjusted_confidence = base_confidence

            # Determine if signal meets confidence threshold
            recommendation = prediction.get("recommendation", "hold")
            if adjusted_confidence < min_confidence:
                recommendation = "hold"
                reasoning = f"Signal confidence ({adjusted_confidence:.2f}) below threshold for {risk_tolerance} risk tolerance"
            else:
                reasoning = prediction.get("reasoning", analysis.reasoning)

            return {
                "success": True,
                "signal": {
                    "action": recommendation,
                    "confidence": min(1.0, adjusted_confidence),
                    "original_confidence": base_confidence,
                    "risk_tolerance": risk_tolerance,
                    "target_price": prediction.get("target_price"),
                    "stop_loss": prediction.get("stop_loss"),
                    "timeframe": prediction.get("timeframe", "medium")
                },
                "analysis": {
                    "model_used": analysis.model_used,
                    "key_insights": [insight.insight for insight in analysis.insights],
                    "risk_factors": prediction.get("risk_factors", []),
                    "reasoning": reasoning
                },
                "data_sources": {
                    "technical_available": bool(technical),
                    "news_available": bool(news),
                    "social_available": bool(social),
                    "market_available": bool(market),
                    "risk_available": bool(risk)
                },
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error generating trading signal: {e}")
        return {
            "success": False,
            "error": f"Trading signal generation failed: {str(e)}"
        }


@server.call_tool()
async def get_available_models() -> Dict[str, Any]:
    """
    Get list of available AI models

    Returns:
        Dict containing available models and status
    """
    try:
        logger.info("Checking available AI models")

        async with OllamaClient() as ollama:
            is_available = await ollama.is_available()

            if not is_available:
                return {
                    "success": False,
                    "error": "Ollama service not available",
                    "status": "offline"
                }

            models = await ollama.list_models()

            return {
                "success": True,
                "status": "online",
                "ollama_host": ollama.base_url,
                "default_model": ollama.default_model,
                "available_models": models,
                "model_count": len(models),
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error checking available models: {e}")
        return {
            "success": False,
            "error": f"Failed to check available models: {str(e)}",
            "status": "error"
        }


async def main():
    """Main server entry point"""
    logger.info("Starting Crypto AI Analysis MCP Server")

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Check Ollama availability
    async with OllamaClient() as ollama:
        if await ollama.is_available():
            models = await ollama.list_models()
            logger.info(f"Ollama available with {len(models)} models: {models}")
        else:
            logger.warning("Ollama not available - will use fallback analysis")

    try:
        async with stdio_server() as streams:
            await server.run(
                streams[0], streams[1],
                server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())