#!/usr/bin/env python3
"""
Comprehensive validation script for all MCP servers in the Crypto Trading system.

This script validates:
1. Syntax correctness
2. Import dependencies
3. MCP protocol compliance
4. Tool function definitions
5. Error handling
6. Configuration requirements
"""

import sys
import os
import asyncio
import importlib.util
from typing import Dict, List, Any
import traceback

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))

class ServerValidator:
    """Validates MCP servers for correctness and compliance"""

    def __init__(self):
        self.results = {}
        self.servers = [
            'binance-mcp',
            'crypto-technical-mcp',
            'crypto-news-mcp',
            'crypto-social-mcp',
            'crypto-risk-mcp',
            'crypto-ai-mcp'
        ]

    def validate_shared_modules(self) -> bool:
        """Validate all shared modules can be imported"""
        print("=== Validating Shared Modules ===")

        try:
            import shared_types
            import constants
            import utils
            import exceptions
            print("✓ All shared modules import successfully")

            # Test key classes exist
            from shared_types import TradingSignal, NewsItem, PriceData, TechnicalIndicator
            from utils import setup_logger, safe_float, utc_now
            from constants import TechnicalAnalysis, RiskManagement
            from exceptions import ApiError, ValidationError
            print("✓ Key classes and functions available")

            return True

        except Exception as e:
            print(f"✗ Shared modules validation failed: {e}")
            traceback.print_exc()
            return False

    def validate_mcp_dependencies(self) -> bool:
        """Validate MCP framework dependencies"""
        print("\n=== Validating MCP Dependencies ===")

        try:
            from mcp.server import Server
            from mcp.server.stdio import stdio_server
            print("✓ MCP server framework available")

            # Test server creation
            test_server = Server("test-validation-server")
            print("✓ Server instance can be created")

            return True

        except Exception as e:
            print(f"✗ MCP dependencies validation failed: {e}")
            return False

    def validate_python_dependencies(self) -> bool:
        """Validate Python standard and external dependencies"""
        print("\n=== Validating Python Dependencies ===")

        # Core dependencies that should always be available
        core_deps = [
            'asyncio', 'sys', 'os', 'typing', 'datetime', 'json',
            'logging', 'hashlib', 'hmac', 'ssl', 'decimal', 'dataclasses'
        ]

        # Scientific/data dependencies
        data_deps = ['numpy', 'pandas']

        # Network dependencies
        network_deps = ['aiohttp']

        # Validation dependencies
        validation_deps = ['pydantic']

        # Optional external dependencies
        optional_deps = {
            'feedparser': 'RSS feed parsing (crypto-news-mcp)',
            'beautifulsoup4': 'HTML parsing (crypto-news-mcp)',
            'dotenv': 'Environment variables',
            'tenacity': 'Retry mechanisms',
            'backoff': 'Exponential backoff',
            'scipy': 'Statistical calculations (crypto-risk-mcp)'
        }

        all_good = True

        # Test core dependencies
        for dep in core_deps + data_deps + network_deps + validation_deps:
            try:
                __import__(dep)
                print(f"✓ {dep}")
            except ImportError as e:
                print(f"✗ {dep}: {e}")
                all_good = False

        # Test optional dependencies
        print("\nOptional Dependencies:")
        for dep, desc in optional_deps.items():
            try:
                if dep == 'beautifulsoup4':
                    import bs4
                elif dep == 'dotenv':
                    from dotenv import load_dotenv
                else:
                    __import__(dep)
                print(f"✓ {dep} - {desc}")
            except ImportError:
                print(f"⚠ {dep} - {desc} (optional, will use fallback)")

        return all_good

    def validate_server_structure(self, server_name: str) -> Dict[str, Any]:
        """Validate individual server structure and compliance"""
        print(f"\n=== Validating {server_name} ===")

        result = {
            'name': server_name,
            'syntax_valid': False,
            'imports_valid': False,
            'server_instance': False,
            'tools_defined': False,
            'main_function': False,
            'error_handling': False,
            'issues': []
        }

        server_path = f"servers/{server_name}/main.py"

        if not os.path.exists(server_path):
            result['issues'].append(f"Server file not found: {server_path}")
            return result

        # Test syntax by compilation
        try:
            with open(server_path, 'r') as f:
                content = f.read()

            compile(content, server_path, 'exec')
            result['syntax_valid'] = True
            print(f"✓ {server_name} syntax is valid")

        except SyntaxError as e:
            result['issues'].append(f"Syntax error: {e}")
            print(f"✗ {server_name} syntax error: {e}")
            return result

        # Analyze the content for required components
        try:
            with open(server_path, 'r') as f:
                content = f.read()

            # Check for required imports
            required_patterns = [
                'from mcp.server import Server',
                'from mcp.server.stdio import stdio_server',
                'server = Server(',
                'async def main(',
                '@server.call_tool()'
            ]

            for pattern in required_patterns:
                if pattern in content:
                    if pattern == 'from mcp.server import Server':
                        result['imports_valid'] = True
                    elif pattern == 'server = Server(':
                        result['server_instance'] = True
                    elif pattern == 'async def main(':
                        result['main_function'] = True
                    elif pattern == '@server.call_tool()':
                        result['tools_defined'] = True
                else:
                    result['issues'].append(f"Missing required pattern: {pattern}")

            # Check for error handling patterns
            error_patterns = ['try:', 'except:', 'handle_error', 'logger.error']
            if any(pattern in content for pattern in error_patterns):
                result['error_handling'] = True
            else:
                result['issues'].append("No error handling patterns found")

            # Count number of tools
            tool_count = content.count('@server.call_tool()')
            print(f"✓ {server_name} has {tool_count} MCP tools defined")

            if result['syntax_valid'] and result['imports_valid'] and result['server_instance']:
                print(f"✓ {server_name} basic structure is valid")
            else:
                print(f"⚠ {server_name} has structural issues")

        except Exception as e:
            result['issues'].append(f"Analysis error: {e}")
            print(f"✗ {server_name} analysis failed: {e}")

        return result

    def validate_configuration_requirements(self) -> bool:
        """Validate configuration and environment requirements"""
        print("\n=== Validating Configuration Requirements ===")

        # Check for .env file or environment variables
        env_file_exists = os.path.exists('.env')
        if env_file_exists:
            print("✓ .env file found")
        else:
            print("⚠ .env file not found (may use system environment variables)")

        # Check for logs directory
        if not os.path.exists('logs'):
            print("⚠ logs directory does not exist (will be created by servers)")
        else:
            print("✓ logs directory exists")

        # Check requirements.txt
        if os.path.exists('requirements.txt'):
            print("✓ requirements.txt found")
            try:
                with open('requirements.txt', 'r') as f:
                    requirements = f.read()
                    required_packages = ['mcp', 'aiohttp', 'pydantic', 'pandas', 'numpy']
                    for package in required_packages:
                        if package in requirements:
                            print(f"✓ {package} listed in requirements")
                        else:
                            print(f"⚠ {package} not found in requirements")
            except Exception as e:
                print(f"✗ Error reading requirements.txt: {e}")
        else:
            print("⚠ requirements.txt not found")

        return True

    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run complete validation suite"""
        print("🔍 Starting Comprehensive MCP Server Validation\n")

        # Step 1: Validate shared modules
        shared_valid = self.validate_shared_modules()

        # Step 2: Validate MCP dependencies
        mcp_valid = self.validate_mcp_dependencies()

        # Step 3: Validate Python dependencies
        python_valid = self.validate_python_dependencies()

        # Step 4: Validate configuration
        config_valid = self.validate_configuration_requirements()

        # Step 5: Validate each server
        server_results = []
        for server_name in self.servers:
            result = self.validate_server_structure(server_name)
            server_results.append(result)

        # Summary
        print("\n" + "="*60)
        print("🎯 VALIDATION SUMMARY")
        print("="*60)

        print(f"Shared Modules: {'✓ PASS' if shared_valid else '✗ FAIL'}")
        print(f"MCP Framework: {'✓ PASS' if mcp_valid else '✗ FAIL'}")
        print(f"Python Dependencies: {'✓ PASS' if python_valid else '✗ FAIL'}")
        print(f"Configuration: {'✓ PASS' if config_valid else '✗ FAIL'}")

        print("\nServer Validation Results:")
        all_servers_valid = True

        for result in server_results:
            server_name = result['name']
            is_valid = (result['syntax_valid'] and result['imports_valid']
                       and result['server_instance'] and result['tools_defined']
                       and result['main_function'])

            status = "✓ PASS" if is_valid else "✗ FAIL"
            print(f"  {server_name:20} {status}")

            if not is_valid:
                all_servers_valid = False
                for issue in result['issues'][:3]:  # Show first 3 issues
                    print(f"    - {issue}")

        overall_status = (shared_valid and mcp_valid and python_valid
                         and config_valid and all_servers_valid)

        print("\n" + "="*60)
        print(f"🏆 OVERALL STATUS: {'✅ ALL SYSTEMS VALID' if overall_status else '❌ ISSUES FOUND'}")
        print("="*60)

        return {
            'overall_valid': overall_status,
            'shared_modules': shared_valid,
            'mcp_framework': mcp_valid,
            'python_dependencies': python_valid,
            'configuration': config_valid,
            'servers': server_results
        }

def main():
    """Main validation entry point"""
    validator = ServerValidator()
    results = validator.run_comprehensive_validation()

    # Exit with appropriate code
    sys.exit(0 if results['overall_valid'] else 1)

if __name__ == "__main__":
    main()