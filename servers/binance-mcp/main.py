#!/usr/bin/env python3
"""
Binance MCP Server

Provides comprehensive Binance exchange integration including:
- Real-time market data (prices, orderbook, trades)
- Account management (balances, positions, history)
- Order execution (market, limit, stop-loss orders)
- Whale movement tracking
- Risk management integration
"""

import asyncio
import sys
import os
import hmac
import hashlib
import time
import ssl
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
from decimal import Decimal

# Load .env file explicitly
from dotenv import load_dotenv
load_dotenv()

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from shared_types import PriceData, OrderRequest, OrderResponse, Position, AccountInfo, OrderSide, OrderType
from utils import setup_logger, safe_float, utc_now, load_env_var, cache, RateLimiter, create_secure_connector
from constants import ApiRateLimits
from exceptions import (
    ApiError, ApiRateLimitError, MarketDataError, OrderExecutionError,
    InvalidOrderError, InsufficientBalanceError, ConfigurationError,
    MissingApiKeyError, NetworkError, TimeoutError, ValidationError,
    handle_error, validate_required_params, validate_numeric_range
)


# Initialize server and logger
server = Server("binance-mcp")
logger = setup_logger("binance-mcp", log_file="logs/binance_server.log")


class BinanceClient:
    """Binance API client with authentication and rate limiting"""

    def __init__(self):
        try:
            self.api_key = load_env_var("BINANCE_API_KEY", required=True)
            self.secret_key = load_env_var("BINANCE_SECRET_KEY", required=True)
        except Exception as e:
            raise MissingApiKeyError(
                "Binance",
                details={"required_vars": ["BINANCE_API_KEY", "BINANCE_SECRET_KEY"]}
            ) from e

        self.testnet = load_env_var("BINANCE_TESTNET", default=True)

        # Set base URLs
        if self.testnet:
            self.base_url = "https://testnet.binance.vision"
            logger.info("Using Binance Testnet")
        else:
            self.base_url = "https://api.binance.com"
            logger.info("Using Binance Mainnet")

        # Rate limiters
        self.rate_limiter = RateLimiter(max_calls=ApiRateLimits.BINANCE_RATE_LIMIT_CALLS, window_seconds=ApiRateLimits.BINANCE_RATE_LIMIT_WINDOW)
        self.order_rate_limiter = RateLimiter(max_calls=ApiRateLimits.BINANCE_ORDER_RATE_LIMIT_CALLS, window_seconds=ApiRateLimits.BINANCE_ORDER_RATE_LIMIT_WINDOW)

        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        # Create secure SSL connector with proper certificate verification
        # SSL verification can be disabled via DISABLE_SSL_VERIFICATION environment variable
        connector = create_secure_connector(verify_ssl=True)
        self.session = aiohttp.ClientSession(connector=connector)
        logger.info("Initialized Binance client with secure SSL configuration")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature for authenticated requests"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        signed: bool = False
    ) -> Dict[str, Any]:
        """Make authenticated request to Binance API"""
        await self.rate_limiter.acquire()

        url = f"{self.base_url}{endpoint}"
        headers = {"X-MBX-APIKEY": self.api_key}

        if params is None:
            params = {}

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            params['signature'] = self._generate_signature(query_string)

        try:
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=ApiRateLimits.BINANCE_API_TIMEOUT)
            ) as response:
                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientResponseError as e:
            error_text = await e.response.text() if e.response else "Unknown error"

            # Handle specific HTTP status codes
            if e.status == 429:
                raise ApiRateLimitError(
                    f"Binance API rate limit exceeded: {error_text}",
                    status_code=e.status,
                    retry_after=int(e.headers.get('Retry-After', 60))
                ) from e
            elif e.status == 401:
                raise ApiError(
                    f"Binance API authentication failed: {error_text}",
                    status_code=e.status,
                    details={"endpoint": endpoint}
                ) from e
            elif e.status >= 500:
                raise ApiError(
                    f"Binance API server error: {error_text}",
                    status_code=e.status,
                    details={"endpoint": endpoint}
                ) from e
            else:
                raise ApiError(
                    f"Binance API error: {error_text}",
                    status_code=e.status,
                    details={"endpoint": endpoint}
                ) from e

        except asyncio.TimeoutError as e:
            raise TimeoutError(
                f"Request to Binance API timed out: {endpoint}",
                timeout_seconds=ApiRateLimits.BINANCE_API_TIMEOUT,
                details={"endpoint": endpoint}
            ) from e
        except Exception as e:
            raise NetworkError(
                f"Network error calling Binance API: {str(e)}",
                details={"endpoint": endpoint}
            ) from e

    async def get_server_time(self) -> int:
        """Get Binance server time"""
        response = await self._make_request("GET", "/api/v3/time")
        return response["serverTime"]

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information including balances"""
        return await self._make_request("GET", "/api/v3/account", signed=True)

    async def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """Get current price for a symbol"""
        params = {"symbol": symbol}
        return await self._make_request("GET", "/api/v3/ticker/price", params=params)

    async def get_24hr_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get 24hr price change statistics"""
        params = {"symbol": symbol}
        return await self._make_request("GET", "/api/v3/ticker/24hr", params=params)

    async def get_orderbook(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get order book for a symbol"""
        params = {"symbol": symbol, "limit": limit}
        return await self._make_request("GET", "/api/v3/depth", params=params)

    async def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Get recent trades for a symbol"""
        params = {"symbol": symbol, "limit": limit}
        return await self._make_request("GET", "/api/v3/trades", params=params)

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC"
    ) -> Dict[str, Any]:
        """Place a new order"""
        await self.order_rate_limiter.acquire()

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": f"{quantity:.8f}",
            "timeInForce": time_in_force
        }

        if price is not None:
            params["price"] = f"{price:.8f}"

        if stop_price is not None:
            params["stopPrice"] = f"{stop_price:.8f}"

        return await self._make_request("POST", "/api/v3/order", params=params, signed=True)

    async def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an existing order"""
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        return await self._make_request("DELETE", "/api/v3/order", params=params, signed=True)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open orders"""
        params = {}
        if symbol:
            params["symbol"] = symbol

        return await self._make_request("GET", "/api/v3/openOrders", params=params, signed=True)

    async def get_order_history(self, symbol: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Get order history for a symbol"""
        params = {
            "symbol": symbol,
            "limit": limit
        }
        return await self._make_request("GET", "/api/v3/allOrders", params=params, signed=True)


class WhaleTracker:
    """Track large transactions and whale movements"""

    def __init__(self, binance_client: BinanceClient):
        self.client = binance_client
        self.whale_threshold = ApiRateLimits.WHALE_THRESHOLD_USD

    async def track_large_trades(self, symbol: str, lookback_minutes: int = 60) -> List[Dict[str, Any]]:
        """Track large trades that could be whale movements"""
        try:
            trades = await self.client.get_recent_trades(symbol, limit=1000)
            current_price = safe_float((await self.client.get_ticker_price(symbol))["price"])

            large_trades = []
            cutoff_time = int((time.time() - lookback_minutes * 60) * 1000)

            for trade in trades:
                trade_time = int(trade["time"])
                if trade_time < cutoff_time:
                    continue

                quantity = safe_float(trade["qty"])
                trade_value = quantity * current_price

                if trade_value >= self.whale_threshold:
                    large_trades.append({
                        "time": datetime.fromtimestamp(trade_time / 1000).isoformat(),
                        "price": safe_float(trade["price"]),
                        "quantity": quantity,
                        "value_usd": trade_value,
                        "is_buyer_maker": trade["isBuyerMaker"]
                    })

            return sorted(large_trades, key=lambda x: x["time"], reverse=True)

        except Exception as e:
            raise MarketDataError(
                "Failed to track whale movements",
                details={"symbol": symbol, "lookback_minutes": lookback_minutes},
                cause=e
            ) from e


# MCP Server Tools
@server.call_tool()
async def get_market_data(
    symbol: str,
    data_type: str = "ticker"
) -> Dict[str, Any]:
    """
    Get real-time market data from Binance

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        data_type: Type of data (ticker, orderbook, trades, 24hr)

    Returns:
        Dict containing market data
    """
    try:
        logger.info(f"Getting {data_type} data for {symbol}")

        async with BinanceClient() as client:
            if data_type == "ticker":
                data = await client.get_ticker_price(symbol)
                return {
                    "success": True,
                    "symbol": symbol,
                    "price": safe_float(data["price"]),
                    "timestamp": utc_now().isoformat()
                }

            elif data_type == "24hr":
                data = await client.get_24hr_ticker(symbol)
                return {
                    "success": True,
                    "symbol": symbol,
                    "price": safe_float(data["lastPrice"]),
                    "change": safe_float(data["priceChange"]),
                    "change_percent": safe_float(data["priceChangePercent"]),
                    "high": safe_float(data["highPrice"]),
                    "low": safe_float(data["lowPrice"]),
                    "volume": safe_float(data["volume"]),
                    "quote_volume": safe_float(data["quoteVolume"]),
                    "timestamp": utc_now().isoformat()
                }

            elif data_type == "orderbook":
                data = await client.get_orderbook(symbol, limit=20)
                return {
                    "success": True,
                    "symbol": symbol,
                    "bids": [[safe_float(bid[0]), safe_float(bid[1])] for bid in data["bids"][:10]],
                    "asks": [[safe_float(ask[0]), safe_float(ask[1])] for ask in data["asks"][:10]],
                    "timestamp": utc_now().isoformat()
                }

            elif data_type == "trades":
                trades = await client.get_recent_trades(symbol, limit=100)
                return {
                    "success": True,
                    "symbol": symbol,
                    "trades": [
                        {
                            "price": safe_float(trade["price"]),
                            "quantity": safe_float(trade["qty"]),
                            "time": datetime.fromtimestamp(int(trade["time"]) / 1000).isoformat(),
                            "is_buyer_maker": trade["isBuyerMaker"]
                        }
                        for trade in trades[:20]
                    ],
                    "timestamp": utc_now().isoformat()
                }

            else:
                raise ValidationError(
                    f"Invalid data_type: {data_type}",
                    field="data_type",
                    value=data_type,
                    details={"valid_values": ["ticker", "orderbook", "trades", "24hr"]}
                )

    except Exception as e:
        return handle_error(e, context="get_market_data", reraise=False)


@server.call_tool()
async def get_account_info() -> Dict[str, Any]:
    """
    Get account balance and position information

    Returns:
        Dict containing account information
    """
    try:
        logger.info("Getting account information")

        async with BinanceClient() as client:
            account_data = await client.get_account_info()

            # Extract balances
            balances = []
            total_btc_value = 0.0

            for balance in account_data["balances"]:
                free_balance = safe_float(balance["free"])
                locked_balance = safe_float(balance["locked"])
                total_balance = free_balance + locked_balance

                if total_balance > 0:
                    balances.append({
                        "asset": balance["asset"],
                        "free": free_balance,
                        "locked": locked_balance,
                        "total": total_balance
                    })

            return {
                "success": True,
                "account_type": account_data.get("accountType", "SPOT"),
                "can_trade": account_data.get("canTrade", False),
                "can_withdraw": account_data.get("canWithdraw", False),
                "can_deposit": account_data.get("canDeposit", False),
                "balances": balances,
                "permissions": account_data.get("permissions", []),
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        return handle_error(e, context="get_account_info", reraise=False)


@server.call_tool()
async def place_order(
    symbol: str,
    side: str,
    type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "GTC"
) -> Dict[str, Any]:
    """
    Place a trading order

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        side: Order side (BUY or SELL)
        type: Order type (MARKET, LIMIT, STOP_LIMIT)
        quantity: Order quantity
        price: Order price (required for LIMIT orders)
        stop_price: Stop price (required for STOP_LIMIT orders)
        time_in_force: Time in force (GTC, IOC, FOK)

    Returns:
        Dict containing order execution result
    """
    try:
        logger.info(f"Placing {side} {type} order for {quantity} {symbol}")

        # Validate inputs
        validate_required_params(
            {"symbol": symbol, "side": side, "type": type, "quantity": quantity},
            ["symbol", "side", "type", "quantity"]
        )

        validate_numeric_range(quantity, min_value=0.00000001, field_name="quantity")

        if type.upper() == "LIMIT" and price is None:
            raise InvalidOrderError(
                "Price is required for LIMIT orders",
                details={"order_type": type.upper()}
            )

        if type.upper() == "STOP_LIMIT" and (price is None or stop_price is None):
            raise InvalidOrderError(
                "Both price and stop_price are required for STOP_LIMIT orders",
                details={"order_type": type.upper(), "price_provided": price is not None, "stop_price_provided": stop_price is not None}
            )

        if price is not None:
            validate_numeric_range(price, min_value=0.00000001, field_name="price")

        if stop_price is not None:
            validate_numeric_range(stop_price, min_value=0.00000001, field_name="stop_price")

        async with BinanceClient() as client:
            order_result = await client.place_order(
                symbol=symbol,
                side=side,
                order_type=type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                time_in_force=time_in_force
            )

            return {
                "success": True,
                "order_id": order_result["orderId"],
                "symbol": order_result["symbol"],
                "side": order_result["side"],
                "type": order_result["type"],
                "quantity": safe_float(order_result["origQty"]),
                "price": safe_float(order_result.get("price", 0)),
                "status": order_result["status"],
                "time_in_force": order_result["timeInForce"],
                "fills": [
                    {
                        "price": safe_float(fill["price"]),
                        "quantity": safe_float(fill["qty"]),
                        "commission": safe_float(fill["commission"])
                    }
                    for fill in order_result.get("fills", [])
                ],
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        return handle_error(e, context="place_order", reraise=False)


@server.call_tool()
async def cancel_order(
    symbol: str,
    order_id: int
) -> Dict[str, Any]:
    """
    Cancel an existing order

    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        order_id: Order ID to cancel

    Returns:
        Dict containing cancellation result
    """
    try:
        logger.info(f"Cancelling order {order_id} for {symbol}")

        async with BinanceClient() as client:
            result = await client.cancel_order(symbol, order_id)

            return {
                "success": True,
                "order_id": result["orderId"],
                "symbol": result["symbol"],
                "status": result["status"],
                "original_quantity": safe_float(result["origQty"]),
                "executed_quantity": safe_float(result["executedQty"]),
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        return handle_error(e, context="cancel_order", reraise=False)


@server.call_tool()
async def get_open_orders(
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all open orders

    Args:
        symbol: Trading pair to filter by (optional)

    Returns:
        Dict containing open orders
    """
    try:
        logger.info(f"Getting open orders for {symbol or 'all symbols'}")

        async with BinanceClient() as client:
            orders = await client.get_open_orders(symbol)

            formatted_orders = []
            for order in orders:
                formatted_orders.append({
                    "order_id": order["orderId"],
                    "symbol": order["symbol"],
                    "side": order["side"],
                    "type": order["type"],
                    "quantity": safe_float(order["origQty"]),
                    "price": safe_float(order["price"]),
                    "executed_quantity": safe_float(order["executedQty"]),
                    "status": order["status"],
                    "time_in_force": order["timeInForce"],
                    "time": datetime.fromtimestamp(int(order["time"]) / 1000).isoformat()
                })

            return {
                "success": True,
                "orders": formatted_orders,
                "total_orders": len(formatted_orders),
                "symbol_filter": symbol,
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        return handle_error(e, context="get_open_orders", reraise=False)


@server.call_tool()
async def get_whale_movements(
    symbol: str,
    lookback_minutes: int = 60,
    min_value_usd: float = 1000000
) -> Dict[str, Any]:
    """
    Track large transactions and whale movements

    Args:
        symbol: Trading pair to monitor (e.g., BTCUSDT)
        lookback_minutes: How many minutes to look back
        min_value_usd: Minimum trade value in USD to consider as whale movement

    Returns:
        Dict containing whale movement data
    """
    try:
        logger.info(f"Tracking whale movements for {symbol}")

        async with BinanceClient() as client:
            whale_tracker = WhaleTracker(client)
            whale_tracker.whale_threshold = min_value_usd

            large_trades = await whale_tracker.track_large_trades(symbol, lookback_minutes)

            # Analyze patterns
            total_buy_volume = sum(trade["value_usd"] for trade in large_trades if not trade["is_buyer_maker"])
            total_sell_volume = sum(trade["value_usd"] for trade in large_trades if trade["is_buyer_maker"])

            net_flow = total_buy_volume - total_sell_volume

            return {
                "success": True,
                "symbol": symbol,
                "lookback_minutes": lookback_minutes,
                "whale_trades": large_trades,
                "total_whale_trades": len(large_trades),
                "total_buy_volume_usd": total_buy_volume,
                "total_sell_volume_usd": total_sell_volume,
                "net_flow_usd": net_flow,
                "sentiment": "bullish" if net_flow > 0 else "bearish" if net_flow < 0 else "neutral",
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        return handle_error(e, context="get_whale_movements", reraise=False)


@server.call_tool()
async def get_trading_fees(
    symbol: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get current trading fees

    Args:
        symbol: Specific symbol to get fees for (optional)

    Returns:
        Dict containing trading fee information
    """
    try:
        logger.info("Getting trading fees")

        async with BinanceClient() as client:
            # Get account info which includes trading fees
            account_data = await client.get_account_info()

            # Default fee rates (can be overridden by account-specific rates)
            maker_commission = safe_float(account_data.get("makerCommission", 10)) / 10000  # Convert basis points
            taker_commission = safe_float(account_data.get("takerCommission", 10)) / 10000

            return {
                "success": True,
                "maker_fee_rate": maker_commission,
                "taker_fee_rate": taker_commission,
                "buyer_commission": safe_float(account_data.get("buyerCommission", 0)) / 10000,
                "seller_commission": safe_float(account_data.get("sellerCommission", 0)) / 10000,
                "can_trade": account_data.get("canTrade", False),
                "symbol_filter": symbol,
                "timestamp": utc_now().isoformat()
            }

    except Exception as e:
        return handle_error(e, context="get_trading_fees", reraise=False)


async def main():
    """Main server entry point"""
    logger.info("Starting Binance MCP Server")

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Verify API credentials are available
    api_key = load_env_var("BINANCE_API_KEY")
    secret_key = load_env_var("BINANCE_SECRET_KEY")

    if not api_key or not secret_key:
        logger.critical("Binance API credentials not found in environment variables")
        logger.critical("Please set BINANCE_API_KEY and BINANCE_SECRET_KEY")
        raise ConfigurationError(
            "Missing Binance API credentials",
            details={"required_vars": ["BINANCE_API_KEY", "BINANCE_SECRET_KEY"]}
        )

    try:
        async with stdio_server() as streams:
            await server.run(
                streams[0], streams[1],
                server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Binance MCP server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())