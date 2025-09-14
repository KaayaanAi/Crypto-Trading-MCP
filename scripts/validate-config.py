#!/usr/bin/env python3
"""
Configuration Validation Script for Crypto Trading MCP System
Validates all configuration files and environment setup.
"""

import os
import sys
import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ConfigValidator:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        self.warnings = []

    def validate_all(self) -> bool:
        """Run all validation checks"""
        logger.info("🔍 Starting configuration validation...")

        # Validate environment files
        self.validate_env_files()

        # Validate YAML files
        self.validate_yaml_files()

        # Validate docker configuration
        self.validate_docker_config()

        # Validate directory structure
        self.validate_directory_structure()

        # Validate required scripts
        self.validate_required_scripts()

        # Report results
        return self.report_results()

    def validate_env_files(self):
        """Validate environment configuration files"""
        logger.info("Validating environment files...")

        env_example = self.project_root / ".env.example"
        env_file = self.project_root / ".env"

        if not env_example.exists():
            self.issues.append("❌ .env.example file is missing")
            return

        # Validate .env.example structure
        try:
            with open(env_example, 'r') as f:
                content = f.read()

            # Check for required sections
            required_sections = [
                "TRADING CONFIGURATION",
                "BINANCE API CONFIGURATION",
                "DATABASE CONFIGURATION",
                "SECURITY AND SSL"
            ]

            for section in required_sections:
                if section not in content:
                    self.issues.append(f"❌ Missing section '{section}' in .env.example")

            # Check for placeholder values
            if "your_binance_api_key_here" not in content:
                self.warnings.append("⚠️ .env.example may contain real API keys instead of placeholders")

            # Validate required environment variables
            required_vars = [
                "BINANCE_API_KEY", "BINANCE_SECRET_KEY", "DEFAULT_SYMBOL",
                "RISK_PER_TRADE", "MIN_CONFIDENCE", "ENABLE_PAPER_TRADING"
            ]

            for var in required_vars:
                if f"{var}=" not in content:
                    self.issues.append(f"❌ Missing required variable {var} in .env.example")

        except Exception as e:
            self.issues.append(f"❌ Error reading .env.example: {str(e)}")

        # Check if .env exists and warn if not
        if not env_file.exists():
            self.warnings.append("⚠️ .env file not found - copy from .env.example and configure")

    def validate_yaml_files(self):
        """Validate YAML configuration files"""
        logger.info("Validating YAML files...")

        yaml_files = [
            "client/config.yaml",
            "docker-compose.yml",
            "monitoring/prometheus.yml"
        ]

        for yaml_file in yaml_files:
            file_path = self.project_root / yaml_file

            if not file_path.exists():
                if yaml_file == "monitoring/prometheus.yml":
                    self.warnings.append(f"⚠️ Optional file {yaml_file} not found")
                else:
                    self.issues.append(f"❌ Required file {yaml_file} not found")
                continue

            try:
                with open(file_path, 'r') as f:
                    yaml.safe_load(f)
                logger.info(f"✅ {yaml_file} is valid YAML")

                # Specific validations for different files
                if yaml_file == "client/config.yaml":
                    self.validate_client_config(file_path)
                elif yaml_file == "docker-compose.yml":
                    self.validate_docker_compose(file_path)

            except yaml.YAMLError as e:
                self.issues.append(f"❌ Invalid YAML in {yaml_file}: {str(e)}")
            except Exception as e:
                self.issues.append(f"❌ Error reading {yaml_file}: {str(e)}")

    def validate_client_config(self, config_path: Path):
        """Validate client configuration specifics"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Check required sections
            required_sections = ["trading", "risk_management", "mcp_servers"]
            for section in required_sections:
                if section not in config:
                    self.issues.append(f"❌ Missing section '{section}' in client config")

            # Validate trading configuration
            if "trading" in config:
                trading = config["trading"]
                if trading.get("risk_per_trade", 0) > 0.1:
                    self.warnings.append("⚠️ Risk per trade is > 10% - very high risk!")

                if not trading.get("min_confidence", 0):
                    self.warnings.append("⚠️ No minimum confidence threshold set")

            # Validate risk management
            if "risk_management" in config:
                risk = config["risk_management"]
                if risk.get("max_drawdown", 0) > 0.3:
                    self.warnings.append("⚠️ Max drawdown > 30% - very high risk!")

        except Exception as e:
            self.issues.append(f"❌ Error validating client config: {str(e)}")

    def validate_docker_compose(self, compose_path: Path):
        """Validate docker-compose configuration"""
        try:
            with open(compose_path, 'r') as f:
                compose = yaml.safe_load(f)

            # Check for required services
            services = compose.get("services", {})
            required_services = ["crypto-trader", "ollama", "redis"]

            for service in required_services:
                if service not in services:
                    self.issues.append(f"❌ Missing required service '{service}' in docker-compose.yml")

            # Check for paper trading safety
            if "crypto-trader" in services:
                env_vars = services["crypto-trader"].get("environment", [])
                paper_trading_set = any("ENABLE_PAPER_TRADING" in str(var) for var in env_vars)
                if not paper_trading_set:
                    self.warnings.append("⚠️ ENABLE_PAPER_TRADING not explicitly set in docker-compose")

        except Exception as e:
            self.issues.append(f"❌ Error validating docker-compose: {str(e)}")

    def validate_docker_config(self):
        """Validate Docker-related configuration"""
        logger.info("Validating Docker configuration...")

        dockerfile = self.project_root / "Dockerfile"
        if not dockerfile.exists():
            self.issues.append("❌ Dockerfile is missing")

        # Check if docker-compose references existing files
        compose_file = self.project_root / "docker-compose.yml"
        if compose_file.exists():
            try:
                with open(compose_file, 'r') as f:
                    content = f.read()

                # Check for volume mounts that should exist
                volume_paths = re.findall(r'\./([^:]+):', content)
                for vol_path in volume_paths:
                    full_path = self.project_root / vol_path
                    if not full_path.exists() and "logs" not in vol_path:
                        self.warnings.append(f"⚠️ Volume mount path {vol_path} doesn't exist")

            except Exception as e:
                self.issues.append(f"❌ Error checking docker-compose volumes: {str(e)}")

    def validate_directory_structure(self):
        """Validate expected directory structure"""
        logger.info("Validating directory structure...")

        required_dirs = ["client", "scripts"]
        optional_dirs = ["logs", "monitoring", "nginx"]

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                self.issues.append(f"❌ Required directory '{dir_name}' is missing")

        for dir_name in optional_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                self.warnings.append(f"⚠️ Optional directory '{dir_name}' is missing")

    def validate_required_scripts(self):
        """Validate required scripts exist"""
        logger.info("Validating required scripts...")

        scripts_dir = self.project_root / "scripts"
        if scripts_dir.exists():
            required_scripts = ["init-mongo.js"]
            for script in required_scripts:
                script_path = scripts_dir / script
                if not script_path.exists():
                    self.issues.append(f"❌ Required script '{script}' is missing")

    def validate_security_config(self):
        """Validate security-related configuration"""
        logger.info("Validating security configuration...")

        # Check for sensitive data in config files
        sensitive_patterns = [
            r'password\s*[:=]\s*["\']?[^"\'\s]+',
            r'secret\s*[:=]\s*["\']?[^"\'\s]+',
            r'key\s*[:=]\s*["\']?[^"\'\s]+',
        ]

        for pattern in sensitive_patterns:
            # Check .env.example for real secrets
            env_example = self.project_root / ".env.example"
            if env_example.exists():
                try:
                    with open(env_example, 'r') as f:
                        content = f.read()

                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if "your_" not in match and "changeme" not in match:
                            self.warnings.append(f"⚠️ Possible real secret in .env.example: {match[:20]}...")

                except Exception:
                    pass

    def report_results(self) -> bool:
        """Report validation results"""
        print("\n" + "="*60)
        print("🔧 CONFIGURATION VALIDATION REPORT")
        print("="*60)

        if not self.issues and not self.warnings:
            print("✅ All configurations are valid!")
            print("✅ No issues found")
            return True

        if self.issues:
            print(f"\n🚨 CRITICAL ISSUES ({len(self.issues)}):")
            for issue in self.issues:
                print(f"   {issue}")

        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   {warning}")

        print(f"\n📊 SUMMARY:")
        print(f"   Critical Issues: {len(self.issues)}")
        print(f"   Warnings: {len(self.warnings)}")

        if self.issues:
            print("\n❌ Configuration validation FAILED")
            print("   Fix critical issues before deploying")
            return False
        else:
            print("\n✅ Configuration validation PASSED")
            print("   Address warnings when possible")
            return True

def main():
    """Main validation function"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    validator = ConfigValidator(project_root)
    success = validator.validate_all()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()