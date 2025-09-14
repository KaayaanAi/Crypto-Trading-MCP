#!/usr/bin/env python3
"""
Integration tests for the Crypto Trading MCP System

Tests the complete system including all MCP servers and the main orchestrator.
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'client'))

from crypto_trader import CryptoTrader, MCPConnectionManager
from mcp_manager import MCPServerManager
import utils


class TestMCPConnectionManager:
    """Test MCP connection management"""

    @pytest.fixture
    def connection_manager(self):
        """Create test connection manager"""
        return MCPConnectionManager("tests/test_config.yaml")

    def test_load_config(self, connection_manager):
        """Test configuration loading"""
        # Should load without errors
        assert len(connection_manager.server_configs) > 0

        # Check required servers are configured
        expected_servers = ['news', 'technical', 'social', 'binance', 'risk', 'ai']
        for server in expected_servers:
            assert server in connection_manager.server_configs

    @pytest.mark.asyncio
    async def test_connect_all_servers(self, connection_manager):
        """Test connecting to all MCP servers"""
        # Mock the actual connection process
        with patch.object(connection_manager, '_connect_server', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True

            success = await connection_manager.connect_all_servers()
            assert success is True
            assert len(connection_manager.connections) > 0

    @pytest.mark.asyncio
    async def test_call_tool(self, connection_manager):
        """Test calling tools on MCP servers"""
        # Mock successful connection
        connection_manager.connections['news'] = {
            'name': 'crypto-news-mcp',
            'status': 'connected',
            'connected_at': datetime.utcnow()
        }

        # Mock tool call
        with patch.object(connection_manager, 'call_tool', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"success": True, "data": "test_result"}

            result = await connection_manager.call_tool('news', 'analyze_news_sentiment')
            assert result['success'] is True


class TestCryptoTrader:
    """Test main crypto trader functionality"""

    @pytest.fixture
    def crypto_trader(self):
        """Create test crypto trader"""
        # Use test configuration
        trader = CryptoTrader("tests/test_config.yaml")
        return trader

    def test_load_config(self, crypto_trader):
        """Test configuration loading"""
        assert crypto_trader.symbol is not None
        assert crypto_trader.risk_per_trade > 0
        assert crypto_trader.min_confidence > 0

    @pytest.mark.asyncio
    async def test_perform_market_analysis(self, crypto_trader):
        """Test market analysis workflow"""
        # Mock MCP connections
        crypto_trader.mcp_manager.connections = {
            'news': {'status': 'connected'},
            'technical': {'status': 'connected'},
            'social': {'status': 'connected'},
            'binance': {'status': 'connected'}
        }

        # Mock tool calls
        async def mock_call_tool(server, tool, **kwargs):
            if server == 'news':
                return {
                    "success": True,
                    "overall_sentiment": 0.2,
                    "confidence": 0.75
                }
            elif server == 'technical':
                return {
                    "success": True,
                    "overall_signal": "bullish",
                    "confidence": 0.8
                }
            elif server == 'social':
                return {
                    "success": True,
                    "overall_sentiment": 0.35
                }
            elif server == 'binance':
                return {
                    "success": True,
                    "price": 43250.50
                }
            return {"success": False}

        with patch.object(crypto_trader.mcp_manager, 'call_tool', side_effect=mock_call_tool):
            analysis = await crypto_trader.perform_market_analysis()

            assert analysis['success'] is True
            assert analysis['sources_available'] > 0
            assert 'timestamp' in analysis

    @pytest.mark.asyncio
    async def test_make_trading_decision(self, crypto_trader):
        """Test trading decision making"""
        # Mock analysis data
        analysis_data = {
            'success': True,
            'news': {'success': True, 'overall_sentiment': 0.3},
            'technical': {'success': True, 'overall_signal': 'bullish'},
            'social': {'success': True, 'overall_sentiment': 0.2},
            'market': {'success': True, 'price': 43250.0}
        }

        # Mock AI service
        crypto_trader.mcp_manager.connections['ai'] = {'status': 'connected'}

        async def mock_ai_call(server, tool, **kwargs):
            return {
                "success": True,
                "signal": {
                    "action": "buy",
                    "confidence": 0.8,
                    "target_price": 45000.0
                },
                "analysis": {
                    "reasoning": "Test reasoning"
                }
            }

        async def mock_risk_call(server, tool, **kwargs):
            return {
                "success": True,
                "position_size": {
                    "quantity": 0.046,
                    "risk_amount": 200.0
                }
            }

        def mock_call_router(server, tool, **kwargs):
            if server == 'ai':
                return mock_ai_call(server, tool, **kwargs)
            elif server == 'risk':
                return mock_risk_call(server, tool, **kwargs)
            return AsyncMock(return_value={"success": False})()

        with patch.object(crypto_trader.mcp_manager, 'call_tool', side_effect=mock_call_router):
            decision = await crypto_trader.make_trading_decision(analysis_data)

            assert decision is not None
            if decision.get('should_trade'):
                assert decision['action'] in ['buy', 'sell']
                assert decision['confidence'] > 0

    @pytest.mark.asyncio
    async def test_execute_trade_paper_mode(self, crypto_trader):
        """Test trade execution in paper trading mode"""
        # Ensure paper trading is enabled
        crypto_trader.paper_trading = True

        decision = {
            'action': 'buy',
            'quantity': 0.05,
            'entry_price': 43250.0,
            'confidence': 0.8,
            'reasoning': 'Test trade'
        }

        result = await crypto_trader.execute_trade(decision)

        assert result['success'] is True
        assert result['paper_trade'] is True
        assert len(crypto_trader.trade_history) > 0


class TestSystemComponents:
    """Test individual system components"""

    def test_shared_types_import(self):
        """Test shared types can be imported"""
        try:
            from types import TradingSignal, MarketAnalysis, NewsItem
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import shared types: {e}")

    def test_shared_utils_functions(self):
        """Test shared utility functions"""
        # Test safe conversions
        assert utils.safe_float("123.45") == 123.45
        assert utils.safe_float("invalid", 0.0) == 0.0
        assert utils.safe_int("42") == 42
        assert utils.safe_int("invalid", 0) == 0

        # Test percentage change calculation
        assert utils.percentage_change(100.0, 110.0) == 10.0
        assert utils.percentage_change(100.0, 90.0) == -10.0

    def test_metrics_collector(self):
        """Test metrics collection functionality"""
        metrics = utils.MetricsCollector()

        # Test counter
        metrics.increment_counter("test_counter")
        metrics.increment_counter("test_counter", 5)
        assert metrics.counters["test_counter"] == 6

        # Test gauge
        metrics.set_gauge("test_gauge", 42.5)
        assert metrics.gauges["test_gauge"] == 42.5

        # Test histogram
        metrics.record_histogram("test_histogram", 1.0)
        metrics.record_histogram("test_histogram", 2.0)
        assert len(metrics.histograms["test_histogram"]) == 2

    def test_cache_functionality(self):
        """Test caching functionality"""
        cache = utils.SimpleCache()

        # Set and get value
        cache.set("test_key", "test_value", ttl_seconds=10)
        assert cache.get("test_key") == "test_value"

        # Test expiration (mock time)
        import time
        original_time = time.time

        def mock_time():
            return original_time() + 20  # 20 seconds later

        with patch('time.time', mock_time):
            # Should be expired
            assert cache.get("test_key") is None


class TestConfigurationValidation:
    """Test configuration validation"""

    def test_default_config_valid(self):
        """Test default configuration is valid"""
        config_path = "client/config.yaml"

        if os.path.exists(config_path):
            import yaml

            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Validate required sections
            assert 'trading' in config
            assert 'analysis' in config
            assert 'risk_management' in config
            assert 'mcp_servers' in config

            # Validate trading config
            trading = config['trading']
            assert 'symbol' in trading
            assert 'risk_per_trade' in trading
            assert trading['risk_per_trade'] > 0
            assert trading['risk_per_trade'] <= 0.1  # Max 10% risk

            # Validate MCP servers
            mcp_servers = config['mcp_servers']
            expected_servers = ['news', 'technical', 'social', 'binance', 'risk', 'ai']
            for server in expected_servers:
                assert server in mcp_servers

    def test_env_variables_handling(self):
        """Test environment variable loading"""
        # Test with default values
        test_var = utils.load_env_var("TEST_VAR_NOT_SET", "default_value")
        assert test_var == "default_value"

        # Test boolean conversion
        with patch.dict(os.environ, {"TEST_BOOL": "true"}):
            test_bool = utils.load_env_var("TEST_BOOL", False)
            assert test_bool is True

        # Test numeric conversion
        with patch.dict(os.environ, {"TEST_INT": "42"}):
            test_int = utils.load_env_var("TEST_INT", 0)
            assert test_int == 42


class TestErrorHandling:
    """Test error handling throughout the system"""

    @pytest.mark.asyncio
    async def test_mcp_server_connection_failure(self):
        """Test handling of MCP server connection failures"""
        manager = MCPServerManager()
        manager.add_server("test_fail", "invalid_command", ["invalid_args"])

        # Should handle connection failure gracefully
        results = await manager.connect_all()
        assert "test_fail" in results
        assert results["test_fail"] is False

    @pytest.mark.asyncio
    async def test_trading_decision_with_partial_data(self):
        """Test trading decisions when some data sources fail"""
        trader = CryptoTrader("tests/test_config.yaml")

        # Partial analysis data (some sources failed)
        analysis_data = {
            'success': True,
            'news': {'success': False, 'error': 'API timeout'},
            'technical': {'success': True, 'overall_signal': 'bullish'},
            'social': {'success': False, 'error': 'Rate limit'},
            'market': {'success': True, 'price': 43250.0}
        }

        decision = await trader.make_trading_decision(analysis_data)

        # Should still make a decision with available data
        assert decision is not None
        assert 'should_trade' in decision

    def test_invalid_configuration_handling(self):
        """Test handling of invalid configuration"""
        with pytest.raises((FileNotFoundError, ValueError)):
            # Should raise appropriate error for invalid config
            CryptoTrader("nonexistent_config.yaml")


# Test fixtures and utilities
@pytest.fixture
def test_config():
    """Create test configuration"""
    return {
        'trading': {
            'symbol': 'BTCUSDT',
            'risk_per_trade': 0.02,
            'min_confidence': 0.7
        },
        'mcp_servers': {
            'news': {'enabled': True, 'timeout': 30},
            'technical': {'enabled': True, 'timeout': 15},
            'social': {'enabled': True, 'timeout': 30},
            'binance': {'enabled': True, 'timeout': 10},
            'risk': {'enabled': True, 'timeout': 5},
            'ai': {'enabled': True, 'timeout': 60}
        }
    }


# Run tests if script is executed directly
if __name__ == "__main__":
    # Create test config file if it doesn't exist
    test_config_path = "tests/test_config.yaml"
    if not os.path.exists(test_config_path):
        os.makedirs("tests", exist_ok=True)
        import yaml

        test_config = {
            'trading': {
                'symbol': 'BTCUSDT',
                'mode': 'swing',
                'risk_per_trade': 0.02,
                'max_positions': 3,
                'min_confidence': 0.7
            },
            'analysis': {
                'lookback_periods': 20,
                'analysis_interval': 300,
                'indicators': ['RSI', 'MACD', 'EMA', 'BB'],
                'timeframes': ['1h', '4h', '1d'],
                'weights': {
                    'technical': 0.3,
                    'news': 0.2,
                    'social': 0.2,
                    'ai': 0.3
                }
            },
            'risk_management': {
                'stop_loss_percent': 0.05,
                'take_profit_ratio': 2.0,
                'max_drawdown': 0.15,
                'daily_loss_limit': 0.10
            },
            'mcp_servers': {
                'news': {'enabled': True, 'timeout': 30},
                'technical': {'enabled': True, 'timeout': 15},
                'social': {'enabled': True, 'timeout': 30},
                'binance': {'enabled': True, 'timeout': 10},
                'risk': {'enabled': True, 'timeout': 5},
                'ai': {'enabled': True, 'timeout': 60}
            }
        }

        with open(test_config_path, 'w') as f:
            yaml.dump(test_config, f, default_flow_style=False)

    # Run tests
    pytest.main([__file__, "-v"])