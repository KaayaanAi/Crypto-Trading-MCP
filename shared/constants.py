"""
Comprehensive constants module for the Crypto Trading MCP System.

This module centralizes all magic numbers and configuration constants used
throughout the system to improve maintainability and avoid duplication.

Categories:
- RISK_MANAGEMENT: Risk parameters and limits
- API_RATE_LIMITS: Rate limiting configuration for exchanges
- TECHNICAL_ANALYSIS: Technical indicator parameters
- TRADING: Trading execution parameters
- NEWS_SENTIMENT: News analysis configuration
- SOCIAL_SENTIMENT: Social media analysis parameters
- SYSTEM: System-wide configuration constants
- VALIDATION: Data validation thresholds
- SECURITY: Security and SSL configuration
- CACHE: Caching configuration
"""


# =============================================================================
# RISK MANAGEMENT CONSTANTS
# =============================================================================


class RiskManagement:
    """Risk management parameters and limits"""

    # Position sizing limits
    MAX_POSITION_SIZE = 0.20  # 20% max per position
    MAX_PORTFOLIO_RISK = 0.02  # 2% max portfolio risk per trade
    MAX_DRAWDOWN = 0.15  # 15% max drawdown threshold

    # Risk/reward parameters
    STOP_LOSS_PERCENT = 0.05  # 5% stop loss
    TAKE_PROFIT_RATIO = 2.0  # 1:2 risk/reward ratio

    # Correlation limits
    MAX_CORRELATION = 0.7  # Max correlation between positions
    HIGH_CORRELATION_THRESHOLD = 0.8  # Threshold for high correlation alerts
    MEDIUM_CORRELATION_THRESHOLD = 0.6  # Threshold for medium correlation alerts

    # Risk assessment thresholds
    RISK_FREE_RATE = 0.02  # 2% annual risk-free rate
    CRITICAL_DRAWDOWN_THRESHOLD = 0.15  # 15% critical drawdown
    WARNING_DRAWDOWN_THRESHOLD = 0.10  # 10% warning drawdown
    ELEVATED_DRAWDOWN_THRESHOLD = 0.08  # 8% elevated risk threshold

    # Kelly Criterion parameters
    DEFAULT_WIN_RATE = 0.60  # 60% default win rate assumption
    MAX_KELLY_FRACTION = 0.25  # Maximum Kelly fraction (25%)
    KELLY_HIGH_RISK_THRESHOLD = 0.15  # High risk threshold for Kelly
    KELLY_MEDIUM_RISK_THRESHOLD = 0.05  # Medium risk threshold for Kelly

    # Portfolio assessment
    HIGH_CONCENTRATION_THRESHOLD = 0.3  # 30% high concentration
    MEDIUM_CONCENTRATION_THRESHOLD = 0.2  # 20% medium concentration

    # Daily loss thresholds
    SIGNIFICANT_DAILY_LOSS = 5000.0  # $5000 significant daily loss
    MODERATE_DAILY_LOSS = 1000.0  # $1000 moderate daily loss

    # VaR parameters
    DEFAULT_VAR_CONFIDENCE_LEVEL = 0.05  # 95% VaR confidence
    VAR_TIME_HORIZON_DAYS = 1  # 1-day VaR
    CRYPTO_VOLATILITY_ASSUMPTION = 0.75  # 75% annual volatility
    ASSET_CORRELATION_ASSUMPTION = 0.6  # 60% default correlation
    VAR_BREACH_WARNING_THRESHOLD = 2  # Multiple VaR breaches warning

    # Account balance assumptions (for calculations)
    DEMO_ACCOUNT_BALANCE = 100000.0  # $100k demo account


# =============================================================================
# API RATE LIMITS
# =============================================================================

class ApiRateLimits:
    """API rate limiting configuration"""

    # Binance rate limits
    BINANCE_RATE_LIMIT_CALLS = 1200  # calls per window
    BINANCE_RATE_LIMIT_WINDOW = 60  # 60 seconds window
    BINANCE_ORDER_RATE_LIMIT_CALLS = 10  # order calls per window
    BINANCE_ORDER_RATE_LIMIT_WINDOW = 1  # 1 second window

    # Whale detection threshold
    WHALE_THRESHOLD_USD = 1000000  # $1M USD whale threshold

    # HTTP request timeouts
    DEFAULT_HTTP_TIMEOUT = 30  # 30 seconds default timeout
    BINANCE_API_TIMEOUT = 30  # Binance API timeout
    QUICK_REQUEST_TIMEOUT = 10  # Quick request timeout
    LONG_REQUEST_TIMEOUT = 60  # Long request timeout (AI analysis)

    # Connection limits
    CONNECTION_POOL_LIMIT = 100  # Max connections in pool
    CONNECTION_PER_HOST_LIMIT = 30  # Max connections per host
    DNS_CACHE_TTL = 300  # DNS cache TTL in seconds


# =============================================================================
# TECHNICAL ANALYSIS CONSTANTS
# =============================================================================

class TechnicalAnalysis:
    """Technical analysis indicator parameters"""

    # RSI parameters
    RSI_PERIOD = 14  # Standard RSI period
    RSI_OVERSOLD_THRESHOLD = 30  # RSI oversold level
    RSI_OVERBOUGHT_THRESHOLD = 70  # RSI overbought level

    # MACD parameters
    MACD_FAST_PERIOD = 12  # MACD fast EMA period
    MACD_SLOW_PERIOD = 26  # MACD slow EMA period
    MACD_SIGNAL_PERIOD = 9  # MACD signal line period

    # Moving averages
    EMA_SHORT_PERIOD = 20  # Short-term EMA
    EMA_LONG_PERIOD = 50  # Long-term EMA

    # Bollinger Bands
    BOLLINGER_PERIOD = 20  # Bollinger Bands period
    BOLLINGER_STD_DEV = 2.0  # Standard deviations for bands

    # Support/Resistance detection
    SUPPORT_RESISTANCE_WINDOW = 5  # Window for local min/max detection
    PRICE_TOLERANCE_PERCENT = 0.01  # 1% price tolerance for level detection
    MAX_SUPPORT_RESISTANCE_LEVELS = 5  # Max levels to return

    # Pattern detection
    MIN_CANDLES_FOR_PATTERNS = 20  # Minimum candles for pattern detection
    TREND_ANALYSIS_CANDLES = 20  # Candles for trend analysis
    DOUBLE_TOP_TOLERANCE_PERCENT = 0.02  # 2% tolerance for double top
    PATTERN_MIN_CANDLES = 50  # Minimum candles for complex patterns
    PATTERN_LOCAL_WINDOW = 5  # Window for local extrema in patterns

    # Data fetching
    DEFAULT_CANDLE_LIMIT = 200  # Default number of candles to fetch
    MAX_CANDLE_LIMIT = 500  # Maximum candles for analysis
    EXTENDED_CANDLE_LIMIT = 1000  # Extended limit for whale tracking

    # Chart analysis
    CHART_PATTERN_CONFIDENCE_THRESHOLD = 0.7  # Min confidence for patterns
    TREND_SLOPE_SIGNIFICANCE_FACTOR = 0.01  # Trend slope significance
    MAX_TREND_CONFIDENCE = 0.9  # Maximum trend confidence

    # Multi-timeframe analysis
    DEFAULT_TIMEFRAMES = ["1h", "4h", "1d"]  # Default timeframes to analyze
    HIGH_FREQUENCY_TIMEFRAMES = ["1m", "5m"]  # High frequency timeframes


# =============================================================================
# TRADING EXECUTION CONSTANTS
# =============================================================================

class Trading:
    """Trading execution parameters"""

    # Order precision
    PRICE_DECIMAL_PLACES = 8  # Price precision
    QUANTITY_DECIMAL_PLACES = 6  # Quantity precision

    # Minimum trade values
    MIN_PRICE_VALUE = 0.0001  # Minimum valid price
    MIN_QUANTITY_VALUE = 0.001  # Minimum valid quantity
    DUST_THRESHOLD = 0.001  # Balance dust threshold

    # Default trading parameters
    DEFAULT_RISK_PER_TRADE = 0.02  # 2% risk per trade
    DEFAULT_MIN_CONFIDENCE = 0.7  # 70% minimum confidence

    # Analysis intervals
    DEFAULT_ANALYSIS_INTERVAL = 300  # 5 minutes analysis interval
    FAST_ANALYSIS_INTERVAL = 60  # 1 minute fast interval
    SLOW_ANALYSIS_INTERVAL = 900  # 15 minutes slow interval

    # Trading thresholds
    RULE_BASED_BUY_THRESHOLD = 0.3  # Rule-based buy threshold
    RULE_BASED_SELL_THRESHOLD = -0.3  # Rule-based sell threshold
    CONFIDENCE_BOOST = 0.3  # Confidence boost for rule-based decisions
    MAX_RULE_CONFIDENCE = 0.8  # Maximum rule-based confidence

    # Position monitoring
    POSITION_CHECK_INTERVAL = 30  # Position check interval in seconds
    ERROR_RETRY_DELAY = 60  # Retry delay on error in seconds

    # Signal weighting
    TECHNICAL_SIGNAL_WEIGHT = 0.6  # Technical analysis weight
    NEWS_SENTIMENT_WEIGHT = 0.5  # News sentiment weight
    SOCIAL_SENTIMENT_WEIGHT = 0.4  # Social sentiment weight


# =============================================================================
# NEWS SENTIMENT CONSTANTS
# =============================================================================

class NewsSentiment:
    """News analysis and sentiment parameters"""

    # Source weights (reliability scoring)
    NEWS_SOURCE_WEIGHTS = {
        "coindesk": 0.9,  # Highest weight for CoinDesk
        "cointelegraph": 0.8,
        "decrypt": 0.7,
        "bitcoinist": 0.6,
        "cryptopotato": 0.6
    }

    # Sentiment analysis thresholds
    POSITIVE_SENTIMENT_THRESHOLD = 0.5  # Positive sentiment threshold
    NEGATIVE_SENTIMENT_THRESHOLD = -0.5  # Negative sentiment threshold
    NEUTRAL_SENTIMENT_RANGE = 0.2  # Neutral sentiment range

    # Content analysis
    MIN_ARTICLE_LENGTH = 100  # Minimum article length for analysis
    MAX_ARTICLES_PER_SOURCE = 20  # Maximum articles per source
    NEWS_RELEVANCE_THRESHOLD = 0.3  # Relevance threshold for crypto news

    # Time-based filtering
    DEFAULT_NEWS_LOOKBACK_HOURS = 6  # Default lookback period
    MAX_NEWS_LOOKBACK_HOURS = 24  # Maximum lookback period

    # Impact assessment
    HIGH_IMPACT_THRESHOLD = 0.8  # High impact threshold
    MEDIUM_IMPACT_THRESHOLD = 0.5  # Medium impact threshold
    LOW_IMPACT_THRESHOLD = 0.2  # Low impact threshold


# =============================================================================
# SOCIAL SENTIMENT CONSTANTS
# =============================================================================

class SocialSentiment:
    """Social media sentiment analysis parameters"""

    # Sentiment calculation
    SENTIMENT_MULTIPLIER_POSITIVE = 1.0  # Positive sentiment multiplier
    SENTIMENT_MULTIPLIER_NEGATIVE = -1.0  # Negative sentiment multiplier
    INFLUENCER_SENTIMENT_BOOST = 2.0  # Influencer sentiment boost multiplier

    # Volume thresholds
    HIGH_SOCIAL_VOLUME_THRESHOLD = 1000  # High volume threshold
    MEDIUM_SOCIAL_VOLUME_THRESHOLD = 100  # Medium volume threshold
    MIN_SOCIAL_VOLUME = 10  # Minimum volume for analysis

    # Platform weights
    TWITTER_PLATFORM_WEIGHT = 0.7  # Twitter weight in analysis
    REDDIT_PLATFORM_WEIGHT = 0.6  # Reddit weight in analysis

    # Engagement thresholds
    HIGH_ENGAGEMENT_THRESHOLD = 100  # High engagement threshold
    MEDIUM_ENGAGEMENT_THRESHOLD = 10  # Medium engagement threshold
    MIN_ENGAGEMENT_THRESHOLD = 1  # Minimum engagement

    # Fear & Greed Index thresholds
    EXTREME_FEAR_THRESHOLD = 25  # Extreme fear threshold
    FEAR_THRESHOLD = 45  # Fear threshold
    GREED_THRESHOLD = 55  # Greed threshold
    EXTREME_GREED_THRESHOLD = 75  # Extreme greed threshold

    # Sentiment confidence levels
    HIGH_CONFIDENCE_THRESHOLD = 0.8  # High confidence threshold
    MEDIUM_CONFIDENCE_THRESHOLD = 0.6  # Medium confidence threshold
    LOW_CONFIDENCE_THRESHOLD = 0.4  # Low confidence threshold


# =============================================================================
# SYSTEM CONFIGURATION CONSTANTS
# =============================================================================

class SystemConfig:
    """System-wide configuration constants"""

    # Logging configuration
    LOG_LEVEL = "INFO"
    MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB max log file size
    LOG_BACKUP_COUNT = 5  # Number of log backups to keep

    # Retry configuration
    MAX_RETRY_ATTEMPTS = 3  # Maximum retry attempts
    RETRY_BASE_DELAY = 1  # Base retry delay in seconds
    RETRY_MAX_DELAY = 10  # Maximum retry delay in seconds
    RETRY_MULTIPLIER = 2  # Retry delay multiplier

    # Concurrency limits
    MAX_CONCURRENT_REQUESTS = 10  # Maximum concurrent requests
    SEMAPHORE_LIMIT = 10  # Semaphore limit for async operations

    # Health check intervals
    HEALTH_CHECK_TIMEOUT = 5  # Health check timeout in seconds
    HEALTH_CHECK_INTERVAL = 60  # Health check interval in seconds

    # Metrics configuration
    MAX_HISTOGRAM_VALUES = 1000  # Maximum histogram values to keep
    METRICS_COLLECTION_INTERVAL = 30  # Metrics collection interval

    # Connection timeouts
    CONNECTION_TIMEOUT = 30  # Connection timeout
    READ_TIMEOUT = 30  # Read timeout
    WRITE_TIMEOUT = 10  # Write timeout


# =============================================================================
# CACHE CONFIGURATION CONSTANTS
# =============================================================================

class Cache:
    """Caching configuration parameters"""

    # Default TTL values (in seconds)
    DEFAULT_TTL = 300  # 5 minutes default TTL
    SHORT_TTL = 60  # 1 minute for high-frequency data
    MEDIUM_TTL = 300  # 5 minutes for medium frequency data
    LONG_TTL = 3600  # 1 hour for low frequency data

    # Specific cache TTLs
    PRICE_DATA_TTL = 60  # Price data cache TTL
    NEWS_DATA_TTL = 300  # News data cache TTL
    SOCIAL_DATA_TTL = 180  # Social data cache TTL (3 minutes)
    TECHNICAL_DATA_TTL = 300  # Technical analysis cache TTL
    ACCOUNT_DATA_TTL = 60  # Account data cache TTL

    # Cache size limits
    MAX_CACHE_SIZE = 10000  # Maximum cache entries
    CACHE_CLEANUP_THRESHOLD = 8000  # Cleanup threshold


# =============================================================================
# VALIDATION THRESHOLDS
# =============================================================================

class Validation:
    """Data validation thresholds and limits"""

    # Symbol validation
    MIN_SYMBOL_LENGTH = 6  # Minimum symbol length (e.g., BTCUSDT)
    VALID_QUOTE_CURRENCIES = ["USDT", "BUSD", "USD", "EUR"]  # Valid quote currencies

    # Price validation
    MIN_PRICE = 0.00000001  # Minimum valid price (1 satoshi equivalent)
    MAX_PRICE = 1000000.0  # Maximum reasonable price

    # Quantity validation
    MIN_QUANTITY = 0.00000001  # Minimum valid quantity
    MAX_QUANTITY = 1000000.0  # Maximum reasonable quantity

    # Percentage validation
    MIN_PERCENTAGE = -100.0  # Minimum percentage change
    MAX_PERCENTAGE = 1000.0  # Maximum percentage change

    # Time validation
    MAX_TIMESTAMP_DIFF = 86400  # Max timestamp difference (1 day)
    MIN_TIMESTAMP = 1000000000  # Minimum valid timestamp (year 2001)


# =============================================================================
# SECURITY AND SSL CONSTANTS
# =============================================================================

class Security:
    """Security and SSL configuration"""

    # SSL configuration
    MIN_TLS_VERSION = "TLSv1_2"  # Minimum TLS version
    SSL_VERIFY_DEFAULT = True  # Default SSL verification

    # API key security
    MIN_API_KEY_LENGTH = 32  # Minimum API key length
    API_KEY_ENTROPY_THRESHOLD = 4.0  # Minimum entropy for API keys

    # Rate limiting for security
    MAX_REQUESTS_PER_MINUTE = 1000  # Maximum requests per minute per IP
    SECURITY_BREACH_THRESHOLD = 10  # Failed auth attempts threshold

    # Data encryption
    HASH_ALGORITHM = "SHA256"  # Default hash algorithm
    HMAC_ALGORITHM = "SHA256"  # HMAC algorithm


# =============================================================================
# UTILITY CONSTANTS
# =============================================================================

class Utils:
    """Utility constants and common values"""

    # Decimal precision
    DECIMAL_PLACES = 8  # Default decimal places for calculations
    PERCENTAGE_DECIMAL_PLACES = 2  # Decimal places for percentages
    CURRENCY_DECIMAL_PLACES = 2  # Decimal places for currency display

    # Time constants
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = 86400
    MILLISECONDS_PER_SECOND = 1000

    # Data size constants
    BYTES_PER_KB = 1024
    BYTES_PER_MB = 1024 * 1024
    BYTES_PER_GB = 1024 * 1024 * 1024


# =============================================================================
# EXPORT CONSTANT GROUPS
# =============================================================================

# Export all constant classes for easy importing
__all__ = [
    'RiskManagement',
    'ApiRateLimits',
    'TechnicalAnalysis',
    'Trading',
    'NewsSentiment',
    'SocialSentiment',
    'SystemConfig',
    'Cache',
    'Validation',
    'Security',
    'Utils'
]

# Convenience dictionary for accessing all constants
ALL_CONSTANTS = {
    'RISK_MANAGEMENT': RiskManagement,
    'API_RATE_LIMITS': ApiRateLimits,
    'TECHNICAL_ANALYSIS': TechnicalAnalysis,
    'TRADING': Trading,
    'NEWS_SENTIMENT': NewsSentiment,
    'SOCIAL_SENTIMENT': SocialSentiment,
    'SYSTEM_CONFIG': SystemConfig,
    'CACHE': Cache,
    'VALIDATION': Validation,
    'SECURITY': Security,
    'UTILS': Utils
}
