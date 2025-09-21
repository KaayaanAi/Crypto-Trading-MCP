"""
Shared type definitions for the Crypto Trading MCP System
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TradingMode(str, Enum):
    SWING = "swing"
    INTRADAY = "intraday"
    SCALP = "scalp"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LIMIT = "stop_limit"


class SignalAction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class DataSourceType(str, Enum):
    NEWS = "news"
    TECHNICAL = "technical"
    SOCIAL = "social"
    MARKET = "market"
    AI = "ai"
    RISK = "risk"


class Timeframe(str, Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


# Error Models
class ErrorDetail(BaseModel):
    """Standardized error detail structure"""
    code: str
    message: str
    severity: str  # "low", "medium", "high", "critical"
    category: str  # "validation", "authentication", "network", etc.
    details: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Base Models
class BaseResponse(BaseModel):
    success: bool = True
    error: Optional[ErrorDetail] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def create_error(cls, error_detail: ErrorDetail):
        """Create an error response"""
        return cls(
            success=False,
            error=error_detail
        )

    @classmethod
    def create_success(cls, **kwargs):
        """Create a success response with additional fields"""
        return cls(success=True, **kwargs)


# News Data Models
class NewsItem(BaseModel):
    title: str
    description: str
    url: str
    published_at: datetime
    source: str
    sentiment_score: Optional[float] = None


class NewsAnalysis(BaseResponse):
    news_items: List[NewsItem] = []
    overall_sentiment: float = Field(0.0, ge=-1, le=1)
    confidence: float = Field(0.0, ge=0, le=1)
    impact_level: str = "low"  # "high", "medium", "low"
    key_topics: List[str] = []


# Technical Analysis Models
class TechnicalIndicator(BaseModel):
    name: str
    value: float
    signal: str  # "bullish", "bearish", "neutral"
    confidence: float = Field(..., ge=0, le=1)


class SupportResistanceLevel(BaseModel):
    level: float
    type: str  # "support", "resistance"
    strength: float = Field(..., ge=0, le=1)
    touches: int


class ChartPattern(BaseModel):
    name: str  # "head_shoulders", "triangle", "flag", etc.
    confidence: float = Field(..., ge=0, le=1)
    direction: str  # "bullish", "bearish", "neutral"
    target_price: Optional[float] = None


class TechnicalAnalysis(BaseResponse):
    symbol: str = ""
    timeframe: Timeframe = Timeframe.ONE_HOUR
    indicators: List[TechnicalIndicator] = []
    patterns: List[ChartPattern] = []
    support_levels: List[SupportResistanceLevel] = []
    resistance_levels: List[SupportResistanceLevel] = []
    overall_signal: str = "neutral"  # "bullish", "bearish", "neutral"
    confidence: float = Field(0.0, ge=0, le=1)


# Social Sentiment Models
class SocialMetric(BaseModel):
    platform: str  # "twitter", "reddit", "telegram"
    sentiment_score: float = Field(..., ge=-1, le=1)
    volume: int  # number of mentions/posts
    confidence: float = Field(..., ge=0, le=1)
    trending_topics: List[str]


class SocialAnalysis(BaseResponse):
    metrics: List[SocialMetric] = []
    fear_greed_index: Optional[float] = Field(None, ge=0, le=100)
    overall_sentiment: float = Field(0.0, ge=-1, le=1)
    confidence: float = Field(0.0, ge=0, le=1)


# Market Data Models
class PriceData(BaseModel):
    symbol: str
    price: float
    volume: float
    change_24h: float
    timestamp: datetime


class OrderbookLevel(BaseModel):
    price: float
    quantity: float


class Orderbook(BaseModel):
    symbol: str
    bids: List[OrderbookLevel]
    asks: List[OrderbookLevel]
    timestamp: datetime


class MarketData(BaseResponse):
    symbol: str = ""
    price_data: Optional[PriceData] = None
    orderbook: Optional[Orderbook] = None
    whale_movements: List[Dict[str, Any]] = []


# Risk Management Models
class PositionSize(BaseModel):
    symbol: str
    quantity: float
    notional_value: float
    risk_amount: float
    confidence: float = Field(..., ge=0, le=1)


class RiskMetrics(BaseModel):
    var_1d: float  # 1-day Value at Risk
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    portfolio_beta: Optional[float] = None
    correlation_risk: str  # "high", "medium", "low"


class RiskAlert(BaseModel):
    level: str  # "warning", "critical"
    message: str
    metric: str
    current_value: float
    threshold: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RiskAnalysis(BaseResponse):
    portfolio_metrics: Optional[RiskMetrics] = None
    position_sizing: Optional[PositionSize] = None
    alerts: List[RiskAlert] = []
    recommendations: List[str] = []


# AI Analysis Models
class AIInsight(BaseModel):
    analysis_type: str  # "sentiment", "technical", "fundamental"
    insight: str
    confidence: float = Field(..., ge=0, le=1)
    weight: float = Field(..., ge=0, le=1)


class AIAnalysis(BaseResponse):
    model_used: str = ""
    insights: List[AIInsight] = []
    prediction: Dict[str, Any] = {}
    confidence: float = Field(0.0, ge=0, le=1)
    reasoning: str = ""


# Trading Models
class TradingSignal(BaseModel):
    symbol: str
    action: SignalAction
    confidence: float = Field(..., ge=0, le=1)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    reasoning: str
    data_sources: List[DataSourceType]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"  # Good Till Cancelled


class OrderResponse(BaseResponse):
    order_id: Optional[str] = None
    symbol: str = ""
    side: Optional[OrderSide] = None
    quantity: float = 0.0
    price: Optional[float] = None
    status: str = "UNKNOWN"
    fill_quantity: float = 0.0
    average_price: Optional[float] = None


class Position(BaseModel):
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    side: str  # "long", "short"
    timestamp: datetime


class AccountInfo(BaseModel):
    total_balance: float
    available_balance: float
    positions: List[Position]
    open_orders: List[Dict[str, Any]]
    total_pnl: float
    daily_pnl: float


# Comprehensive Analysis Models
class MarketAnalysis(BaseModel):
    symbol: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Individual analysis results
    news_analysis: Optional[NewsAnalysis] = None
    technical_analysis: Optional[TechnicalAnalysis] = None
    social_analysis: Optional[SocialAnalysis] = None
    ai_analysis: Optional[AIAnalysis] = None
    risk_analysis: Optional[RiskAnalysis] = None

    # Combined results
    overall_signal: SignalAction = SignalAction.HOLD
    confidence: float = Field(0.0, ge=0, le=1)
    reasoning: str = ""

    # Calculated scores
    technical_score: float = Field(0.0, ge=-1, le=1)
    fundamental_score: float = Field(0.0, ge=-1, le=1)
    sentiment_score: float = Field(0.0, ge=-1, le=1)
    risk_score: float = Field(0.0, ge=0, le=1)


class TradingDecision(BaseModel):
    analysis: MarketAnalysis
    signal: TradingSignal
    risk_assessment: RiskAnalysis
    execution_plan: Dict[str, Any]


# MCP Communication Models
class MCPRequest(BaseModel):
    method: str
    params: Dict[str, Any] = {}
    id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))


class MCPResponse(BaseModel):
    id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPServerInfo(BaseModel):
    name: str
    version: str
    status: str  # "running", "stopped", "error"
    last_ping: Optional[datetime] = None
    tools: List[str] = []


# System Status Models
class SystemHealth(BaseModel):
    overall_status: str  # "healthy", "degraded", "unhealthy"
    mcp_servers: Dict[str, MCPServerInfo]
    last_trade: Optional[datetime] = None
    active_positions: int
    daily_pnl: float
    system_uptime: float  # seconds
    errors: List[str] = []


# Configuration Models
class TradingConfig(BaseModel):
    symbol: str = "BTCUSDT"
    mode: TradingMode = TradingMode.SWING
    risk_per_trade: float = Field(0.02, ge=0.001, le=0.1)
    max_positions: int = Field(3, ge=1, le=10)
    min_confidence: float = Field(0.7, ge=0.5, le=1.0)


class RiskConfig(BaseModel):
    stop_loss_percent: float = Field(0.05, ge=0.01, le=0.2)
    take_profit_ratio: float = Field(2.0, ge=1.0, le=10.0)
    max_drawdown: float = Field(0.15, ge=0.05, le=0.5)
    daily_loss_limit: float = Field(0.10, ge=0.02, le=0.3)


# Utility Functions
def create_error_response(
    code: str,
    message: str,
    severity: str = "medium",
    category: str = "general",
    details: Optional[Dict[str, Any]] = None
) -> BaseResponse:
    """Create a standardized error response"""
    error_detail = ErrorDetail(
        code=code,
        message=message,
        severity=severity,
        category=category,
        details=details or {}
    )
    return BaseResponse.create_error(error_detail)


def create_success_response(**kwargs) -> BaseResponse:
    """Create a standardized success response"""
    return BaseResponse.create_success(**kwargs)


def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format"""
    return len(symbol) >= 6 and symbol.isupper() and symbol.endswith('USDT')


def calculate_risk_reward(entry_price: float, stop_loss: float, take_profit: float) -> float:
    """Calculate risk-reward ratio"""
    risk = abs(entry_price - stop_loss)
    reward = abs(take_profit - entry_price)
    return reward / risk if risk > 0 else 0.0
