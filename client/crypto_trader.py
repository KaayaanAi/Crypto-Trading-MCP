#!/usr/bin/env python3
"""
Crypto Trading MCP Client

Main orchestrator that connects to multiple MCP servers for comprehensive
cryptocurrency trading automation. Combines news analysis, technical analysis,
social sentiment, market data, risk management, and AI insights.
"""

import asyncio
import sys
import os
import yaml
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
import logging

# Load .env file explicitly
from dotenv import load_dotenv

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from utils import setup_logger, load_env_var, utc_now, MetricsCollector, create_secure_connector
from constants import Trading, SystemConfig, ApiRateLimits
from exceptions import (
    TradingSystemError, MarketDataError, ConfigurationError,
    handle_error
)

load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = setup_logger("crypto-trader", log_file="logs/crypto_trader.log")


@dataclass
class MCPServerConfig:
    """MCP Server configuration"""
    name: str
    command: str
    args: List[str]
    enabled: bool = True
    timeout: int = 30
    retry_attempts: int = 3


class MCPConnectionManager:
    """Manages connections to multiple MCP servers"""

    def __init__(self, config_path: str = "client/config.yaml"):
        self.config_path = config_path
        self.connections: Dict[str, Any] = {}
        self.server_configs: Dict[str, MCPServerConfig] = {}
        self.load_config()

    def load_config(self):
        """Load MCP server configurations"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            mcp_config = config.get('mcp_servers', {})

            self.server_configs = {
                'news': MCPServerConfig(
                    name="crypto-news-mcp",
                    command="python",
                    args=["servers/crypto-news-mcp/main.py"],
                    enabled=mcp_config.get('news', {}).get('enabled', True),
                    timeout=mcp_config.get('news', {}).get('timeout', 30)
                ),
                'technical': MCPServerConfig(
                    name="crypto-technical-mcp",
                    command="python",
                    args=["servers/crypto-technical-mcp/main.py"],
                    enabled=mcp_config.get('technical', {}).get('enabled', True),
                    timeout=mcp_config.get('technical', {}).get('timeout', SystemConfig.CONNECTION_TIMEOUT)
                ),
                'social': MCPServerConfig(
                    name="crypto-social-mcp",
                    command="python",
                    args=["servers/crypto-social-mcp/main.py"],
                    enabled=mcp_config.get('social', {}).get('enabled', True),
                    timeout=mcp_config.get('social', {}).get('timeout', SystemConfig.CONNECTION_TIMEOUT)
                ),
                'binance': MCPServerConfig(
                    name="binance-mcp",
                    command="python",
                    args=["servers/binance-mcp/main.py"],
                    enabled=mcp_config.get('binance', {}).get('enabled', True),
                    timeout=mcp_config.get('binance', {}).get('timeout', ApiRateLimits.QUICK_REQUEST_TIMEOUT)
                ),
                'risk': MCPServerConfig(
                    name="crypto-risk-mcp",
                    command="python",
                    args=["servers/crypto-risk-mcp/main.py"],
                    enabled=mcp_config.get('risk', {}).get('enabled', True),
                    timeout=mcp_config.get('risk', {}).get('timeout', SystemConfig.HEALTH_CHECK_TIMEOUT)
                ),
                'ai': MCPServerConfig(
                    name="crypto-ai-mcp",
                    command="python",
                    args=["servers/crypto-ai-mcp/main.py"],
                    enabled=mcp_config.get('ai', {}).get('enabled', True),
                    timeout=mcp_config.get('ai', {}).get('timeout', ApiRateLimits.LONG_REQUEST_TIMEOUT)
                )
            }

            logger.info(f"Loaded configuration for {len(self.server_configs)} MCP servers")

        except Exception as e:
            raise ConfigurationError(
                f"Failed to load MCP server configuration from {self.config_path}",
                details={"config_path": self.config_path},
                cause=e
            ) from e

    async def connect_all_servers(self):
        """Connect to all enabled MCP servers"""
        logger.info("Connecting to MCP servers...")

        connection_tasks = []
        for server_name, config in self.server_configs.items():
            if config.enabled:
                connection_tasks.append(self._connect_server(server_name, config))
            else:
                logger.info(f"Skipping disabled server: {server_name}")

        results = await asyncio.gather(*connection_tasks, return_exceptions=True)

        successful_connections = 0
        for server_name, result in zip(self.server_configs.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to connect to {server_name}: {result}")
            else:
                successful_connections += 1

        logger.info(f"Successfully connected to {successful_connections}/{len(connection_tasks)} servers")
        return successful_connections > 0

    async def _connect_server(self, server_name: str, config: MCPServerConfig):
        """Connect to individual MCP server (simulated)"""
        try:
            logger.info(f"Connecting to {server_name}...")

            # In a real implementation, this would establish actual MCP connections
            # For now, we simulate the connection
            await asyncio.sleep(0.1)  # Simulate connection delay

            # Store mock connection info
            self.connections[server_name] = {
                'name': config.name,
                'status': 'connected',
                'connected_at': utc_now(),
                'config': config
            }

            logger.info(f"Connected to {server_name}")
            return True

        except Exception as e:
            raise TradingSystemError(
                f"Failed to connect to MCP server {server_name}",
                details={"server_name": server_name, "config": config.name},
                cause=e
            ) from e

    async def call_tool(self, server_name: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a tool on a specific MCP server"""
        if server_name not in self.connections:
            raise TradingSystemError(
                f"Not connected to MCP server: {server_name}",
                details={"server_name": server_name, "available_servers": list(self.connections.keys())}
            )

        try:
            # For the critical price issue, let's make direct API calls for Binance
            if server_name == "binance" and tool_name == "get_market_data":
                return await self._get_real_market_data(**kwargs)

            # For other tools, use simulation for now but log that it's mock data
            logger.warning(f"Using simulated data for {server_name}.{tool_name} - replace with real MCP calls")
            return await self._simulate_tool_call(server_name, tool_name, **kwargs)

        except TradingSystemError:
            # Re-raise trading system errors
            raise
        except Exception as e:
            raise TradingSystemError(
                f"Failed to call {tool_name} on {server_name}",
                details={"server_name": server_name, "tool_name": tool_name, "kwargs": str(kwargs)},
                cause=e
            ) from e

    async def _get_real_market_data(self, **kwargs) -> Dict[str, Any]:
        """Get real market data from Binance API"""
        symbol = kwargs.get("symbol", "BTCUSDT")

        # Use mainnet for real price data
        base_url = "https://api.binance.com"

        # Create secure SSL connector with proper certificate verification
        connector = create_secure_connector(verify_ssl=True)

        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                # Get current price
                price_url = f"{base_url}/api/v3/ticker/price?symbol={symbol}"
                async with session.get(price_url) as response:
                    if response.status == 200:
                        price_data = await response.json()
                        current_price = float(price_data['price'])

                        # Get 24hr stats for additional data
                        stats_url = f"{base_url}/api/v3/ticker/24hr?symbol={symbol}"
                        async with session.get(stats_url) as stats_response:
                            if stats_response.status == 200:
                                stats_data = await stats_response.json()
                                change_percent = float(stats_data['priceChangePercent'])
                                volume = float(stats_data['volume'])
                            else:
                                change_percent = 0.0
                                volume = 0.0

                        logger.info(
                            f"✅ Real market data: {symbol} price ${current_price:,.2f} "
                            f"({change_percent:+.2f}%)"
                        )

                        return {
                            "success": True,
                            "symbol": symbol,
                            "price": current_price,
                            "change_percent": change_percent,
                            "volume": volume,
                            "timestamp": utc_now().isoformat(),
                            "source": "binance_mainnet"
                        }
                    else:
                        logger.error(f"Binance API error: {response.status}")
                        return {"success": False, "error": f"API error: {response.status}"}

        except Exception as e:
            raise MarketDataError(
                "Failed to fetch real market data from Binance API",
                details={"symbol": symbol, "base_url": base_url},
                cause=e
            ) from e

    async def _simulate_tool_call(self, server_name: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Simulate MCP tool calls with realistic responses"""
        await asyncio.sleep(0.1)  # Simulate network delay

        if server_name == "news":
            if tool_name == "analyze_news_sentiment":
                return {
                    "success": True,
                    "overall_sentiment": 0.2,
                    "confidence": 0.75,
                    "impact_level": "medium",
                    "key_topics": ["bitcoin", "regulation", "adoption"],
                    "analyzed_items": 15
                }

        elif server_name == "technical":
            if tool_name == "calculate_indicators":
                return {
                    "success": True,
                    "indicators": [
                        {"name": "RSI", "value": 45.2, "signal": "neutral", "confidence": 0.8},
                        {"name": "MACD", "value": 125.5, "signal": "bullish", "confidence": 0.7},
                        {"name": "EMA_20", "value": 43250.0, "signal": "bullish", "confidence": 0.9}
                    ],
                    "overall_signal": "bullish",
                    "confidence": 0.8
                }

        elif server_name == "social":
            if tool_name == "analyze_social_sentiment":
                return {
                    "success": True,
                    "overall_sentiment": 0.35,
                    "sentiment_level": "bullish",
                    "platform_results": {
                        "twitter": {"sentiment_score": 0.4, "volume": 1250, "confidence": 0.8},
                        "reddit": {"sentiment_score": 0.3, "volume": 85, "confidence": 0.7}
                    }
                }

        elif server_name == "binance":
            if tool_name == "get_market_data":
                return {
                    "success": True,
                    "symbol": kwargs.get("symbol", "BTCUSDT"),
                    "price": 43250.50,
                    "change_percent": 2.35,
                    "volume": 125000.0
                }
            elif tool_name == "get_account_info":
                return {
                    "success": True,
                    "balances": [
                        {"asset": "USDT", "free": 10000.0, "locked": 0.0, "total": 10000.0},
                        {"asset": "BTC", "free": 0.1, "locked": 0.0, "total": 0.1}
                    ],
                    "can_trade": True
                }
            elif tool_name == "place_order":
                return {
                    "success": True,
                    "order_id": f"ORDER_{int(utc_now().timestamp())}",
                    "status": "FILLED",
                    "symbol": kwargs.get("symbol"),
                    "side": kwargs.get("side"),
                    "quantity": kwargs.get("quantity"),
                    "price": kwargs.get("price")
                }

        elif server_name == "risk":
            if tool_name == "calculate_position_size":
                return {
                    "success": True,
                    "position_size": {
                        "quantity": 0.046,
                        "notional_value": 2000.0,
                        "risk_amount": 200.0,
                        "confidence": 0.85
                    },
                    "risk_metrics": {
                        "risk_per_trade_percent": 2.0,
                        "position_value_percent": 20.0
                    }
                }

        elif server_name == "ai":
            if tool_name == "generate_trading_signal":
                return {
                    "success": True,
                    "signal": {
                        "action": "buy",
                        "confidence": 0.78,
                        "target_price": 45000.0,
                        "stop_loss": 41500.0,
                        "timeframe": "medium"
                    },
                    "analysis": {
                        "model_used": "llama2",
                        "key_insights": ["Technical breakout pattern", "Positive news sentiment"],
                        "reasoning": "Multiple bullish signals align with manageable risk profile"
                    }
                }

        # Default response
        return {
            "success": False,
            "error": f"Simulated call to {tool_name} on {server_name}"
        }

    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        logger.info("Disconnecting from MCP servers...")
        self.connections.clear()


class CryptoTrader:
    """Main crypto trading orchestrator"""

    def __init__(self, config_path: str = "client/config.yaml"):
        self.config_path = config_path
        self.mcp_manager = MCPConnectionManager(config_path)
        self.metrics = MetricsCollector()
        self.load_config()

        # Trading state
        self.active_positions: List[Dict] = []
        self.trade_history: List[Dict] = []
        self.last_analysis_time: Optional[datetime] = None

        # Safety controls
        self.emergency_stop = load_env_var("EMERGENCY_STOP", False)
        self.paper_trading = load_env_var("ENABLE_PAPER_TRADING", True)

    def load_config(self):
        """Load trading configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            self.trading_config = config.get('trading', {})
            self.analysis_config = config.get('analysis', {})
            self.risk_config = config.get('risk_management', {})

            self.symbol = self.trading_config.get('symbol', 'BTCUSDT')
            self.risk_per_trade = self.trading_config.get('risk_per_trade', Trading.DEFAULT_RISK_PER_TRADE)
            self.min_confidence = self.trading_config.get('min_confidence', Trading.DEFAULT_MIN_CONFIDENCE)

            logger.info(f"Loaded trading config - Symbol: {self.symbol}, Risk: {self.risk_per_trade:.1%}")

        except Exception as e:
            raise ConfigurationError(
                f"Failed to load trading configuration from {self.config_path}",
                details={"config_path": self.config_path},
                cause=e
            ) from e

    async def start_trading(self):
        """Start the main trading loop"""
        logger.info("Starting crypto trading system...")

        if self.emergency_stop:
            logger.error("EMERGENCY STOP is enabled - trading disabled")
            return

        if self.paper_trading:
            logger.warning("Paper trading mode enabled - no real orders will be placed")

        # Connect to MCP servers
        if not await self.mcp_manager.connect_all_servers():
            logger.error("Failed to connect to MCP servers - cannot start trading")
            return

        try:
            # Main trading loop
            analysis_interval = self.analysis_config.get('analysis_interval', Trading.DEFAULT_ANALYSIS_INTERVAL)

            while not self.emergency_stop:
                try:
                    # Perform market analysis
                    analysis = await self.perform_market_analysis()

                    if analysis and analysis.get('success'):
                        # Generate trading decision
                        decision = await self.make_trading_decision(analysis)

                        if decision and decision.get('should_trade'):
                            # Execute trade
                            execution_result = await self.execute_trade(decision)
                            logger.info(f"Trade execution result: {execution_result}")

                        # Update metrics
                        self.metrics.increment_counter("analysis_cycles")

                    # Monitor existing positions
                    await self.monitor_positions()

                    # Wait before next analysis
                    logger.info(f"Waiting {analysis_interval}s before next analysis...")
                    await asyncio.sleep(analysis_interval)

                except TradingSystemError as e:
                    logger.error(f"Trading system error: {e}")
                    self.metrics.increment_counter("trading_system_errors")
                    # Check if this is a critical error that should stop trading
                    if e.severity in ["high", "critical"]:
                        logger.critical("Critical error in trading loop - enabling emergency stop")
                        self.emergency_stop = True
                        break
                    await asyncio.sleep(60)  # Wait 1 minute on error
                except Exception as e:
                    logger.error(f"Unexpected error in trading loop: {e}")
                    self.metrics.increment_counter("trading_loop_errors")
                    # For unexpected errors, be more conservative
                    await asyncio.sleep(120)  # Wait 2 minutes on unexpected error

        except KeyboardInterrupt:
            logger.info("Trading stopped by user")

        finally:
            await self.mcp_manager.disconnect_all()
            logger.info("Trading system shutdown complete")

    async def perform_market_analysis(self) -> Dict[str, Any]:
        """Gather data from all MCP servers and perform analysis"""
        logger.info("Performing comprehensive market analysis...")

        start_time = utc_now()
        analysis_data = {}

        try:
            # Gather data from all sources in parallel
            tasks = {}

            # News analysis
            if 'news' in self.mcp_manager.connections:
                tasks['news'] = self.mcp_manager.call_tool(
                    'news', 'analyze_news_sentiment',
                    timeframe='6h'
                )

            # Technical analysis
            if 'technical' in self.mcp_manager.connections:
                indicators = self.analysis_config.get('indicators', ['RSI', 'MACD', 'EMA'])
                tasks['technical'] = self.mcp_manager.call_tool(
                    'technical', 'calculate_indicators',
                    symbol=self.symbol,
                    indicators=indicators
                )

            # Social sentiment
            if 'social' in self.mcp_manager.connections:
                tasks['social'] = self.mcp_manager.call_tool(
                    'social', 'analyze_social_sentiment',
                    platforms=['twitter', 'reddit']
                )

            # Market data
            if 'binance' in self.mcp_manager.connections:
                tasks['market'] = self.mcp_manager.call_tool(
                    'binance', 'get_market_data',
                    symbol=self.symbol,
                    data_type='24hr'
                )

            # Execute all tasks
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            # Process results
            for key, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.error(f"Error in {key} analysis: {result}")
                    analysis_data[key] = {"success": False, "error": str(result)}
                else:
                    analysis_data[key] = result

            # Calculate analysis duration
            analysis_duration = (utc_now() - start_time).total_seconds()
            self.metrics.record_histogram("analysis_duration_seconds", analysis_duration)

            analysis_data.update({
                "success": True,
                "timestamp": start_time.isoformat(),
                "analysis_duration_ms": analysis_duration * 1000,
                "sources_available": len([k for k, v in analysis_data.items() if v.get("success")])
            })

            self.last_analysis_time = start_time
            logger.info(f"Market analysis completed in {analysis_duration:.2f}s")

            return analysis_data

        except Exception as e:
            return handle_error(e, context="perform_market_analysis", reraise=False)

    async def make_trading_decision(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Make trading decision based on analysis"""
        logger.info("Making trading decision...")

        try:
            # Use AI to synthesize analysis if available
            if 'ai' in self.mcp_manager.connections:
                ai_result = await self.mcp_manager.call_tool(
                    'ai', 'generate_trading_signal',
                    market_data=analysis,
                    risk_tolerance=self.trading_config.get('mode', 'medium')
                )

                if ai_result.get('success'):
                    signal = ai_result['signal']
                    action = signal.get('action', 'hold')
                    confidence = signal.get('confidence', 0.0)

                    # Check minimum confidence threshold
                    if confidence >= self.min_confidence and action in ['buy', 'sell']:
                        # Calculate position size
                        account_balance = 10000.0  # Simulated balance
                        entry_price = analysis.get('market', {}).get('price', 0)
                        stop_loss_percent = self.risk_config.get('stop_loss_percent', 0.05)
                        stop_loss_price = entry_price * (1 - stop_loss_percent)

                        position_result = await self.mcp_manager.call_tool(
                            'risk', 'calculate_position_size',
                            account_balance=account_balance,
                            risk_per_trade=self.risk_per_trade,
                            entry_price=entry_price,
                            stop_loss_price=stop_loss_price
                        )

                        if position_result.get('success'):
                            return {
                                "should_trade": True,
                                "action": action,
                                "confidence": confidence,
                                "entry_price": entry_price,
                                "quantity": position_result['position_size']['quantity'],
                                "stop_loss": stop_loss_price,
                                "take_profit": signal.get('target_price'),
                                "reasoning": ai_result['analysis']['reasoning'],
                                "risk_amount": position_result['position_size']['risk_amount']
                            }

                    logger.info(f"Signal confidence ({confidence:.2f}) below threshold ({self.min_confidence})")
                    return {"should_trade": False, "reason": "Confidence below threshold"}

            # Fallback rule-based decision if AI not available
            return await self._rule_based_decision(analysis)

        except Exception as e:
            error_response = handle_error(e, context="make_trading_decision", reraise=False)
            return {"should_trade": False, "error": error_response.get("error", {}).get("message", str(e))}

    async def _rule_based_decision(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback rule-based trading decision"""
        logger.info("Using rule-based trading decision")

        try:
            scores = []

            # Technical analysis score
            technical = analysis.get('technical', {})
            if technical.get('success'):
                tech_signal = technical.get('overall_signal', 'neutral')
                if tech_signal == 'bullish':
                    scores.append(Trading.TECHNICAL_SIGNAL_WEIGHT)
                elif tech_signal == 'bearish':
                    scores.append(-Trading.TECHNICAL_SIGNAL_WEIGHT)

            # News sentiment score
            news = analysis.get('news', {})
            if news.get('success'):
                news_sentiment = news.get('overall_sentiment', 0.0)
                scores.append(news_sentiment * Trading.NEWS_SENTIMENT_WEIGHT)

            # Social sentiment score
            social = analysis.get('social', {})
            if social.get('success'):
                social_sentiment = social.get('overall_sentiment', 0.0)
                scores.append(social_sentiment * Trading.SOCIAL_SENTIMENT_WEIGHT)

            if not scores:
                return {"should_trade": False, "reason": "No valid analysis data"}

            overall_score = sum(scores) / len(scores)
            confidence = min(Trading.MAX_RULE_CONFIDENCE, abs(overall_score) + Trading.CONFIDENCE_BOOST)

            if overall_score > Trading.RULE_BASED_BUY_THRESHOLD and confidence >= self.min_confidence:
                action = "buy"
            elif overall_score < Trading.RULE_BASED_SELL_THRESHOLD and confidence >= self.min_confidence:
                action = "sell"
            else:
                return {"should_trade": False, "reason": "No clear signal"}

            return {
                "should_trade": True,
                "action": action,
                "confidence": confidence,
                "reasoning": f"Rule-based decision: score={overall_score:.2f}, confidence={confidence:.2f}"
            }

        except Exception as e:
            error_response = handle_error(e, context="rule_based_decision", reraise=False)
            return {"should_trade": False, "error": error_response.get("error", {}).get("message", str(e))}

    async def execute_trade(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trading decision"""
        action = decision['action']
        quantity = decision.get('quantity', 0.01)

        logger.info(f"Executing {action} order for {quantity} {self.symbol}")

        try:
            if self.paper_trading:
                # Paper trading - just log the trade
                trade_record = {
                    "timestamp": utc_now().isoformat(),
                    "action": action,
                    "symbol": self.symbol,
                    "quantity": quantity,
                    "price": decision.get('entry_price'),
                    "confidence": decision.get('confidence'),
                    "reasoning": decision.get('reasoning'),
                    "paper_trade": True
                }

                self.trade_history.append(trade_record)
                self.metrics.increment_counter(f"paper_trades_{action}")

                logger.info(f"Paper trade executed: {trade_record}")
                return {"success": True, "paper_trade": True, "trade_record": trade_record}

            else:
                # Real trading
                order_result = await self.mcp_manager.call_tool(
                    'binance', 'place_order',
                    symbol=self.symbol,
                    side=action.upper(),
                    type='MARKET',
                    quantity=quantity
                )

                if order_result.get('success'):
                    trade_record = {
                        "timestamp": utc_now().isoformat(),
                        "order_id": order_result['order_id'],
                        "action": action,
                        "symbol": self.symbol,
                        "quantity": quantity,
                        "price": order_result.get('price'),
                        "status": order_result.get('status'),
                        "confidence": decision.get('confidence'),
                        "reasoning": decision.get('reasoning')
                    }

                    self.trade_history.append(trade_record)
                    self.metrics.increment_counter(f"live_trades_{action}")

                    logger.info(f"Live trade executed: {trade_record}")
                    return {"success": True, "trade_record": trade_record}

                else:
                    logger.error(f"Trade execution failed: {order_result}")
                    return {"success": False, "error": order_result.get('error')}

        except Exception as e:
            self.metrics.increment_counter("trade_execution_errors")
            error_response = handle_error(e, context="execute_trade", reraise=False)
            return {"success": False, "error": error_response.get("error", {}).get("message", str(e))}

    async def monitor_positions(self):
        """Monitor existing positions"""
        try:
            if 'binance' in self.mcp_manager.connections:
                account_info = await self.mcp_manager.call_tool('binance', 'get_account_info')

                if account_info.get('success'):
                    balances = account_info.get('balances', [])
                    # Log significant balances
                    for balance in balances:
                        if balance['total'] > 0.001:  # Small threshold to avoid dust
                            logger.debug(f"Balance: {balance['asset']} = {balance['total']}")

        except Exception as e:
            logger.warning(f"Error monitoring positions (non-critical): {e}")
            # Position monitoring errors are non-critical, just log and continue

    def get_status(self) -> Dict[str, Any]:
        """Get current trading system status"""
        return {
            "system_status": "running" if not self.emergency_stop else "stopped",
            "paper_trading": self.paper_trading,
            "connected_servers": len(self.mcp_manager.connections),
            "last_analysis": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            "total_trades": len(self.trade_history),
            "active_positions": len(self.active_positions),
            "metrics": self.metrics.get_metrics()
        }


async def main():
    """Main entry point"""
    logger.info("Starting Crypto Trading MCP Client System")

    # Create necessary directories
    os.makedirs("logs", exist_ok=True)

    try:
        trader = CryptoTrader()
        await trader.start_trading()

    except KeyboardInterrupt:
        logger.info("System stopped by user")
    except TradingSystemError as e:
        logger.error(f"Trading system error: {e}")
        if e.severity == "critical":
            logger.critical("Critical system error - exiting")
            raise
        else:
            logger.error("Non-critical system error - exiting gracefully")
    except Exception as e:
        logger.error(f"Unexpected system error: {e}")
        raise TradingSystemError(
            "Unexpected error in main trading system",
            cause=e
        ) from e


if __name__ == "__main__":
    asyncio.run(main())
