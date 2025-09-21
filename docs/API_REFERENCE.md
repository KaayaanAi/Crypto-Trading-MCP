# API Reference - Crypto Trading MCP System

## Overview

The Crypto Trading MCP System provides two ways to interact with the MCP servers:

1. **Native MCP Protocol**: Direct WebSocket connections using MCP protocol
2. **HTTP Bridge API**: RESTful HTTP endpoints for integration with tools like n8n

## HTTP Bridge API (v1.1.0)

### Base URL
```
http://localhost:8080/api
```

### Authentication
All API endpoints require no authentication for local deployment. For production, implement proper API key authentication.

### Common Response Format
```json
{
  "success": true,
  "data": {...},
  "error": null,
  "timestamp": "2025-09-21T15:30:00Z"
}
```

### Error Response Format
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {...}
  },
  "timestamp": "2025-09-21T15:30:00Z"
}
```

---

## System Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-21T15:30:00Z",
  "uptime": 3600,
  "version": "1.1.0"
}
```

### Server Status
```http
GET /api/servers/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "crypto-news-mcp": {
      "status": "connected",
      "last_ping": "2025-09-21T15:29:45Z",
      "version": "1.1.0"
    },
    "crypto-technical-mcp": {
      "status": "connected",
      "last_ping": "2025-09-21T15:29:45Z",
      "version": "1.1.0"
    }
  }
}
```

---

## News MCP Server API

### Get Latest News
```http
GET /api/news/latest?limit=10&source=all
```

**Parameters:**
- `limit` (optional): Number of articles (default: 10, max: 50)
- `source` (optional): News source filter (`coindesk`, `cointelegraph`, `decrypt`, `all`)

**Response:**
```json
{
  "success": true,
  "data": {
    "articles": [
      {
        "title": "Bitcoin Reaches New All-Time High",
        "summary": "Bitcoin price surged to $75,000...",
        "url": "https://example.com/article",
        "published_at": "2025-09-21T14:30:00Z",
        "source": "coindesk",
        "sentiment": {
          "score": 0.8,
          "label": "bullish"
        },
        "tags": ["bitcoin", "price", "ath"]
      }
    ],
    "total_count": 25,
    "sentiment_summary": {
      "average_score": 0.6,
      "bullish_count": 15,
      "bearish_count": 5,
      "neutral_count": 5
    }
  }
}
```

### Analyze News Sentiment
```http
POST /api/news/analyze
```

**Request Body:**
```json
{
  "text": "Bitcoin price is showing strong bullish momentum",
  "symbol": "BTCUSDT"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "sentiment": {
      "score": 0.85,
      "label": "bullish",
      "confidence": 0.92
    },
    "keywords": ["bitcoin", "bullish", "momentum"],
    "impact_score": 0.7
  }
}
```

---

## Technical Analysis MCP Server API

### Get Technical Indicators
```http
GET /api/technical/indicators?symbol=BTCUSDT&timeframe=1h&indicators=RSI,MACD,EMA
```

**Parameters:**
- `symbol` (required): Trading pair symbol
- `timeframe` (required): Timeframe (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`)
- `indicators` (required): Comma-separated list of indicators

**Available Indicators:**
- `RSI`: Relative Strength Index
- `MACD`: Moving Average Convergence Divergence
- `EMA`: Exponential Moving Average
- `SMA`: Simple Moving Average
- `BB`: Bollinger Bands
- `VWAP`: Volume Weighted Average Price
- `STOCH`: Stochastic Oscillator

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "timestamp": "2025-09-21T15:00:00Z",
    "indicators": {
      "RSI": {
        "value": 65.2,
        "signal": "neutral",
        "overbought": false,
        "oversold": false
      },
      "MACD": {
        "macd": 1250.5,
        "signal": 1180.2,
        "histogram": 70.3,
        "trend": "bullish"
      },
      "EMA": {
        "ema_12": 67850.5,
        "ema_26": 67200.1,
        "signal": "bullish"
      }
    }
  }
}
```

### Detect Chart Patterns
```http
GET /api/technical/patterns?symbol=BTCUSDT&timeframe=4h
```

**Response:**
```json
{
  "success": true,
  "data": {
    "patterns": [
      {
        "type": "ascending_triangle",
        "confidence": 0.85,
        "timeframe": "4h",
        "formation_period": "2025-09-18T00:00:00Z - 2025-09-21T12:00:00Z",
        "breakout_target": 72000,
        "support_level": 65000,
        "resistance_level": 70000
      }
    ]
  }
}
```

### Get Support/Resistance Levels
```http
GET /api/technical/levels?symbol=BTCUSDT&timeframe=1d
```

**Response:**
```json
{
  "success": true,
  "data": {
    "support_levels": [
      {
        "price": 65000,
        "strength": 0.9,
        "touches": 5,
        "last_touch": "2025-09-20T08:00:00Z"
      }
    ],
    "resistance_levels": [
      {
        "price": 72000,
        "strength": 0.85,
        "touches": 3,
        "last_touch": "2025-09-21T14:00:00Z"
      }
    ]
  }
}
```

---

## Social Sentiment MCP Server API

### Get Social Sentiment
```http
GET /api/social/sentiment?symbol=BTCUSDT&timeframe=24h
```

**Parameters:**
- `symbol` (required): Trading pair symbol
- `timeframe` (optional): Time period (`1h`, `4h`, `24h`, `7d`)

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "BTCUSDT",
    "timeframe": "24h",
    "overall_sentiment": {
      "score": 0.72,
      "label": "bullish",
      "confidence": 0.88
    },
    "sources": {
      "twitter": {
        "sentiment": 0.75,
        "mentions": 1250,
        "engagement": 45000
      },
      "reddit": {
        "sentiment": 0.68,
        "posts": 89,
        "upvotes": 2340
      }
    },
    "fear_greed_index": {
      "value": 72,
      "label": "greed",
      "change_24h": 5
    }
  }
}
```

### Get Trending Topics
```http
GET /api/social/trending?limit=10
```

**Response:**
```json
{
  "success": true,
  "data": {
    "trending_topics": [
      {
        "keyword": "bitcoin",
        "mentions": 5240,
        "sentiment": 0.78,
        "change_24h": 15.2
      },
      {
        "keyword": "ethereum",
        "mentions": 3890,
        "sentiment": 0.65,
        "change_24h": -5.1
      }
    ]
  }
}
```

---

## Binance MCP Server API

### Get Market Data
```http
GET /api/binance/market?symbol=BTCUSDT
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "BTCUSDT",
    "price": 68750.50,
    "change_24h": 2.5,
    "volume_24h": 15240000,
    "high_24h": 69500.00,
    "low_24h": 67200.00,
    "bid": 68745.00,
    "ask": 68755.00,
    "timestamp": "2025-09-21T15:30:00Z"
  }
}
```

### Get Order Book
```http
GET /api/binance/orderbook?symbol=BTCUSDT&limit=20
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "BTCUSDT",
    "bids": [
      ["68745.00", "0.15420"],
      ["68740.00", "0.28950"]
    ],
    "asks": [
      ["68755.00", "0.12340"],
      ["68760.00", "0.34210"]
    ],
    "timestamp": "2025-09-21T15:30:00Z"
  }
}
```

### Place Order (requires authentication in production)
```http
POST /api/binance/order
```

**Request Body:**
```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "LIMIT",
  "quantity": "0.001",
  "price": "68000.00",
  "timeInForce": "GTC"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "orderId": 12345678,
    "symbol": "BTCUSDT",
    "status": "NEW",
    "clientOrderId": "client_order_123",
    "transactTime": "2025-09-21T15:30:00Z"
  }
}
```

---

## Risk Management MCP Server API

### Calculate Position Size
```http
POST /api/risk/position-size
```

**Request Body:**
```json
{
  "account_balance": 10000,
  "risk_per_trade": 0.02,
  "entry_price": 68000,
  "stop_loss": 66000,
  "symbol": "BTCUSDT"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "position_size": 0.098,
    "risk_amount": 200.00,
    "risk_percentage": 2.0,
    "stop_loss_distance": 2000,
    "position_value": 6664.00
  }
}
```

### Get Risk Assessment
```http
GET /api/risk/assessment?symbol=BTCUSDT
```

**Response:**
```json
{
  "success": true,
  "data": {
    "risk_level": "medium",
    "risk_score": 0.6,
    "volatility": {
      "daily": 0.045,
      "weekly": 0.078
    },
    "max_position_size": 0.15,
    "recommended_stop_loss": 0.03,
    "risk_factors": [
      "High volatility in 24h",
      "Strong resistance at 70k"
    ]
  }
}
```

---

## AI Analysis MCP Server API

### Get Market Analysis
```http
POST /api/ai/analyze
```

**Request Body:**
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1d",
  "analysis_type": "comprehensive",
  "include_sentiment": true,
  "include_technical": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "BTCUSDT",
    "analysis": {
      "summary": "Based on current market conditions...",
      "direction": "bullish",
      "confidence": 0.78,
      "timeframe": "short_term",
      "key_factors": [
        "Strong technical momentum",
        "Positive sentiment shift",
        "Breaking resistance levels"
      ]
    },
    "recommendations": {
      "action": "BUY",
      "entry_zone": "67500-68500",
      "stop_loss": "65000",
      "take_profit": ["72000", "75000"],
      "risk_reward_ratio": 2.1
    }
  }
}
```

---

## WebSocket API

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');
```

### Subscribe to Price Updates
```json
{
  "action": "subscribe",
  "channel": "price",
  "symbol": "BTCUSDT"
}
```

### Subscribe to News Updates
```json
{
  "action": "subscribe",
  "channel": "news",
  "filters": {
    "sources": ["coindesk", "cointelegraph"],
    "sentiment_threshold": 0.5
  }
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_SYMBOL` | Trading pair symbol not found |
| `INVALID_TIMEFRAME` | Unsupported timeframe |
| `INSUFFICIENT_DATA` | Not enough historical data |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INVALID_PARAMETERS` | Missing or invalid parameters |
| `SERVER_UNAVAILABLE` | MCP server connection failed |
| `CALCULATION_ERROR` | Error in mathematical calculations |
| `API_ERROR` | External API error (Binance, etc.) |

---

## Rate Limits

- **General API**: 100 requests per minute per IP
- **Market Data**: 300 requests per minute per IP
- **Order Placement**: 10 requests per minute per IP
- **WebSocket**: 50 connections per IP

---

## SDK Examples

### Python
```python
import requests

# Get latest news
response = requests.get('http://localhost:8080/api/news/latest')
news = response.json()

# Get technical indicators
indicators = requests.get(
    'http://localhost:8080/api/technical/indicators',
    params={
        'symbol': 'BTCUSDT',
        'timeframe': '1h',
        'indicators': 'RSI,MACD'
    }
)
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

// Get market data
const marketData = await axios.get('http://localhost:8080/api/binance/market', {
  params: { symbol: 'BTCUSDT' }
});

// Calculate position size
const positionSize = await axios.post('http://localhost:8080/api/risk/position-size', {
  account_balance: 10000,
  risk_per_trade: 0.02,
  entry_price: 68000,
  stop_loss: 66000,
  symbol: 'BTCUSDT'
});
```

---

## Support

For API support and questions:
- GitHub Issues: [Report Issues](https://github.com/your-org/crypto-trading-mcp/issues)
- Documentation: [Full Documentation](https://github.com/your-org/crypto-trading-mcp/docs)
- Changelog: [Version History](../CHANGELOG.md)