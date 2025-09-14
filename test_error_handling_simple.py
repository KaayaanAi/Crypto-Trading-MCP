#!/usr/bin/env python3
"""
Simple test script to verify standardized error handling core functionality
"""

import sys
import os
from typing import Dict, Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

try:
    from exceptions import (
        TradingSystemError, RiskManagementError, PositionSizingError,
        MarketDataError, OrderExecutionError, ValidationError,
        ConfigurationError, handle_error, validate_required_params,
        validate_numeric_range, safe_execute, ErrorSeverity, ErrorCategory
    )
    EXCEPTIONS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Could not import exceptions module: {e}")
    EXCEPTIONS_AVAILABLE = False


def test_basic_exception_functionality():
    """Test basic exception functionality without external dependencies"""
    print("🧪 Testing basic exception functionality...")

    if not EXCEPTIONS_AVAILABLE:
        print("❌ Exceptions module not available, skipping tests")
        return False

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

    return True


def test_validation_functions():
    """Test validation utility functions"""
    print("\n🧪 Testing validation functions...")

    if not EXCEPTIONS_AVAILABLE:
        print("❌ Exceptions module not available, skipping tests")
        return False

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

    return True


def test_error_categories_and_severities():
    """Test error categories and severities"""
    print("\n🧪 Testing error categories and severities...")

    if not EXCEPTIONS_AVAILABLE:
        print("❌ Exceptions module not available, skipping tests")
        return False

    # Test error categories
    categories = [
        ErrorCategory.VALIDATION,
        ErrorCategory.RISK_MANAGEMENT,
        ErrorCategory.MARKET_DATA,
        ErrorCategory.ORDER_EXECUTION,
        ErrorCategory.CONFIGURATION
    ]

    for category in categories:
        print(f"✅ Error category available: {category.value}")

    # Test error severities
    severities = [
        ErrorSeverity.LOW,
        ErrorSeverity.MEDIUM,
        ErrorSeverity.HIGH,
        ErrorSeverity.CRITICAL
    ]

    for severity in severities:
        print(f"✅ Error severity available: {severity.value}")

    return True


def test_handle_error_function():
    """Test centralized error handling"""
    print("\n🧪 Testing handle_error function...")

    if not EXCEPTIONS_AVAILABLE:
        print("❌ Exceptions module not available, skipping tests")
        return False

    # Test without re-raising (should return dict)
    generic_error = RuntimeError("Runtime error")
    error_dict = handle_error(generic_error, context="test", reraise=False)
    assert error_dict["success"] is False
    assert "error" in error_dict
    print("✅ Error handling without re-raise works correctly")

    # Test with trading system error (should re-raise)
    try:
        with_trading_error = TradingSystemError("Test error")
        handle_error(with_trading_error, context="test", reraise=True)
        assert False, "Should have re-raised TradingSystemError"
    except TradingSystemError:
        print("✅ Trading system error re-raised correctly")

    return True


def test_safe_execute():
    """Test safe execution wrapper"""
    print("\n🧪 Testing safe_execute function...")

    if not EXCEPTIONS_AVAILABLE:
        print("❌ Exceptions module not available, skipping tests")
        return False

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

    return True


def test_error_response_format():
    """Test error response format"""
    print("\n🧪 Testing error response format...")

    if not EXCEPTIONS_AVAILABLE:
        print("❌ Exceptions module not available, skipping tests")
        return False

    # Create a test error and check its format
    error = TradingSystemError(
        "Test error message",
        details={"key1": "value1", "key2": 42}
    )

    error_dict = error.to_dict()

    # Check required fields
    required_fields = ["success", "error"]
    for field in required_fields:
        assert field in error_dict, f"Missing required field: {field}"

    # Check error structure
    error_info = error_dict["error"]
    error_required_fields = ["code", "message", "severity", "category", "details", "timestamp"]
    for field in error_required_fields:
        assert field in error_info, f"Missing required error field: {field}"

    assert error_dict["success"] is False
    assert error_info["code"] == "TRADING_SYSTEM_ERROR"
    assert error_info["message"] == "Test error message"
    assert error_info["details"]["key1"] == "value1"
    assert error_info["details"]["key2"] == 42

    print("✅ Error response format is standardized and correct")
    return True


def run_simple_tests():
    """Run simplified error handling tests"""
    print("🚀 Starting Simple Error Handling Tests\n")

    test_results = []

    test_results.append(test_basic_exception_functionality())
    test_results.append(test_validation_functions())
    test_results.append(test_error_categories_and_severities())
    test_results.append(test_handle_error_function())
    test_results.append(test_safe_execute())
    test_results.append(test_error_response_format())

    success_count = sum(test_results)
    total_count = len(test_results)

    print(f"\n📊 Test Results: {success_count}/{total_count} passed")

    if success_count == total_count:
        print("\n✅ All simple error handling tests passed!")
        print("\n📋 Verified Features:")
        print("- Custom exception hierarchy: ✅")
        print("- Standardized error response format: ✅")
        print("- Validation functions: ✅")
        print("- Error categories and severities: ✅")
        print("- Centralized error handling: ✅")
        print("- Safe execution wrapper: ✅")
        return True
    else:
        print(f"\n❌ {total_count - success_count} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_simple_tests()

    if success:
        print("\n🎉 Error handling standardization is working correctly!")
        print("\nNext steps:")
        print("1. Install required dependencies (pydantic, etc.) for full testing")
        print("2. Test with actual MCP server integration")
        print("3. Verify error handling in production scenarios")

    sys.exit(0 if success else 1)