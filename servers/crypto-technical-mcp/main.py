#!/usr/bin/env python3
"""
Crypto Technical Analysis MCP Server

Provides comprehensive technical analysis for cryptocurrencies including:
- Technical indicators (RSI, MACD, EMA, Bollinger Bands, VWAP)
- Chart pattern detection
- Support and resistance level identification
- Multi-timeframe analysis
"""

import asyncio
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import aiohttp
from dataclasses import dataclass

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from shared_types import TechnicalIndicator, ChartPattern, SupportResistanceLevel, TechnicalAnalysis, Timeframe
from utils import setup_logger, safe_float, utc_now, cache
from constants import TechnicalAnalysis as TAConstants, Cache


# Initialize server and logger
server = Server("crypto-technical-mcp")
logger = setup_logger("crypto-technical-mcp", log_file="logs/technical_server.log")


@dataclass
class OHLCV:
    """Open, High, Low, Close, Volume data point"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class TechnicalAnalyzer:
    """Technical analysis calculations and pattern detection"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_price_data(self, symbol: str, timeframe: str, limit: int = 500) -> List[OHLCV]:
        """
        Fetch OHLCV price data from Binance API

        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch

        Returns:
            List of OHLCV data points
        """
        try:
            cache_key = f"ohlcv_{symbol}_{timeframe}_{limit}"
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Using cached price data for {symbol} {timeframe}")
                return cached_data

            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": timeframe,
                "limit": limit
            }

            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

            ohlcv_data = []
            for candle in data:
                ohlcv = OHLCV(
                    timestamp=datetime.fromtimestamp(candle[0] / 1000),
                    open=safe_float(candle[1]),
                    high=safe_float(candle[2]),
                    low=safe_float(candle[3]),
                    close=safe_float(candle[4]),
                    volume=safe_float(candle[5])
                )
                ohlcv_data.append(ohlcv)

            # Cache for 1 minute for high-frequency timeframes, 5 minutes for others
            cache_ttl = Cache.SHORT_TTL if timeframe in TAConstants.HIGH_FREQUENCY_TIMEFRAMES else Cache.TECHNICAL_DATA_TTL
            cache.set(cache_key, ohlcv_data, ttl_seconds=cache_ttl)

            logger.info(f"Fetched {len(ohlcv_data)} candles for {symbol} {timeframe}")
            return ohlcv_data

        except Exception as e:
            logger.error(f"Error fetching price data for {symbol}: {e}")
            return []

    def calculate_rsi(self, prices: List[float], period: int = TAConstants.RSI_PERIOD) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)

    def calculate_macd(self, prices: List[float], fast: int = TAConstants.MACD_FAST_PERIOD, slow: int = TAConstants.MACD_SLOW_PERIOD, signal: int = TAConstants.MACD_SIGNAL_PERIOD) -> Tuple[float, float, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow + signal:
            return 0.0, 0.0, 0.0

        df = pd.DataFrame({'close': prices})

        # Calculate EMAs
        ema_fast = df['close'].ewm(span=fast).mean()
        ema_slow = df['close'].ewm(span=slow).mean()

        # MACD line
        macd_line = ema_fast - ema_slow

        # Signal line
        signal_line = macd_line.ewm(span=signal).mean()

        # Histogram
        histogram = macd_line - signal_line

        return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices)

        df = pd.DataFrame({'close': prices})
        ema = df['close'].ewm(span=period).mean()
        return float(ema.iloc[-1])

    def calculate_bollinger_bands(self, prices: List[float], period: int = TAConstants.BOLLINGER_PERIOD, std_dev: float = TAConstants.BOLLINGER_STD_DEV) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return 0.0, 0.0, 0.0

        df = pd.DataFrame({'close': prices})
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return float(upper_band.iloc[-1]), float(sma.iloc[-1]), float(lower_band.iloc[-1])

    def calculate_vwap(self, ohlcv_data: List[OHLCV]) -> float:
        """Calculate Volume Weighted Average Price"""
        if not ohlcv_data:
            return 0.0

        total_volume = 0
        total_price_volume = 0

        for candle in ohlcv_data:
            typical_price = (candle.high + candle.low + candle.close) / 3
            price_volume = typical_price * candle.volume
            total_price_volume += price_volume
            total_volume += candle.volume

        return total_price_volume / total_volume if total_volume > 0 else 0.0

    def detect_support_resistance(self, ohlcv_data: List[OHLCV], window: int = TAConstants.SUPPORT_RESISTANCE_WINDOW) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """Detect support and resistance levels"""
        if len(ohlcv_data) < window * 2 + 1:
            return [], []

        highs = [candle.high for candle in ohlcv_data]
        lows = [candle.low for candle in ohlcv_data]

        # Find local maxima (resistance) and minima (support)
        resistance_levels = []
        support_levels = []

        for i in range(window, len(ohlcv_data) - window):
            # Check for local high (resistance)
            if highs[i] == max(highs[i - window:i + window + 1]):
                # Count touches
                touches = sum(1 for h in highs if abs(h - highs[i]) <= highs[i] * TAConstants.PRICE_TOLERANCE_PERCENT)
                strength = min(1.0, touches / 5.0)

                resistance = SupportResistanceLevel(
                    level=highs[i],
                    type="resistance",
                    strength=strength,
                    touches=touches
                )
                resistance_levels.append(resistance)

            # Check for local low (support)
            if lows[i] == min(lows[i - window:i + window + 1]):
                # Count touches
                touches = sum(1 for l in lows if abs(l - lows[i]) <= lows[i] * TAConstants.PRICE_TOLERANCE_PERCENT)
                strength = min(1.0, touches / 5.0)

                support = SupportResistanceLevel(
                    level=lows[i],
                    type="support",
                    strength=strength,
                    touches=touches
                )
                support_levels.append(support)

        # Remove duplicates and sort by strength
        resistance_levels = sorted(set(resistance_levels), key=lambda x: x.strength, reverse=True)[:TAConstants.MAX_SUPPORT_RESISTANCE_LEVELS]
        support_levels = sorted(set(support_levels), key=lambda x: x.strength, reverse=True)[:TAConstants.MAX_SUPPORT_RESISTANCE_LEVELS]

        return support_levels, resistance_levels

    def detect_chart_patterns(self, ohlcv_data: List[OHLCV]) -> List[ChartPattern]:
        """Detect common chart patterns"""
        patterns = []

        if len(ohlcv_data) < TAConstants.MIN_CANDLES_FOR_PATTERNS:
            return patterns

        closes = [candle.close for candle in ohlcv_data]
        highs = [candle.high for candle in ohlcv_data]
        lows = [candle.low for candle in ohlcv_data]

        # Simple trend detection
        recent_closes = closes[-TAConstants.TREND_ANALYSIS_CANDLES:]
        trend_slope = np.polyfit(range(len(recent_closes)), recent_closes, 1)[0]

        if trend_slope > 0:
            patterns.append(ChartPattern(
                name="uptrend",
                confidence=min(TAConstants.MAX_TREND_CONFIDENCE, abs(trend_slope) / (recent_closes[-1] * TAConstants.TREND_SLOPE_SIGNIFICANCE_FACTOR)),
                direction="bullish"
            ))
        elif trend_slope < 0:
            patterns.append(ChartPattern(
                name="downtrend",
                confidence=min(TAConstants.MAX_TREND_CONFIDENCE, abs(trend_slope) / (recent_closes[-1] * TAConstants.TREND_SLOPE_SIGNIFICANCE_FACTOR)),
                direction="bearish"
            ))

        # Double top pattern detection (simplified)
        if len(highs) >= TAConstants.PATTERN_MIN_CANDLES:
            recent_highs = highs[-TAConstants.PATTERN_MIN_CANDLES:]
            max_indices = []

            for i in range(TAConstants.PATTERN_LOCAL_WINDOW, len(recent_highs) - TAConstants.PATTERN_LOCAL_WINDOW):
                if recent_highs[i] == max(recent_highs[i-TAConstants.PATTERN_LOCAL_WINDOW:i+TAConstants.PATTERN_LOCAL_WINDOW+1]):
                    max_indices.append(i)

            if len(max_indices) >= 2:
                last_two_highs = max_indices[-2:]
                high1 = recent_highs[last_two_highs[0]]
                high2 = recent_highs[last_two_highs[1]]

                if abs(high1 - high2) / high1 < TAConstants.DOUBLE_TOP_TOLERANCE_PERCENT:
                    patterns.append(ChartPattern(
                        name="double_top",
                        confidence=TAConstants.CHART_PATTERN_CONFIDENCE_THRESHOLD,
                        direction="bearish",
                        target_price=min(lows[max_indices[-2]:max_indices[-1]])
                    ))

        return patterns

    async def analyze_symbol(self, symbol: str, timeframe: str, indicators: List[str]) -> TechnicalAnalysis:
        """Perform comprehensive technical analysis"""
        try:
            # Fetch price data
            ohlcv_data = await self.fetch_price_data(symbol, timeframe, limit=TAConstants.DEFAULT_CANDLE_LIMIT)

            if not ohlcv_data:
                return TechnicalAnalysis(
                    symbol=symbol,
                    timeframe=Timeframe(timeframe),
                    indicators=[],
                    patterns=[],
                    support_levels=[],
                    resistance_levels=[],
                    overall_signal="neutral",
                    confidence=0.0,
                    success=False,
                    error_message="Failed to fetch price data"
                )

            closes = [candle.close for candle in ohlcv_data]
            current_price = closes[-1]

            # Calculate requested indicators
            calculated_indicators = []

            for indicator_name in indicators:
                try:
                    if indicator_name.upper() == "RSI":
                        rsi_value = self.calculate_rsi(closes)
                        signal = "oversold" if rsi_value < TAConstants.RSI_OVERSOLD_THRESHOLD else "overbought" if rsi_value > TAConstants.RSI_OVERBOUGHT_THRESHOLD else "neutral"
                        confidence = abs(rsi_value - 50) / 50.0

                        calculated_indicators.append(TechnicalIndicator(
                            name="RSI",
                            value=rsi_value,
                            signal=signal,
                            confidence=confidence
                        ))

                    elif indicator_name.upper() == "MACD":
                        macd, signal_line, histogram = self.calculate_macd(closes)
                        signal = "bullish" if macd > signal_line else "bearish"
                        confidence = abs(histogram) / current_price

                        calculated_indicators.append(TechnicalIndicator(
                            name="MACD",
                            value=macd,
                            signal=signal,
                            confidence=min(1.0, confidence)
                        ))

                    elif indicator_name.upper() == "EMA":
                        ema_20 = self.calculate_ema(closes, TAConstants.EMA_SHORT_PERIOD)
                        signal = "bullish" if current_price > ema_20 else "bearish"
                        confidence = abs(current_price - ema_20) / current_price

                        calculated_indicators.append(TechnicalIndicator(
                            name=f"EMA_{TAConstants.EMA_SHORT_PERIOD}",
                            value=ema_20,
                            signal=signal,
                            confidence=min(1.0, confidence)
                        ))

                    elif indicator_name.upper() == "BB":
                        upper, middle, lower = self.calculate_bollinger_bands(closes)
                        if current_price > upper:
                            signal = "overbought"
                            confidence = (current_price - upper) / current_price
                        elif current_price < lower:
                            signal = "oversold"
                            confidence = (lower - current_price) / current_price
                        else:
                            signal = "neutral"
                            confidence = 0.5

                        calculated_indicators.append(TechnicalIndicator(
                            name="Bollinger_Bands",
                            value=middle,
                            signal=signal,
                            confidence=min(1.0, confidence)
                        ))

                    elif indicator_name.upper() == "VWAP":
                        vwap = self.calculate_vwap(ohlcv_data)
                        signal = "bullish" if current_price > vwap else "bearish"
                        confidence = abs(current_price - vwap) / current_price

                        calculated_indicators.append(TechnicalIndicator(
                            name="VWAP",
                            value=vwap,
                            signal=signal,
                            confidence=min(1.0, confidence)
                        ))

                except Exception as e:
                    logger.error(f"Error calculating {indicator_name}: {e}")

            # Detect patterns
            patterns = self.detect_chart_patterns(ohlcv_data)

            # Find support/resistance levels
            support_levels, resistance_levels = self.detect_support_resistance(ohlcv_data)

            # Calculate overall signal
            bullish_signals = len([ind for ind in calculated_indicators if ind.signal in ["bullish", "oversold"]])
            bearish_signals = len([ind for ind in calculated_indicators if ind.signal in ["bearish", "overbought"]])

            if bullish_signals > bearish_signals:
                overall_signal = "bullish"
            elif bearish_signals > bullish_signals:
                overall_signal = "bearish"
            else:
                overall_signal = "neutral"

            # Calculate confidence
            total_confidence = sum(ind.confidence for ind in calculated_indicators)
            avg_confidence = total_confidence / len(calculated_indicators) if calculated_indicators else 0.0

            return TechnicalAnalysis(
                symbol=symbol,
                timeframe=Timeframe(timeframe),
                indicators=calculated_indicators,
                patterns=patterns,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                overall_signal=overall_signal,
                confidence=avg_confidence
            )

        except Exception as e:
            logger.error(f"Error in technical analysis for {symbol}: {e}")
            return TechnicalAnalysis(
                symbol=symbol,
                timeframe=Timeframe(timeframe),
                indicators=[],
                patterns=[],
                support_levels=[],
                resistance_levels=[],
                overall_signal="neutral",
                confidence=0.0,
                success=False,
                error_message=str(e)
            )


# MCP Server Tools
@server.call_tool()
async def calculate_indicators(
    symbol: str,
    timeframe: str = "1h",
    indicators: List[str] = None
) -> Dict[str, Any]:
    """
    Calculate technical indicators for a cryptocurrency symbol

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        timeframe: Time interval (1m, 5m, 15m, 1h, 4h, 1d)
        indicators: List of indicators to calculate (RSI, MACD, EMA, BB, VWAP)

    Returns:
        Dict containing calculated indicators
    """
    try:
        if not indicators:
            indicators = ["RSI", "MACD", "EMA", "BB", "VWAP"]

        logger.info(f"Calculating indicators for {symbol} on {timeframe}: {indicators}")

        async with TechnicalAnalyzer() as analyzer:
            analysis = await analyzer.analyze_symbol(symbol, timeframe, indicators)

            if not analysis.success:
                return {
                    "success": False,
                    "error": analysis.error_message or "Analysis failed"
                }

            return {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "indicators": [ind.dict() for ind in analysis.indicators],
                "overall_signal": analysis.overall_signal,
                "confidence": analysis.confidence,
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in calculate_indicators: {e}")
        return {
            "success": False,
            "error": f"Failed to calculate indicators: {str(e)}"
        }


@server.call_tool()
async def detect_patterns(
    symbol: str,
    timeframe: str = "4h",
    pattern_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Detect chart patterns for a cryptocurrency symbol

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        timeframe: Time interval for pattern detection
        pattern_types: Specific patterns to look for (optional)

    Returns:
        Dict containing detected patterns
    """
    try:
        logger.info(f"Detecting patterns for {symbol} on {timeframe}")

        async with TechnicalAnalyzer() as analyzer:
            analysis = await analyzer.analyze_symbol(symbol, timeframe, ["RSI"])  # Minimal indicators for pattern detection

            if not analysis.success:
                return {
                    "success": False,
                    "error": analysis.error_message or "Pattern detection failed"
                }

            return {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "patterns": [pattern.dict() for pattern in analysis.patterns],
                "pattern_count": len(analysis.patterns),
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in detect_patterns: {e}")
        return {
            "success": False,
            "error": f"Failed to detect patterns: {str(e)}"
        }


@server.call_tool()
async def find_support_resistance(
    symbol: str,
    timeframe: str = "4h",
    lookback_periods: int = 100
) -> Dict[str, Any]:
    """
    Find support and resistance levels for a cryptocurrency symbol

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        timeframe: Time interval for analysis
        lookback_periods: Number of periods to analyze

    Returns:
        Dict containing support and resistance levels
    """
    try:
        logger.info(f"Finding support/resistance for {symbol} on {timeframe}")

        async with TechnicalAnalyzer() as analyzer:
            ohlcv_data = await analyzer.fetch_price_data(symbol, timeframe, limit=lookback_periods)

            if not ohlcv_data:
                return {
                    "success": False,
                    "error": "Failed to fetch price data"
                }

            support_levels, resistance_levels = analyzer.detect_support_resistance(ohlcv_data)

            return {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "support_levels": [level.dict() for level in support_levels],
                "resistance_levels": [level.dict() for level in resistance_levels],
                "current_price": ohlcv_data[-1].close,
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in find_support_resistance: {e}")
        return {
            "success": False,
            "error": f"Failed to find support/resistance levels: {str(e)}"
        }


@server.call_tool()
async def multi_timeframe_analysis(
    symbol: str,
    timeframes: List[str] = None,
    indicators: List[str] = None
) -> Dict[str, Any]:
    """
    Perform multi-timeframe technical analysis

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        timeframes: List of timeframes to analyze
        indicators: List of indicators to calculate

    Returns:
        Dict containing multi-timeframe analysis results
    """
    try:
        if not timeframes:
            timeframes = TAConstants.DEFAULT_TIMEFRAMES

        if not indicators:
            indicators = ["RSI", "MACD", "EMA"]

        logger.info(f"Multi-timeframe analysis for {symbol}: {timeframes}")

        async with TechnicalAnalyzer() as analyzer:
            analyses = {}

            for tf in timeframes:
                try:
                    analysis = await analyzer.analyze_symbol(symbol, tf, indicators)
                    analyses[tf] = {
                        "indicators": [ind.dict() for ind in analysis.indicators],
                        "patterns": [pattern.dict() for pattern in analysis.patterns],
                        "overall_signal": analysis.overall_signal,
                        "confidence": analysis.confidence
                    }
                except Exception as e:
                    logger.error(f"Error analyzing {tf} timeframe: {e}")
                    analyses[tf] = {"error": str(e)}

            # Calculate consensus signal
            signals = [analyses[tf].get("overall_signal", "neutral") for tf in timeframes
                      if "error" not in analyses[tf]]

            bullish_count = signals.count("bullish")
            bearish_count = signals.count("bearish")

            if bullish_count > bearish_count:
                consensus_signal = "bullish"
            elif bearish_count > bullish_count:
                consensus_signal = "bearish"
            else:
                consensus_signal = "neutral"

            # Calculate average confidence
            confidences = [analyses[tf].get("confidence", 0.0) for tf in timeframes
                          if "error" not in analyses[tf]]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "success": True,
                "symbol": symbol,
                "timeframes": timeframes,
                "analyses": analyses,
                "consensus_signal": consensus_signal,
                "consensus_confidence": avg_confidence,
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error in multi_timeframe_analysis: {e}")
        return {
            "success": False,
            "error": f"Failed to perform multi-timeframe analysis: {str(e)}"
        }


async def main():
    """Main server entry point"""
    logger.info("Starting Crypto Technical Analysis MCP Server")

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

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