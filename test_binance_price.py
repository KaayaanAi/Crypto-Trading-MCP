#!/usr/bin/env python3
"""
Test script to verify Binance API connection and get current BTCUSDT price
"""

import asyncio
import aiohttp
import os
import sys
import ssl
from datetime import datetime

# Load .env file explicitly
from dotenv import load_dotenv
load_dotenv()

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared'))

from utils import load_env_var, create_secure_connector

async def test_binance_price():
    """Test Binance API connection and get current BTCUSDT price"""

    # Load environment variables
    api_key = load_env_var("BINANCE_API_KEY")
    testnet = load_env_var("BINANCE_TESTNET", default=False)

    print(f"API Key loaded: {'Yes' if api_key else 'No'}")
    print(f"Using testnet: {testnet}")

    # Determine base URL
    if testnet:
        base_url = "https://testnet.binance.vision"
        print("🔶 Using TESTNET - prices may be outdated/mock")
    else:
        base_url = "https://api.binance.com"
        print("✅ Using MAINNET - real market prices")

    # Test endpoints
    endpoints_to_test = [
        "/api/v3/ticker/price?symbol=BTCUSDT",
        "/api/v3/ticker/24hr?symbol=BTCUSDT",
        "/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1"
    ]

    # Create secure SSL connector with proper certificate verification
    # SSL verification can be disabled via DISABLE_SSL_VERIFICATION environment variable
    connector = create_secure_connector(verify_ssl=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        for endpoint in endpoints_to_test:
            try:
                url = f"{base_url}{endpoint}"
                print(f"\n📡 Testing: {url}")

                headers = {}
                if api_key:
                    headers["X-MBX-APIKEY"] = api_key

                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()

                        if endpoint.endswith("ticker/price"):
                            price = float(data['price'])
                            print(f"✅ Current BTCUSDT Price: ${price:,.2f}")
                        elif endpoint.endswith("ticker/24hr"):
                            price = float(data['lastPrice'])
                            change = float(data['priceChangePercent'])
                            volume = float(data['volume'])
                            print(f"✅ 24hr Data: Price=${price:,.2f}, Change={change:+.2f}%, Volume={volume:,.0f}")
                        elif "klines" in endpoint:
                            kline = data[0]
                            open_price = float(kline[1])
                            high_price = float(kline[2])
                            low_price = float(kline[3])
                            close_price = float(kline[4])
                            print(f"✅ Latest 1m Candle: O=${open_price:,.2f} H=${high_price:,.2f} L=${low_price:,.2f} C=${close_price:,.2f}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Error {response.status}: {error_text}")

            except Exception as e:
                print(f"❌ Exception: {e}")

    # Compare with CoinMarketCap reference
    print(f"\n🔍 Reference Check:")
    print(f"Expected price from CoinMarketCap: $115,288.09")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")

if __name__ == "__main__":
    asyncio.run(test_binance_price())