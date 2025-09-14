// MongoDB Initialization Script for Crypto Trading MCP System

// Switch to the crypto_trading database
db = db.getSiblingDB('crypto_trading');

// Create collections with indexes for optimal performance

// Trading data collection
db.createCollection('trades');
db.trades.createIndex({ "timestamp": -1 });
db.trades.createIndex({ "symbol": 1, "timestamp": -1 });
db.trades.createIndex({ "status": 1 });

// Market data collection
db.createCollection('market_data');
db.market_data.createIndex({ "symbol": 1, "timestamp": -1 });
db.market_data.createIndex({ "timeframe": 1, "timestamp": -1 });

// News and sentiment data
db.createCollection('news');
db.news.createIndex({ "timestamp": -1 });
db.news.createIndex({ "source": 1, "timestamp": -1 });
db.news.createIndex({ "sentiment": 1, "timestamp": -1 });

// Social media data
db.createCollection('social_data');
db.social_data.createIndex({ "platform": 1, "timestamp": -1 });
db.social_data.createIndex({ "sentiment": 1, "timestamp": -1 });

// AI analysis results
db.createCollection('ai_analysis');
db.ai_analysis.createIndex({ "timestamp": -1 });
db.ai_analysis.createIndex({ "symbol": 1, "timestamp": -1 });
db.ai_analysis.createIndex({ "confidence": -1, "timestamp": -1 });

// Portfolio and positions
db.createCollection('portfolio');
db.portfolio.createIndex({ "timestamp": -1 });

db.createCollection('positions');
db.positions.createIndex({ "symbol": 1, "status": 1 });
db.positions.createIndex({ "entry_time": -1 });

// Risk management data
db.createCollection('risk_events');
db.risk_events.createIndex({ "timestamp": -1 });
db.risk_events.createIndex({ "event_type": 1, "timestamp": -1 });

// Backtesting results
db.createCollection('backtest_results');
db.backtest_results.createIndex({ "strategy": 1, "start_date": -1 });

// Create user for the application (if authentication is enabled)
// This is only created if MONGO_INITDB_ROOT_USERNAME is set
if (process.env.MONGO_INITDB_ROOT_USERNAME) {
    db.createUser({
        user: "crypto_trader",
        pwd: "crypto_trader_password",
        roles: [
            {
                role: "readWrite",
                db: "crypto_trading"
            }
        ]
    });
}

print("MongoDB initialized successfully for Crypto Trading MCP System");
print("Collections created with appropriate indexes for optimal performance");