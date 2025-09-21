#!/usr/bin/env python3
"""
Custom exception classes for the Crypto Trading MCP System

Provides domain-specific exceptions with proper error handling,
logging, and standardized error response formats.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification"""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    API_LIMIT = "api_limit"
    MARKET_DATA = "market_data"
    ORDER_EXECUTION = "order_execution"
    RISK_MANAGEMENT = "risk_management"
    CONFIGURATION = "configuration"
    SYSTEM = "system"


class BaseTradingError(Exception):
    """Base exception class for all trading system errors"""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()

        # Log the error automatically
        self._log_error()

    def _log_error(self):
        """Log the error with appropriate level based on severity"""
        logger = logging.getLogger(self.__class__.__module__)

        log_message = f"{self.error_code}: {self.message}"
        if self.details:
            log_message += f" | Details: {self.details}"
        if self.cause:
            log_message += f" | Caused by: {self.cause}"

        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=True)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=True)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to standardized dictionary format"""
        return {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
                "severity": self.severity.value,
                "category": self.category.value,
                "details": self.details,
                "timestamp": self.timestamp.isoformat(),
            },
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class TradingSystemError(BaseTradingError):
    """General trading system errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message=message, error_code="TRADING_SYSTEM_ERROR", category=ErrorCategory.SYSTEM, **kwargs)


class RiskManagementError(BaseTradingError):
    """Risk management specific errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="RISK_MANAGEMENT_ERROR",
            category=ErrorCategory.RISK_MANAGEMENT,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class PositionSizingError(RiskManagementError):
    """Position sizing calculation errors"""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("error_code", "POSITION_SIZING_ERROR")
        super().__init__(message, **kwargs)


class RiskLimitExceededError(RiskManagementError):
    """Risk limits exceeded errors"""

    def __init__(self, message: str, current_value: float, limit: float, **kwargs):
        details = kwargs.get("details", {})
        details.update({"current_value": current_value, "limit": limit, "excess": current_value - limit})
        kwargs["details"] = details
        # Override the parent's error_code and severity
        kwargs["error_code"] = "RISK_LIMIT_EXCEEDED"
        kwargs["severity"] = ErrorSeverity.CRITICAL
        # Call BaseTradingError directly to avoid parent's __init__ setting error_code
        BaseTradingError.__init__(self, message=message, category=ErrorCategory.RISK_MANAGEMENT, **kwargs)


class MarketDataError(BaseTradingError):
    """Market data related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message=message, error_code="MARKET_DATA_ERROR", category=ErrorCategory.MARKET_DATA, **kwargs)


class PriceDataError(MarketDataError):
    """Price data specific errors"""

    def __init__(self, message: str, symbol: str = None, **kwargs):
        details = kwargs.get("details", {})
        if symbol:
            details["symbol"] = symbol
        kwargs["details"] = details
        kwargs.setdefault("error_code", "PRICE_DATA_ERROR")
        super().__init__(message, **kwargs)


class OrderExecutionError(BaseTradingError):
    """Order execution errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="ORDER_EXECUTION_ERROR",
            category=ErrorCategory.ORDER_EXECUTION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class InsufficientBalanceError(OrderExecutionError):
    """Insufficient balance for order execution"""

    def __init__(self, message: str, required: float, available: float, **kwargs):
        details = kwargs.get("details", {})
        details.update(
            {"required_balance": required, "available_balance": available, "shortfall": required - available}
        )
        kwargs["details"] = details
        kwargs.setdefault("error_code", "INSUFFICIENT_BALANCE")
        super().__init__(message, **kwargs)


class InvalidOrderError(OrderExecutionError):
    """Invalid order parameters"""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("error_code", "INVALID_ORDER")
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)


class ConfigurationError(BaseTradingError):
    """Configuration errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class MissingApiKeyError(ConfigurationError):
    """Missing API key configuration"""

    def __init__(self, service: str, **kwargs):
        message = f"Missing API key for {service}"
        details = kwargs.get("details", {})
        details["service"] = service
        kwargs["details"] = details
        kwargs.setdefault("error_code", "MISSING_API_KEY")
        kwargs.setdefault("severity", ErrorSeverity.CRITICAL)
        super().__init__(message, **kwargs)


class ApiError(BaseTradingError):
    """API related errors"""

    def __init__(self, message: str, status_code: int = None, **kwargs):
        details = kwargs.get("details", {})
        if status_code:
            details["status_code"] = status_code
        kwargs["details"] = details
        kwargs.setdefault("error_code", "API_ERROR")
        kwargs.setdefault("category", ErrorCategory.NETWORK)
        super().__init__(message, **kwargs)


class ApiRateLimitError(ApiError):
    """API rate limit exceeded"""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after_seconds"] = retry_after
        kwargs["details"] = details
        kwargs.setdefault("error_code", "API_RATE_LIMIT")
        kwargs.setdefault("category", ErrorCategory.API_LIMIT)
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)


class ValidationError(BaseTradingError):
    """Input validation errors"""

    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["invalid_value"] = str(value)
        kwargs["details"] = details
        kwargs.setdefault("error_code", "VALIDATION_ERROR")
        kwargs.setdefault("category", ErrorCategory.VALIDATION)
        kwargs.setdefault("severity", ErrorSeverity.MEDIUM)
        super().__init__(message, **kwargs)


class NetworkError(BaseTradingError):
    """Network connectivity errors"""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("error_code", "NETWORK_ERROR")
        kwargs.setdefault("category", ErrorCategory.NETWORK)
        kwargs.setdefault("severity", ErrorSeverity.HIGH)
        super().__init__(message, **kwargs)


class TimeoutError(NetworkError):
    """Request timeout errors"""

    def __init__(self, message: str, timeout_seconds: float = None, **kwargs):
        details = kwargs.get("details", {})
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        kwargs["details"] = details
        kwargs.setdefault("error_code", "TIMEOUT_ERROR")
        super().__init__(message, **kwargs)


# Error handling utilities
def handle_error(
    error: Exception, context: str = "", reraise: bool = True, default_response: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Centralized error handling utility

    Args:
        error: The exception to handle
        context: Additional context for logging
        reraise: Whether to reraise the exception
        default_response: Default response if not reraising

    Returns:
        Standardized error response dict
    """
    if isinstance(error, BaseTradingError):
        response = error.to_dict()
    else:
        # Convert generic exceptions to trading system errors
        trading_error = TradingSystemError(
            message=str(error), details={"original_error_type": type(error).__name__, "context": context}, cause=error
        )
        response = trading_error.to_dict()

    if reraise:
        if isinstance(error, BaseTradingError):
            raise error
        else:
            # Wrap in trading system error if not already a trading error
            raise TradingSystemError(message=f"Unexpected error in {context}: {str(error)}", cause=error) from error

    return (
        response
        if response
        else (
            default_response
            or {
                "success": False,
                "error": {
                    "code": "UNKNOWN_ERROR",
                    "message": "An unexpected error occurred",
                    "severity": "high",
                    "category": "system",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }
        )
    )


def create_error_response(
    error_code: str,
    message: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a standardized error response without raising an exception

    Args:
        error_code: Error code identifier
        message: Human-readable error message
        severity: Error severity level
        category: Error category
        details: Additional error details

    Returns:
        Standardized error response dict
    """
    return {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "severity": severity.value,
            "category": category.value,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        },
    }


def validate_required_params(params: Dict[str, Any], required: List[str]) -> None:
    """
    Validate that required parameters are present and not None

    Args:
        params: Dictionary of parameters to validate
        required: List of required parameter names

    Raises:
        ValidationError: If any required parameters are missing
    """
    missing = []
    for param in required:
        if param not in params or params[param] is None:
            missing.append(param)

    if missing:
        raise ValidationError(
            f"Missing required parameters: {', '.join(missing)}",
            details={"missing_parameters": missing, "provided_parameters": list(params.keys())},
        )


def validate_numeric_range(
    value: float, min_value: Optional[float] = None, max_value: Optional[float] = None, field_name: str = "value"
) -> None:
    """
    Validate that a numeric value is within specified range

    Args:
        value: Value to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        field_name: Name of the field being validated

    Raises:
        ValidationError: If value is outside the specified range
    """
    if min_value is not None and value < min_value:
        raise ValidationError(
            f"{field_name} must be at least {min_value}",
            field=field_name,
            value=value,
            details={"min_value": min_value, "max_value": max_value},
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"{field_name} must be at most {max_value}",
            field=field_name,
            value=value,
            details={"min_value": min_value, "max_value": max_value},
        )


def safe_execute(func, *args, context: str = "", default_return: Any = None, **kwargs) -> Any:
    """
    Safely execute a function with proper error handling

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        context: Context for error logging
        default_return: Default value to return on error
        **kwargs: Keyword arguments for the function

    Returns:
        Function result or default_return on error
    """
    try:
        return func(*args, **kwargs)
    except BaseTradingError:
        # Re-raise trading errors as-is
        raise
    except Exception as e:
        # Convert generic exceptions to trading system errors
        raise TradingSystemError(
            message=f"Error in {context or func.__name__}: {str(e)}",
            details={"function": func.__name__, "context": context},
            cause=e,
        ) from e
