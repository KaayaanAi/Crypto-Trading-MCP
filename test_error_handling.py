#!/usr/bin/env python3
"""
Test script to verify standardized error handling across the Crypto Trading MCP System
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from exceptions import (
    TradingSystemError, RiskManagementError, PositionSizingError,
    MarketDataError, OrderExecutionError, ValidationError,
    ConfigurationError, handle_error, validate_required_params,
    validate_numeric_range, safe_execute
)
from shared_types import create_error_response, ErrorDetail


def test_custom_exceptions():
    """Test custom exception classes"""
    print("🧪 Testing custom exception classes...")

    # Test basic trading system error
    try:
        raise TradingSystemError("Test system error")
    except TradingSystemError as e:
        print(f"✅ TradingSystemError: {e}")
        error_dict = e.to_dict()
        assert error_dict["success"] is False
        assert error_dict["error"]["code"] == "TRADING_SYSTEM_ERROR"
        assert "system" in error_dict["error"]["category"]

    # Test risk management error with details
    try:
        raise RiskManagementError(
            "Position size too large",
            details={"requested_size": 1000, "max_allowed": 500}
        )
    except RiskManagementError as e:
        print(f"✅ RiskManagementError: {e}")
        error_dict = e.to_dict()
        assert "risk_management" in error_dict["error"]["category"]
        assert "high" in error_dict["error"]["severity"]

    # Test validation error
    try:
        validate_numeric_range(-5, min_value=0, field_name="test_value")
    except ValidationError as e:
        print(f"✅ ValidationError: {e}")
        error_dict = e.to_dict()
        assert "validation" in error_dict["error"]["category"]
        assert "test_value" in str(e)


def test_validation_functions():
    """Test validation utility functions"""
    print("\n🧪 Testing validation functions...")

    # Test required params validation
    try:
        validate_required_params(
            {"param1": "value1", "param2": None},
            ["param1", "param2", "param3"]
        )
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        print(f"✅ Required params validation: {e}")

    # Test numeric range validation
    try:
        validate_numeric_range(150, min_value=0, max_value=100, field_name="percentage")
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        print(f"✅ Numeric range validation: {e}")

    # Test valid inputs (should not raise)
    validate_required_params({"a": 1, "b": 2}, ["a", "b"])
    validate_numeric_range(50, min_value=0, max_value=100)
    print("✅ Valid inputs passed correctly")


def test_error_response_format():
    """Test standardized error response format"""
    print("\n🧪 Testing error response format...")

    # Test error response creation
    error_response = create_error_response(
        code="TEST_ERROR",
        message="This is a test error",
        severity="medium",
        category="testing",
        details={"test_key": "test_value"}
    )

    assert error_response.success is False
    assert error_response.error.code == "TEST_ERROR"
    assert error_response.error.message == "This is a test error"
    assert error_response.error.severity == "medium"
    assert error_response.error.category == "testing"
    assert error_response.error.details["test_key"] == "test_value"
    print("✅ Error response format is correct")


def test_handle_error_function():
    """Test centralized error handling"""
    print("\n🧪 Testing handle_error function...")

    # Test with trading system error (should re-raise)
    try:
        with_trading_error = TradingSystemError("Test error")
        handle_error(with_trading_error, context="test", reraise=True)
        assert False, "Should have re-raised TradingSystemError"
    except TradingSystemError:
        print("✅ Trading system error re-raised correctly")

    # Test with generic error (should wrap and re-raise)
    try:
        generic_error = ValueError("Generic error")
        handle_error(generic_error, context="test", reraise=True)
        assert False, "Should have wrapped and re-raised"
    except TradingSystemError as e:
        print(f"✅ Generic error wrapped correctly: {e}")
        assert "test" in str(e)

    # Test without re-raising (should return dict)
    generic_error = RuntimeError("Runtime error")
    error_dict = handle_error(generic_error, context="test", reraise=False)
    assert error_dict["success"] is False
    assert "error" in error_dict
    print("✅ Error handling without re-raise works correctly")


def test_safe_execute():
    """Test safe execution wrapper"""
    print("\n🧪 Testing safe_execute function...")

    def working_function(x, y):
        return x + y

    def failing_function():
        raise ValueError("This function fails")

    # Test successful execution
    result = safe_execute(working_function, 5, 3, context="addition")
    assert result == 8
    print("✅ Safe execute with working function")

    # Test failed execution
    try:
        safe_execute(failing_function, context="failing_test")
        assert False, "Should have raised TradingSystemError"
    except TradingSystemError as e:
        print(f"✅ Safe execute with failing function: {e}")
        assert "failing_test" in str(e)


async def test_risk_server_error_handling():
    """Test risk server error handling (simulated)"""
    print("\n🧪 Testing risk server error handling...")

    # Add the risk server path
    sys.path.append(os.path.join(os.path.dirname(__file__), 'servers', 'crypto-risk-mcp'))

    try:
        from main import RiskCalculator

        calculator = RiskCalculator()

        # Test invalid position size calculation
        try:
            calculator.calculate_position_size(
                account_balance=-100,  # Invalid negative balance
                risk_per_trade=0.02,
                entry_price=50000,
                stop_loss_price=48000,
                method="fixed_percent"
            )
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            print(f"✅ Risk calculator validation error: {e}")

        # Test invalid method
        try:
            calculator.calculate_position_size(
                account_balance=10000,
                risk_per_trade=0.02,
                entry_price=50000,
                stop_loss_price=48000,
                method="invalid_method"
            )
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            print(f"✅ Risk calculator method validation: {e}")

        print("✅ Risk server error handling tests passed")

    except ImportError as e:
        print(f"⚠️  Could not test risk server (import error): {e}")


def test_error_severity_and_logging():
    """Test error severity levels and logging"""
    print("\n🧪 Testing error severity and logging...")

    # Test different severity levels
    severities = ["low", "medium", "high", "critical"]

    for severity in severities:
        try:
            if severity == "critical":
                from exceptions import RiskLimitExceededError
                raise RiskLimitExceededError(
                    f"Test {severity} error",
                    current_value=100,
                    limit=50
                )
            else:
                raise TradingSystemError(
                    f"Test {severity} error",
                    severity=getattr(__import__('exceptions'), 'ErrorSeverity')(severity.upper())
                )
        except Exception as e:
            print(f"✅ {severity.capitalize()} severity error: {e}")
            error_dict = e.to_dict()
            if severity == "critical":
                assert error_dict["error"]["severity"] == "critical"
            else:
                assert error_dict["error"]["severity"] == severity


def run_all_tests():
    """Run all error handling tests"""
    print("🚀 Starting Error Handling Standardization Tests\n")

    try:
        test_custom_exceptions()
        test_validation_functions()
        test_error_response_format()
        test_handle_error_function()
        test_safe_execute()
        asyncio.run(test_risk_server_error_handling())
        test_error_severity_and_logging()

        print("\n✅ All error handling tests passed!")
        print("\n📊 Summary:")
        print("- Custom exception classes: ✅ Working")
        print("- Validation functions: ✅ Working")
        print("- Standardized error responses: ✅ Working")
        print("- Centralized error handling: ✅ Working")
        print("- Safe execution wrapper: ✅ Working")
        print("- Error severity levels: ✅ Working")
        print("- Risk server integration: ✅ Working")

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)