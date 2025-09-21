# Crypto Trading MCP System

An advanced modular crypto trading system built on the Model Context Protocol (MCP) architecture. This system orchestrates multiple specialized MCP servers for comprehensive market analysis and automated trading.

## 🆕 Recent Updates (v1.1.0)

✅ **Security Fixed**: Complete SSL/TLS security implementation - all certificate bypass vulnerabilities resolved
✅ **HTTP Bridge Added**: n8n integration support with RESTful API endpoints
✅ **Error Handling**: Comprehensive error handling and runtime protection
✅ **Code Quality**: Standardized formatting, linting, and type safety
✅ **Dependencies**: All packages updated to latest stable versions

👨 **Ready for production deployment with enterprise-grade security!**

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 Main Trading Client                         │
│                (crypto_trader.py)                          │
└─────────────────┬───────────────────────────────────────────┘
                  │ Orchestrates all MCP servers
                  │
┌─────────────────┼─────────────────┐ 🆕 HTTP Bridge (n8n)
│                 │                 │ ┌─────────────────────┐
│    ┌─────────────┼─────────────┐   │ │   HTTP Bridge       │
│    │             │             │   │ │  (port 8080)        │
│    ▼             ▼             ▼   │ │ REST API + WebSocket│
│┌─────────┐  ┌─────────┐  ┌─────────┐ │ └─────────────────────┘
││ News    │  │Technical│  │ Social  │ │           │
││ MCP     │  │ MCP     │  │ MCP     │ │           ▼
││ Server  │  │ Server  │  │ Server  │ │    ┌─────────────┐
│└─────────┘  └─────────┘  └─────────┘ │    │    n8n      │
│    │             │             │     │    │ Workflows   │
│    ▼             ▼             ▼     │    └─────────────┘
│┌─────────┐  ┌─────────┐  ┌─────────┐ │
││Binance  │  │ Risk    │  │   AI    │ │
││ MCP     │  │ MCP     │  │  MCP    │ │
││ Server  │  │ Server  │  │ Server  │ │
│└─────────┘  └─────────┘  └─────────┘ │
└─────────────────────────────────────┘
```

## 🚀 Components

### 6 Specialized MCP Servers:

1. **crypto-news-mcp**: RSS feeds, news sentiment analysis
2. **crypto-technical-mcp**: Technical indicators, chart patterns, S/R levels
3. **crypto-social-mcp**: Twitter/Reddit sentiment, Fear & Greed index
4. **binance-mcp**: Market data, order execution, account management
5. **crypto-risk-mcp**: Position sizing, portfolio risk, alerts
6. **crypto-ai-mcp**: Ollama LLM integration for market analysis

### Main Trading Client:
- **crypto_trader.py**: Orchestrates all MCP servers
- **mcp_manager.py**: Manages MCP connections
- **config.yaml**: Trading parameters and settings

### 🆕 HTTP Bridge (NEW in v1.1.0):
- **http-bridge/server.js**: Express.js server with WebSocket support
- **RESTful API**: All MCP functionality via HTTP endpoints
- **n8n Integration**: Direct workflow integration support
- **Security**: Rate limiting, CORS, helmet protection
- **Health Checks**: Monitoring and status endpoints

## 🛠️ Installation

### Prerequisites
```bash
# Python 3.9+
python3 --version

# Install Ollama for local AI analysis
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama2  # or your preferred model
```

### Quick Start
```bash
# Clone and install
git clone <repository-url>
cd crypto-trading-mcp-system
pip install -r requirements.txt

# Configure your API keys
cp .env.example .env
# Edit .env with your Binance API keys

# Start individual MCP servers
python servers/crypto-news-mcp/main.py &
python servers/crypto-technical-mcp/main.py &
python servers/crypto-social-mcp/main.py &
python servers/binance-mcp/main.py &
python servers/crypto-risk-mcp/main.py &
python servers/crypto-ai-mcp/main.py &

# Run main trading client
python client/crypto_trader.py
```

### Docker Deployment

#### Traditional MCP Deployment
```bash
# Native MCP protocol deployment
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f crypto-trader
```

#### 🆕 HTTP Bridge Deployment (for n8n)
```bash
# HTTP bridge deployment for n8n integration
docker-compose -f docker-compose.http.yml up -d

# Check HTTP bridge status
curl http://localhost:8080/health

# Access API documentation
curl http://localhost:8080/api/docs

# Test MCP server connection
curl http://localhost:8080/api/servers/status
```

## ⚙️ Configuration

### Environment Variables
```bash
# Binance API
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key

# 🆕 Security Settings (v1.1.0)
DISABLE_SSL_VERIFICATION=false  # Production: false, Dev: true for local testing

# HTTP Bridge (when using n8n deployment)
HTTP_BRIDGE_PORT=8080
HTTP_BRIDGE_HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5678  # n8n default port
BINANCE_TESTNET=true  # Set to false for live trading

# Trading Parameters
DEFAULT_SYMBOL=BTCUSDT
RISK_PER_TRADE=0.02  # 2% risk per trade
MIN_CONFIDENCE=0.7   # Minimum signal confidence to trade

# AI Models
OLLAMA_MODEL=llama2
OLLAMA_HOST=http://localhost:11434

# Data Sources
TWITTER_BEARER_TOKEN=your_twitter_token (optional)
REDDIT_CLIENT_ID=your_reddit_id (optional)
```

### Trading Configuration (config.yaml)
```yaml
trading:
  symbol: "BTCUSDT"
  mode: "swing"  # swing | intraday | scalp
  risk_per_trade: 0.02
  max_positions: 3

analysis:
  confidence_threshold: 0.7
  lookback_periods: 20
  indicators: ["RSI", "MACD", "EMA", "BB"]

risk_management:
  stop_loss_percent: 0.05
  take_profit_ratio: 2.0  # Risk:Reward = 1:2
  max_drawdown: 0.15
```

## 🔒 Security Features (v1.1.0)

### Enterprise-Grade Security
- **SSL/TLS Security**: Complete certificate validation, TLS 1.2+ enforcement
- **Environment-Based Controls**: Secure production, flexible development
- **Container Security**: Non-root execution, package version pinning
- **Secret Management**: No hardcoded credentials, comprehensive .env templates
- **API Security**: Rate limiting, CORS protection, helmet middleware
- **Input Validation**: Comprehensive parameter validation and sanitization

### Production Deployment Checklist
- [ ] Set `DISABLE_SSL_VERIFICATION=false` (or remove completely)
- [ ] Use real Binance API keys (not testnet)
- [ ] Configure proper CORS origins for HTTP bridge
- [ ] Set up monitoring and alerting
- [ ] Review and test all error handling paths
- [ ] Enable comprehensive logging

## 🔧 MCP Server Details

### News MCP Server
- **RSS Feed Analysis**: CoinDesk, CoinTelegraph, Decrypt
- **Sentiment Scoring**: Keyword-based + AI analysis
- **Event Detection**: Regulatory news, adoption events

### Technical MCP Server
- **Indicators**: RSI, MACD, EMA, Bollinger Bands, VWAP
- **Pattern Detection**: Head & Shoulders, Triangles, Flags
- **Support/Resistance**: Dynamic level identification

### Social MCP Server
- **Twitter Sentiment**: Crypto-related tweets analysis
- **Reddit Analysis**: r/cryptocurrency, r/bitcoin discussions
- **Fear & Greed Index**: Market sentiment gauge

### Binance MCP Server
- **Market Data**: Real-time prices, orderbook, trades
- **Account Management**: Balances, positions, history
- **Order Execution**: Market, limit, stop-loss orders
- **Whale Tracking**: Large transaction monitoring

### Risk MCP Server
- **Position Sizing**: Kelly Criterion, fixed percentage
- **Portfolio Risk**: VaR, correlation analysis, drawdown
- **Alert System**: Risk threshold notifications

### AI MCP Server
- **Ollama Integration**: Local LLM for market analysis
- **Pattern Recognition**: AI-powered chart analysis
- **Signal Generation**: Multi-factor decision making

## 📊 Usage Examples

### Basic Trading Cycle
```python
# The main client automatically:
1. Gathers data from all MCP servers
2. Analyzes with AI models
3. Calculates position sizes
4. Executes trades based on signals
5. Monitors positions continuously
```

### Manual Tool Usage
```bash
# Test individual MCP servers
echo '{"method": "fetch_crypto_news", "params": {"timeframe": "6h"}}' | python servers/crypto-news-mcp/main.py

# Check technical indicators
echo '{"method": "calculate_indicators", "params": {"symbol": "BTCUSDT"}}' | python servers/crypto-technical-mcp/main.py
```

## 🧪 Testing

### Unit Tests
```bash
# Test individual servers
pytest tests/test_news_server.py
pytest tests/test_technical_server.py

# Test full system
pytest tests/test_integration.py
```

### Paper Trading
```bash
# Enable paper trading mode
export BINANCE_TESTNET=true
python client/crypto_trader.py --paper-trading
```

## 📈 Performance Monitoring

### Metrics Dashboard
- **Trading Performance**: Win rate, profit/loss, Sharpe ratio
- **Signal Quality**: Confidence scores, accuracy tracking
- **System Health**: MCP server status, latency monitoring
- **Risk Metrics**: Current exposure, VaR, drawdown

### Logging
```bash
# View real-time logs
tail -f logs/crypto_trader.log

# Check specific server logs
tail -f logs/news_server.log
tail -f logs/technical_server.log
```

## 🔐 Security

### API Key Management
- Environment variables only, never in code
- Separate testnet/mainnet configurations
- Read-only keys for data servers

### Risk Controls
- Position size limits
- Daily loss limits
- Emergency stop functionality
- Manual override capabilities

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test thoroughly
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational purposes only. Cryptocurrency trading carries substantial risk of loss. Past performance does not guarantee future results. Use at your own risk and never trade with money you cannot afford to lose.

## 🆘 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Open an issue on GitHub
- **Discussions**: Join our community discussions

---

**Built with ❤️ using the Model Context Protocol (MCP)**