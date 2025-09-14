"""
Shared utility functions for the Crypto Trading MCP System
"""

import os
import asyncio
import logging
import hashlib
import json
import ssl
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import aiohttp
import backoff
from tenacity import retry, stop_after_attempt, wait_exponential
from constants import SystemConfig, Cache, Validation, Security, Utils


# Logging setup
def setup_logger(name: str, level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Setup structured logging for components"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger


# Environment and Configuration
def load_env_var(key: str, default: Any = None, required: bool = False) -> Any:
    """Load environment variable with type conversion"""
    value = os.getenv(key, default)

    if required and value is None:
        raise ValueError(f"Required environment variable {key} is not set")

    # Type conversion based on default type
    if default is not None and value is not None:
        if isinstance(default, bool):
            if isinstance(value, bool):
                return value
            return str(value).lower() in ('true', '1', 'yes', 'on')
        elif isinstance(default, int):
            return int(value)
        elif isinstance(default, float):
            return float(value)
        elif isinstance(default, list):
            return value.split(',') if value else []

    return value


def validate_config(config: Dict[str, Any], required_keys: List[str]) -> bool:
    """Validate configuration has all required keys"""
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(f"Missing required configuration keys: {missing_keys}")
    return True


# Data Processing Utilities
def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def round_decimal(value: float, places: int = Utils.DECIMAL_PLACES) -> float:
    """Round decimal to specified places"""
    if value is None:
        return 0.0

    decimal_value = Decimal(str(value))
    rounded = decimal_value.quantize(
        Decimal('0.' + '0' * places),
        rounding=ROUND_HALF_UP
    )
    return float(rounded)


def percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change"""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


# Time Utilities
def utc_now() -> datetime:
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


def timestamp_to_datetime(timestamp: Union[int, float, str]) -> datetime:
    """Convert timestamp to datetime"""
    try:
        if isinstance(timestamp, str):
            timestamp = float(timestamp)

        # Handle milliseconds
        if timestamp > 1e12:
            timestamp = timestamp / 1000

        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (ValueError, TypeError):
        return utc_now()


def datetime_to_timestamp(dt: datetime) -> float:
    """Convert datetime to timestamp"""
    return dt.timestamp()


# API Utilities
class RateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, max_calls: int, window_seconds: int = Utils.SECONDS_PER_MINUTE):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []

    async def acquire(self):
        """Acquire rate limit token"""
        now = utc_now().timestamp()

        # Remove old calls outside window
        self.calls = [call_time for call_time in self.calls
                     if now - call_time < self.window_seconds]

        # Check if we can make another call
        if len(self.calls) >= self.max_calls:
            sleep_time = self.window_seconds - (now - self.calls[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                return await self.acquire()

        self.calls.append(now)


@backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
async def make_http_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """Make HTTP request with retry logic"""
    try:
        async with session.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data if method.upper() != 'GET' else None,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            response.raise_for_status()
            return await response.json()

    except asyncio.TimeoutError:
        raise aiohttp.ClientError(f"Request timeout after {timeout}s")
    except aiohttp.ClientResponseError as e:
        raise aiohttp.ClientError(f"HTTP {e.status}: {e.message}")


# Caching Utilities
class SimpleCache:
    """Simple in-memory cache with TTL"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any, ttl_seconds: int = Cache.DEFAULT_TTL):
        """Set cache value with TTL"""
        expires_at = utc_now().timestamp() + ttl_seconds
        self._cache[key] = {
            'value': value,
            'expires_at': expires_at
        }

    def get(self, key: str) -> Optional[Any]:
        """Get cache value if not expired"""
        if key not in self._cache:
            return None

        cached_item = self._cache[key]
        if utc_now().timestamp() > cached_item['expires_at']:
            del self._cache[key]
            return None

        return cached_item['value']

    def delete(self, key: str):
        """Delete cache key"""
        self._cache.pop(key, None)

    def clear(self):
        """Clear all cache"""
        self._cache.clear()

    def size(self) -> int:
        """Get cache size"""
        return len(self._cache)


# Security Utilities
def generate_api_key() -> str:
    """Generate a secure API key"""
    import secrets
    return secrets.token_urlsafe(32)


def hash_string(text: str) -> str:
    """Hash string using SHA256"""
    return hashlib.sha256(text.encode()).hexdigest()


def verify_signature(data: str, signature: str, secret: str) -> bool:
    """Verify HMAC signature"""
    import hmac

    expected_signature = hmac.new(
        secret.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


# Data Validation
def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format"""
    return (
        isinstance(symbol, str) and
        len(symbol) >= 6 and
        symbol.isupper() and
        symbol.endswith('USDT')
    )


def validate_price(price: float, min_price: float = Validation.MIN_PRICE) -> bool:
    """Validate price value"""
    return isinstance(price, (int, float)) and price > min_price


def validate_quantity(quantity: float, min_quantity: float = Validation.MIN_QUANTITY) -> bool:
    """Validate quantity value"""
    return isinstance(quantity, (int, float)) and quantity > min_quantity


# JSON Utilities
def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely load JSON string"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Safely dump object to JSON"""
    try:
        return json.dumps(obj, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return default


# Async Utilities
async def gather_with_semaphore(tasks: List, max_concurrent: int = 10):
    """Execute tasks with concurrency limit"""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_task(task):
        async with semaphore:
            return await task

    bounded_tasks = [bounded_task(task) for task in tasks]
    return await asyncio.gather(*bounded_tasks, return_exceptions=True)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def retry_async_operation(operation, *args, **kwargs):
    """Retry async operation with exponential backoff"""
    return await operation(*args, **kwargs)


# Trading Utilities
def calculate_position_size(
    account_balance: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float
) -> float:
    """Calculate position size based on risk management"""
    if entry_price <= 0 or stop_loss_price <= 0:
        return 0.0

    risk_amount = account_balance * risk_per_trade
    price_risk = abs(entry_price - stop_loss_price)

    if price_risk <= 0:
        return 0.0

    position_size = risk_amount / price_risk
    return round_decimal(position_size, 6)


def calculate_pnl(
    entry_price: float,
    current_price: float,
    quantity: float,
    side: str = "long"
) -> Dict[str, float]:
    """Calculate P&L for position"""
    if side.lower() == "long":
        pnl = (current_price - entry_price) * quantity
    else:
        pnl = (entry_price - current_price) * quantity

    pnl_percent = (pnl / (entry_price * quantity)) * 100 if entry_price > 0 else 0.0

    return {
        "unrealized_pnl": round_decimal(pnl, 2),
        "unrealized_pnl_percent": round_decimal(pnl_percent, 2)
    }


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio"""
    if not returns or len(returns) < 2:
        return 0.0

    import statistics

    mean_return = statistics.mean(returns)
    std_return = statistics.stdev(returns)

    if std_return == 0:
        return 0.0

    return (mean_return - risk_free_rate) / std_return


# Health Check Utilities
async def check_service_health(url: str, timeout: int = 5) -> Dict[str, Any]:
    """Check health of external service"""
    try:
        start_time = utc_now()

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                latency = (utc_now() - start_time).total_seconds() * 1000

                return {
                    "status": "healthy" if response.status == 200 else "unhealthy",
                    "status_code": response.status,
                    "latency_ms": round(latency, 2),
                    "timestamp": start_time.isoformat()
                }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": 0,
            "timestamp": utc_now().isoformat()
        }


# Metrics Utilities
class MetricsCollector:
    """Simple metrics collector"""

    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = {}

    def increment_counter(self, name: str, value: int = 1):
        """Increment counter metric"""
        self.counters[name] = self.counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float):
        """Set gauge metric"""
        self.gauges[name] = value

    def record_histogram(self, name: str, value: float):
        """Record histogram value"""
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)

        # Keep only last values as per config
        if len(self.histograms[name]) > SystemConfig.MAX_HISTOGRAM_VALUES:
            self.histograms[name] = self.histograms[name][-SystemConfig.MAX_HISTOGRAM_VALUES:]

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        import statistics

        histogram_stats = {}
        for name, values in self.histograms.items():
            if values:
                histogram_stats[name] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "std": statistics.stdev(values) if len(values) > 1 else 0
                }

        return {
            "counters": self.counters,
            "gauges": self.gauges,
            "histograms": histogram_stats,
            "timestamp": utc_now().isoformat()
        }


# SSL Security Utilities
def create_ssl_context(verify_ssl: bool = True) -> ssl.SSLContext:
    """
    Create a secure SSL context for HTTPS connections.

    Args:
        verify_ssl: Whether to verify SSL certificates (default True for security)

    Returns:
        ssl.SSLContext: Properly configured SSL context

    Security Notes:
        - SSL verification is enabled by default for production security
        - Only disable SSL verification in development environments when absolutely necessary
        - Uses environment variable DISABLE_SSL_VERIFICATION for override control
    """
    # Check environment override (defaults to False for security)
    env_disable_ssl = load_env_var("DISABLE_SSL_VERIFICATION", default=False, required=False)

    if env_disable_ssl:
        logger = logging.getLogger(__name__)
        logger.warning(
            "🔒 SSL VERIFICATION DISABLED - This should only be used in development! "
            "Set DISABLE_SSL_VERIFICATION=false for production."
        )

    # Override verify_ssl if environment variable is set
    should_verify = verify_ssl and not env_disable_ssl

    # Create SSL context
    ssl_context = ssl.create_default_context()

    if should_verify:
        # Secure configuration (default)
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Set minimum TLS version for security
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

        # Load system CA certificates
        ssl_context.load_default_certs()

    else:
        # Development/testing configuration (INSECURE - use only when necessary)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Still set minimum TLS version even when not verifying certs
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

    return ssl_context


def create_secure_connector(verify_ssl: bool = True) -> aiohttp.TCPConnector:
    """
    Create a secure TCP connector for aiohttp with proper SSL handling.

    Args:
        verify_ssl: Whether to verify SSL certificates (default True)

    Returns:
        aiohttp.TCPConnector: Connector with secure SSL configuration
    """
    ssl_context = create_ssl_context(verify_ssl)

    return aiohttp.TCPConnector(
        ssl=ssl_context,
        limit=SystemConfig.MAX_CONCURRENT_REQUESTS * 10,  # Connection pool limit
        limit_per_host=SystemConfig.MAX_CONCURRENT_REQUESTS * 3,  # Per-host connection limit
        ttl_dns_cache=Cache.DEFAULT_TTL,  # DNS cache TTL
        use_dns_cache=True,
        enable_cleanup_closed=True
    )


# Global instances
cache = SimpleCache()
metrics = MetricsCollector()