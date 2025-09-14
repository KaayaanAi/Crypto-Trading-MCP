# 🚀 Quick Start Guide

Get your Crypto Trading MCP System up and running in minutes!

## 📋 Prerequisites

### Required
- **Python 3.9+** - [Download here](https://python.org)
- **Git** - For cloning the repository

### Recommended
- **Docker & Docker Compose** - For containerized deployment
- **Ollama** - For AI-powered analysis ([Install here](https://ollama.com/download))

## ⚡ Quick Setup (5 minutes)

### 1. Clone and Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd crypto-trading-mcp-system

# Make startup script executable
chmod +x scripts/start.sh

# Quick start with default settings
./scripts/start.sh development
```

### 2. Configure Your API Keys
```bash
# Copy environment template
cp .env.example .env

# Edit with your keys (minimum required for paper trading)
nano .env
```

**Essential settings:**
```bash
# Binance API (use testnet for safety)
BINANCE_API_KEY=your_testnet_api_key
BINANCE_SECRET_KEY=your_testnet_secret_key
BINANCE_TESTNET=true

# Keep paper trading ON for safety
ENABLE_PAPER_TRADING=true
```

### 3. Start Trading System
```bash
# Development mode (recommended for first time)
./scripts/start.sh development

# Or Docker mode (all-in-one)
./scripts/start.sh docker
```

## 🎯 What Happens Next

Once started, the system will:

1. **Connect to 6 MCP Servers**:
   - 📰 News Analysis Server (RSS feeds + sentiment)
   - 📊 Technical Analysis Server (RSI, MACD, patterns)
   - 🐦 Social Sentiment Server (Twitter, Reddit, Fear/Greed)
   - 💱 Binance Exchange Server (market data, orders)
   - ⚠️ Risk Management Server (position sizing, alerts)
   - 🤖 AI Analysis Server (Ollama integration)

2. **Begin Analysis Cycles** (every 5 minutes):
   - Gather data from all sources
   - AI synthesis of market conditions
   - Generate trading signals
   - Execute trades (paper mode by default)

3. **Monitor & Log Everything**:
   - All activities logged to `logs/crypto_trader.log`
   - Metrics collected for performance monitoring
   - Health checks for all components

## 📊 Monitoring Your System

### Check System Status
```bash
./scripts/start.sh status
```

### View Live Logs
```bash
# Main system logs
tail -f logs/crypto_trader.log

# Individual server logs
tail -f logs/news_server.log
tail -f logs/technical_server.log
# ... etc
```

### Docker Monitoring (if using Docker)
```bash
# All services status
docker-compose ps

# Live logs from all services
docker-compose logs -f

# Specific service logs
docker-compose logs -f crypto-trader
```

## 🛡️ Safety First

### Paper Trading Mode (Default)
- **All trades are simulated** - no real money at risk
- Full system functionality without financial exposure
- Perfect for testing and learning

### Testnet Mode (Recommended)
- Uses Binance testnet with fake money
- Real API integration without risk
- Test your strategies safely

### Production Checklist
Before going live with real money:

1. ✅ Tested extensively in paper mode
2. ✅ Verified all API connections work
3. ✅ Understood risk management settings
4. ✅ Set appropriate position sizes
5. ✅ Emergency stop procedures tested
6. ✅ Monitoring and alerts configured

## 🔧 Configuration Customization

### Basic Trading Settings
Edit `client/config.yaml`:

```yaml
trading:
  symbol: "BTCUSDT"           # Trading pair
  risk_per_trade: 0.02        # 2% risk per trade
  min_confidence: 0.7         # 70% minimum signal confidence
  max_positions: 3            # Maximum concurrent positions

risk_management:
  stop_loss_percent: 0.05     # 5% stop loss
  take_profit_ratio: 2.0      # 1:2 risk/reward ratio
  max_drawdown: 0.15          # 15% maximum portfolio drawdown
```

### AI Configuration
```yaml
# In .env file
OLLAMA_MODEL=llama2           # AI model to use
OLLAMA_HOST=http://localhost:11434
AI_ANALYSIS_ENABLED=true
```

## 📈 Deployment Options

### 1. Development Mode (Local)
```bash
./scripts/start.sh development
```
- **Best for**: Development, testing, learning
- **Resources**: Low (runs on your machine)
- **Setup time**: 2 minutes

### 2. Docker Basic
```bash
./scripts/start.sh docker
```
- **Best for**: Production, easy deployment
- **Resources**: Medium (isolated containers)
- **Setup time**: 5 minutes

### 3. Docker Full Stack
```bash
./scripts/start.sh docker-full
```
- **Best for**: Enterprise, monitoring, analytics
- **Resources**: High (includes Grafana, Prometheus, MongoDB)
- **Setup time**: 10 minutes
- **Includes**:
  - 📊 Grafana dashboards (localhost:3000)
  - 📈 Prometheus metrics (localhost:9090)
  - 🗄️ MongoDB persistence (localhost:27017)

## 🆘 Troubleshooting

### Common Issues

**"Failed to connect to MCP servers"**
```bash
# Check Python dependencies
pip install -r requirements.txt

# Verify config file exists
ls -la client/config.yaml
```

**"Ollama not available"**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# Pull required model
ollama pull llama2
```

**"Binance API errors"**
```bash
# Verify your API keys in .env
cat .env | grep BINANCE

# Ensure testnet is enabled for safety
export BINANCE_TESTNET=true
```

**Docker issues**
```bash
# Reset Docker environment
docker-compose down
docker system prune -f
./scripts/start.sh docker
```

### Getting Help

1. **Check logs first**: `tail -f logs/crypto_trader.log`
2. **Run system tests**: `./scripts/start.sh test`
3. **Check system status**: `./scripts/start.sh status`
4. **Review configuration**: Ensure all required API keys are set

## 🔄 System Management

### Start/Stop/Restart
```bash
# Start system
./scripts/start.sh [mode]

# Stop system
./scripts/start.sh [mode] stop

# Restart system
./scripts/start.sh [mode] restart

# Check status
./scripts/start.sh [mode] status
```

### Emergency Stop
```bash
# Immediate stop (kills all processes)
./scripts/start.sh stop

# Or set emergency stop flag
export EMERGENCY_STOP=true
```

### Backup Important Data
```bash
# Backup configuration
cp .env .env.backup
cp client/config.yaml client/config.yaml.backup

# Backup logs and data
tar -czf backup-$(date +%Y%m%d).tar.gz logs/ data/
```

## 🎯 Next Steps

Once your system is running:

1. **Monitor Performance**: Watch logs and metrics
2. **Analyze Results**: Review trading decisions and outcomes
3. **Optimize Settings**: Adjust confidence thresholds and risk parameters
4. **Scale Up**: Add more trading pairs or strategies
5. **Go Live**: Switch to real trading when ready (carefully!)

## 📚 Learn More

- **[Architecture Overview](../README.md)** - Understanding the system design
- **[MCP Server Details](../servers/)** - Deep dive into each component
- **[Configuration Guide](CONFIG.md)** - Advanced configuration options
- **[API Documentation](API.md)** - Integration with external systems

---

**⚠️ Important Disclaimer**: This software is for educational purposes. Cryptocurrency trading carries substantial risk. Never trade with money you cannot afford to lose. Always start with paper trading and testnet before using real funds.

**🎉 Happy Trading!** You're now ready to explore the world of automated crypto trading with your MCP-powered system!