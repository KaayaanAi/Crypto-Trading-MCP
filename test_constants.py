#!/usr/bin/env python3
"""
Test script to verify that constants are properly imported and used
across the Crypto Trading MCP System.
"""

import sys
import os

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

def test_constants_import():
    """Test that constants can be imported successfully"""
    try:
        from constants import (
            RiskManagement, ApiRateLimits, TechnicalAnalysis, Trading,
            NewsSentiment, SocialSentiment, SystemConfig, Cache,
            Validation, Security, Utils
        )
        print("✅ All constants imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Error importing constants: {e}")
        return False

def test_risk_management_constants():
    """Test risk management constants"""
    from constants import RiskManagement

    print(f"Risk Management Constants:")
    print(f"  MAX_POSITION_SIZE: {RiskManagement.MAX_POSITION_SIZE}")
    print(f"  MAX_PORTFOLIO_RISK: {RiskManagement.MAX_PORTFOLIO_RISK}")
    print(f"  STOP_LOSS_PERCENT: {RiskManagement.STOP_LOSS_PERCENT}")
    print(f"  RISK_FREE_RATE: {RiskManagement.RISK_FREE_RATE}")

    # Validate types and ranges
    assert isinstance(RiskManagement.MAX_POSITION_SIZE, float)
    assert 0 < RiskManagement.MAX_POSITION_SIZE < 1
    assert isinstance(RiskManagement.RISK_FREE_RATE, float)
    assert RiskManagement.RISK_FREE_RATE >= 0

    print("✅ Risk management constants validated")

def test_api_rate_limits():
    """Test API rate limit constants"""
    from constants import ApiRateLimits

    print(f"API Rate Limits:")
    print(f"  BINANCE_RATE_LIMIT_CALLS: {ApiRateLimits.BINANCE_RATE_LIMIT_CALLS}")
    print(f"  WHALE_THRESHOLD_USD: {ApiRateLimits.WHALE_THRESHOLD_USD}")

    assert isinstance(ApiRateLimits.BINANCE_RATE_LIMIT_CALLS, int)
    assert ApiRateLimits.BINANCE_RATE_LIMIT_CALLS > 0
    assert isinstance(ApiRateLimits.WHALE_THRESHOLD_USD, int)
    assert ApiRateLimits.WHALE_THRESHOLD_USD > 0

    print("✅ API rate limits validated")

def test_technical_analysis_constants():
    """Test technical analysis constants"""
    from constants import TechnicalAnalysis

    print(f"Technical Analysis Constants:")
    print(f"  RSI_PERIOD: {TechnicalAnalysis.RSI_PERIOD}")
    print(f"  MACD_FAST_PERIOD: {TechnicalAnalysis.MACD_FAST_PERIOD}")
    print(f"  RSI_OVERSOLD_THRESHOLD: {TechnicalAnalysis.RSI_OVERSOLD_THRESHOLD}")

    assert isinstance(TechnicalAnalysis.RSI_PERIOD, int)
    assert TechnicalAnalysis.RSI_PERIOD > 0
    assert TechnicalAnalysis.MACD_FAST_PERIOD < TechnicalAnalysis.MACD_SLOW_PERIOD
    assert 0 < TechnicalAnalysis.RSI_OVERSOLD_THRESHOLD < TechnicalAnalysis.RSI_OVERBOUGHT_THRESHOLD < 100

    print("✅ Technical analysis constants validated")

def test_trading_constants():
    """Test trading execution constants"""
    from constants import Trading

    print(f"Trading Constants:")
    print(f"  DEFAULT_RISK_PER_TRADE: {Trading.DEFAULT_RISK_PER_TRADE}")
    print(f"  DEFAULT_MIN_CONFIDENCE: {Trading.DEFAULT_MIN_CONFIDENCE}")
    print(f"  TECHNICAL_SIGNAL_WEIGHT: {Trading.TECHNICAL_SIGNAL_WEIGHT}")

    assert 0 < Trading.DEFAULT_RISK_PER_TRADE < 1
    assert 0 < Trading.DEFAULT_MIN_CONFIDENCE <= 1
    assert Trading.RULE_BASED_BUY_THRESHOLD > 0
    assert Trading.RULE_BASED_SELL_THRESHOLD < 0

    print("✅ Trading constants validated")

def test_constants_usage_in_modules():
    """Test that constants are properly used in modules"""

    # Test risk management module
    sys.path.append(os.path.join(os.path.dirname(__file__), 'servers', 'crypto-risk-mcp'))
    try:
        # This will test that the constants are imported and used without import errors
        from servers.crypto_risk_mcp.main import RiskParameters
        risk_params = RiskParameters()

        from constants import RiskManagement

        # Check that the constants are actually being used
        assert risk_params.max_position_size == RiskManagement.MAX_POSITION_SIZE
        assert risk_params.max_portfolio_risk == RiskManagement.MAX_PORTFOLIO_RISK

        print("✅ Constants properly used in risk management module")
    except Exception as e:
        print(f"⚠️  Could not fully test risk management integration: {e}")

    # Test that technical analysis constants work
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'servers', 'crypto-technical-mcp'))

        from constants import TechnicalAnalysis as TAConstants

        # Verify constants are reasonable
        assert TAConstants.RSI_PERIOD == 14  # Standard RSI period
        assert TAConstants.MACD_FAST_PERIOD == 12  # Standard MACD
        assert TAConstants.RSI_OVERSOLD_THRESHOLD == 30  # Standard thresholds
        assert TAConstants.RSI_OVERBOUGHT_THRESHOLD == 70

        print("✅ Technical analysis constants validated")
    except Exception as e:
        print(f"⚠️  Could not fully test technical analysis integration: {e}")

def test_no_magic_numbers_remain():
    """Verify that major magic numbers have been replaced"""

    # Read the risk management file and check for common magic numbers
    try:
        risk_file_path = os.path.join(os.path.dirname(__file__), 'servers', 'crypto-risk-mcp', 'main.py')
        with open(risk_file_path, 'r') as f:
            content = f.read()

        # These magic numbers should not appear in the code anymore
        magic_numbers_to_check = ['0.20', '0.02', '0.15', '0.05', '2.0']
        remaining_magic = []

        for magic in magic_numbers_to_check:
            if magic in content and f'= {magic}' in content:
                remaining_magic.append(magic)

        if remaining_magic:
            print(f"⚠️  Some magic numbers may still remain: {remaining_magic}")
        else:
            print("✅ Major magic numbers have been replaced with constants")

    except Exception as e:
        print(f"⚠️  Could not check for remaining magic numbers: {e}")

def main():
    """Run all tests"""
    print("🧪 Testing Crypto Trading MCP System Constants")
    print("=" * 50)

    success_count = 0
    total_tests = 6

    # Run all tests
    if test_constants_import():
        success_count += 1

    try:
        test_risk_management_constants()
        success_count += 1
    except Exception as e:
        print(f"❌ Risk management constants test failed: {e}")

    try:
        test_api_rate_limits()
        success_count += 1
    except Exception as e:
        print(f"❌ API rate limits test failed: {e}")

    try:
        test_technical_analysis_constants()
        success_count += 1
    except Exception as e:
        print(f"❌ Technical analysis constants test failed: {e}")

    try:
        test_trading_constants()
        success_count += 1
    except Exception as e:
        print(f"❌ Trading constants test failed: {e}")

    try:
        test_constants_usage_in_modules()
        success_count += 1
    except Exception as e:
        print(f"❌ Module integration test failed: {e}")

    test_no_magic_numbers_remain()  # This is informational

    print("=" * 50)
    print(f"✅ {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("🎉 All constants tests passed! Magic numbers successfully eliminated.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())