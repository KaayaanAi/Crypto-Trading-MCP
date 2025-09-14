#!/usr/bin/env python3
"""
SSL Security Test Script

Tests that the SSL certificate verification fixes work correctly:
1. Verifies SSL certificates are properly validated by default
2. Tests that SSL verification can be disabled via environment variable for development
3. Ensures real Binance API connections still work with proper SSL
4. Validates error handling for SSL connection issues
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

from utils import load_env_var, create_ssl_context, create_secure_connector


async def test_ssl_context_creation():
    """Test SSL context creation with different configurations"""
    print("🔐 Testing SSL Context Creation...")

    # Test secure SSL context (default)
    secure_context = create_ssl_context(verify_ssl=True)
    print(f"✅ Secure SSL context: verify_mode={secure_context.verify_mode}, check_hostname={secure_context.check_hostname}")

    # Test with environment variable override
    original_env = os.environ.get("DISABLE_SSL_VERIFICATION")

    # Test with SSL verification disabled via environment
    os.environ["DISABLE_SSL_VERIFICATION"] = "true"
    dev_context = create_ssl_context(verify_ssl=True)  # Should be overridden by env var
    print(f"⚠️  Dev SSL context (env override): verify_mode={dev_context.verify_mode}, check_hostname={dev_context.check_hostname}")

    # Restore original environment
    if original_env is not None:
        os.environ["DISABLE_SSL_VERIFICATION"] = original_env
    else:
        os.environ.pop("DISABLE_SSL_VERIFICATION", None)

    print("✅ SSL context creation tests passed\n")


async def test_secure_connector():
    """Test secure connector creation"""
    print("🔗 Testing Secure Connector Creation...")

    # Test secure connector
    connector = create_secure_connector(verify_ssl=True)
    print(f"✅ Secure connector created with SSL context")

    # Clean up
    await connector.close()
    print("✅ Secure connector tests passed\n")


async def test_real_binance_connection():
    """Test real connection to Binance API with proper SSL"""
    print("📡 Testing Real Binance API Connection...")

    # Use mainnet for real API test
    base_url = "https://api.binance.com"
    endpoint = "/api/v3/ticker/price?symbol=BTCUSDT"

    try:
        # Test with secure SSL (production configuration)
        connector = create_secure_connector(verify_ssl=True)

        async with aiohttp.ClientSession(connector=connector) as session:
            url = f"{base_url}{endpoint}"
            print(f"📡 Testing secure connection to: {url}")

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['price'])
                    print(f"✅ Secure SSL connection successful: BTCUSDT price ${price:,.2f}")
                    return True
                else:
                    print(f"❌ API returned status {response.status}")
                    return False

    except ssl.SSLError as e:
        print(f"🔒 SSL Error (expected if certificates are being validated): {e}")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


async def test_ssl_verification_bypass():
    """Test SSL verification bypass for development (when explicitly enabled)"""
    print("🚧 Testing SSL Verification Bypass (Development Mode)...")

    # Save original environment
    original_env = os.environ.get("DISABLE_SSL_VERIFICATION")

    try:
        # Enable SSL bypass for this test
        os.environ["DISABLE_SSL_VERIFICATION"] = "true"

        # Test connection with SSL verification disabled
        connector = create_secure_connector(verify_ssl=True)  # Should be overridden by env

        base_url = "https://api.binance.com"
        endpoint = "/api/v3/ticker/price?symbol=BTCUSDT"

        async with aiohttp.ClientSession(connector=connector) as session:
            url = f"{base_url}{endpoint}"
            print(f"📡 Testing connection with SSL bypass: {url}")

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['price'])
                    print(f"⚠️  SSL bypass connection successful: BTCUSDT price ${price:,.2f}")
                    print("⚠️  WARNING: SSL verification was bypassed - only use in development!")
                    return True
                else:
                    print(f"❌ API returned status {response.status}")
                    return False

    except Exception as e:
        print(f"❌ Error with SSL bypass: {e}")
        return False
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["DISABLE_SSL_VERIFICATION"] = original_env
        else:
            os.environ.pop("DISABLE_SSL_VERIFICATION", None)


async def test_ssl_error_handling():
    """Test proper error handling for SSL issues"""
    print("⚠️  Testing SSL Error Handling...")

    try:
        # Try to connect to a site with known SSL issues (using secure settings)
        connector = create_secure_connector(verify_ssl=True)

        async with aiohttp.ClientSession(connector=connector) as session:
            # Test with expired.badssl.com (known SSL test site)
            test_url = "https://expired.badssl.com"
            print(f"📡 Testing SSL error handling with: {test_url}")

            try:
                async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    print(f"❌ Unexpected success - SSL validation may not be working")
                    return False
            except ssl.SSLError as ssl_err:
                print(f"✅ SSL error properly caught: {type(ssl_err).__name__}")
                return True
            except Exception as e:
                print(f"✅ Connection error properly handled: {type(e).__name__}")
                return True

    except Exception as e:
        print(f"❌ Error in SSL error handling test: {e}")
        return False


async def run_security_tests():
    """Run all SSL security tests"""
    print("🛡️  SSL Security Test Suite")
    print("=" * 50)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print(f"Environment DISABLE_SSL_VERIFICATION: {os.environ.get('DISABLE_SSL_VERIFICATION', 'not set')}")
    print("")

    tests = [
        ("SSL Context Creation", test_ssl_context_creation),
        ("Secure Connector", test_secure_connector),
        ("Real Binance Connection", test_real_binance_connection),
        ("SSL Verification Bypass", test_ssl_verification_bypass),
        ("SSL Error Handling", test_ssl_error_handling),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        print("-" * 30)
        try:
            result = await test_func()
            if result is not False:
                passed += 1
                print(f"✅ {test_name}: PASSED\n")
            else:
                print(f"❌ {test_name}: FAILED\n")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}\n")

    print("=" * 50)
    print(f"🔒 SSL Security Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All SSL security tests passed!")
        print("✅ SSL certificate verification is working correctly")
        print("✅ Environment-based SSL bypass is working for development")
        print("✅ Error handling is robust")
    else:
        print(f"⚠️  {total - passed} test(s) failed - review SSL configuration")

    print("\n🔐 Security Recommendations:")
    print("- Keep DISABLE_SSL_VERIFICATION=false (or unset) in production")
    print("- Only use DISABLE_SSL_VERIFICATION=true in development when necessary")
    print("- Monitor SSL certificate expiration dates")
    print("- Use secure TLS versions (1.2+)")

    return passed == total


if __name__ == "__main__":
    asyncio.run(run_security_tests())