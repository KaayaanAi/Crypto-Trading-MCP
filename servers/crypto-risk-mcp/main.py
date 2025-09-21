#!/usr/bin/env python3
"""
Crypto Risk Management MCP Server

Provides comprehensive risk management for crypto trading including:
- Position sizing calculations
- Portfolio risk assessment
- Value at Risk (VaR) calculations
- Drawdown monitoring
- Risk alerts and notifications
- Correlation analysis
- Kelly Criterion optimization
"""

import asyncio
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from dataclasses import dataclass
import math

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from shared_types import RiskMetrics, RiskAlert, RiskAnalysis, PositionSize
from utils import setup_logger, safe_float, utc_now, cache, calculate_pnl, calculate_sharpe_ratio
from constants import RiskManagement
from exceptions import (
    RiskManagementError, PositionSizingError, RiskLimitExceededError,
    ValidationError, handle_error, validate_required_params, validate_numeric_range,
    safe_execute
)


# Initialize server and logger
server = Server("crypto-risk-mcp")
logger = setup_logger("crypto-risk-mcp", log_file="logs/risk_server.log")


@dataclass
class PortfolioPosition:
    """Portfolio position data"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    weight: float  # Portfolio weight


@dataclass
class RiskParameters:
    """Risk management parameters"""
    max_position_size: float = RiskManagement.MAX_POSITION_SIZE
    max_portfolio_risk: float = RiskManagement.MAX_PORTFOLIO_RISK
    max_drawdown: float = RiskManagement.MAX_DRAWDOWN
    max_correlation: float = RiskManagement.MAX_CORRELATION
    stop_loss_percent: float = RiskManagement.STOP_LOSS_PERCENT
    take_profit_ratio: float = RiskManagement.TAKE_PROFIT_RATIO


class RiskCalculator:
    """Risk management calculations and analysis"""

    def __init__(self):
        self.risk_free_rate = RiskManagement.RISK_FREE_RATE

    def calculate_position_size(
        self,
        account_balance: float,
        risk_per_trade: float,
        entry_price: float,
        stop_loss_price: float,
        method: str = "fixed_percent"
    ) -> PositionSize:
        """
        Calculate optimal position size based on risk management rules

        Args:
            account_balance: Total account balance
            risk_per_trade: Risk percentage per trade (e.g., 0.02 for 2%)
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price
            method: Position sizing method (fixed_percent, kelly, volatility)

        Returns:
            PositionSize object with calculated values

        Raises:
            PositionSizingError: If calculation fails due to invalid inputs
        """
        # Validate inputs
        validate_numeric_range(account_balance, min_value=0.01, field_name="account_balance")
        validate_numeric_range(risk_per_trade, min_value=0.001, max_value=0.5, field_name="risk_per_trade")
        validate_numeric_range(entry_price, min_value=0.01, field_name="entry_price")
        validate_numeric_range(stop_loss_price, min_value=0.01, field_name="stop_loss_price")

        if method not in ["fixed_percent", "kelly", "volatility"]:
            raise ValidationError(
                f"Invalid position sizing method: {method}",
                field="method",
                value=method,
                details={"valid_methods": ["fixed_percent", "kelly", "volatility"]}
            )

        try:
            risk_amount = account_balance * risk_per_trade
            price_risk = abs(entry_price - stop_loss_price)

            if price_risk <= 0:
                raise PositionSizingError(
                    "Price risk must be greater than zero (entry price cannot equal stop loss price)",
                    details={
                        "entry_price": entry_price,
                        "stop_loss_price": stop_loss_price,
                        "price_risk": price_risk
                    }
                )

            if method == "fixed_percent":
                # Simple fixed percentage risk
                quantity = risk_amount / price_risk
                confidence = 0.8

            elif method == "kelly":
                # Kelly Criterion (simplified)
                # Assumes default win rate and 1:2 risk/reward
                win_rate = RiskManagement.DEFAULT_WIN_RATE
                avg_win = price_risk * 2  # 1:2 risk/reward
                avg_loss = price_risk

                # Protection against division by zero
                if avg_win <= 0:
                    raise PositionSizingError(
                        "Invalid Kelly calculation: average win must be greater than zero",
                        details={"avg_win": avg_win, "price_risk": price_risk}
                    )

                kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
                kelly_fraction = max(0, min(kelly_fraction, RiskManagement.MAX_KELLY_FRACTION))

                kelly_risk_amount = account_balance * kelly_fraction
                quantity = kelly_risk_amount / price_risk
                confidence = 0.9

            elif method == "volatility":
                # Volatility-adjusted position sizing (simplified)
                # Assumes we have some volatility measure
                volatility_factor = 0.8  # Could be calculated from historical data
                adjusted_risk = risk_amount * (1 / volatility_factor)
                quantity = adjusted_risk / price_risk
                confidence = 0.7

            else:
                # Default to fixed percent
                quantity = risk_amount / price_risk
                confidence = 0.6

            notional_value = quantity * entry_price
            max_position_value = account_balance * RiskManagement.MAX_POSITION_SIZE

            # Cap position size if it exceeds maximum
            if notional_value > max_position_value:
                logger.warning(
                    f"Position size capped: {notional_value:.2f} -> {max_position_value:.2f}"
                )
                quantity = max_position_value / entry_price
                notional_value = max_position_value
                confidence *= 0.8  # Reduce confidence for capped positions

            return PositionSize(
                symbol="",
                quantity=round(quantity, 8),
                notional_value=round(notional_value, 2),
                risk_amount=round(risk_amount, 2),
                confidence=confidence
            )

        except (PositionSizingError, ValidationError):
            # Re-raise our custom errors
            raise
        except Exception as e:
            raise PositionSizingError(
                "Failed to calculate position size due to unexpected error",
                details={
                    "account_balance": account_balance,
                    "risk_per_trade": risk_per_trade,
                    "entry_price": entry_price,
                    "stop_loss_price": stop_loss_price,
                    "method": method
                },
                cause=e
            ) from e

    def calculate_portfolio_var(
        self,
        positions: List[PortfolioPosition],
        confidence_level: float = 0.05,
        time_horizon_days: int = 1
    ) -> float:
        """
        Calculate Value at Risk (VaR) for the portfolio

        Args:
            positions: List of portfolio positions
            confidence_level: Confidence level (0.05 for 95% VaR)
            time_horizon_days: Time horizon in days

        Returns:
            VaR value as a positive number (loss amount)
        """
        try:
            if not positions:
                return 0.0

            # Calculate portfolio weights and values
            total_value = sum(pos.market_value for pos in positions)
            if total_value <= 0:
                return 0.0

            weights = np.array([pos.market_value / total_value for pos in positions])

            # Simplified volatility assumptions (in practice, use historical data)
            # Crypto assets typically have high annual volatility
            volatilities = np.array([RiskManagement.CRYPTO_VOLATILITY_ASSUMPTION] * len(positions))

            # Simplified correlation matrix (in practice, calculate from historical data)
            n_assets = len(positions)
            correlation_matrix = np.full((n_assets, n_assets), RiskManagement.ASSET_CORRELATION_ASSUMPTION)
            np.fill_diagonal(correlation_matrix, 1.0)

            # Calculate portfolio variance
            covariance_matrix = np.outer(volatilities, volatilities) * correlation_matrix
            portfolio_variance = np.dot(weights, np.dot(covariance_matrix, weights))
            portfolio_volatility = np.sqrt(portfolio_variance)

            # Scale to time horizon
            horizon_volatility = portfolio_volatility * np.sqrt(time_horizon_days / 365)

            # Calculate VaR using normal distribution assumption
            from scipy import stats
            var_multiplier = stats.norm.ppf(1 - confidence_level)  # e.g., 1.645 for 95% VaR
            var_absolute = total_value * horizon_volatility * var_multiplier

            return var_absolute

        except Exception as e:
            raise RiskManagementError(
                "Failed to calculate portfolio VaR",
                details={"positions_count": len(positions), "confidence_level": confidence_level},
                cause=e
            ) from e

    def calculate_max_drawdown(self, pnl_history: List[float]) -> float:
        """Calculate maximum drawdown from P&L history"""
        try:
            if not pnl_history or len(pnl_history) < 2:
                return 0.0

            # Calculate cumulative P&L
            cumulative_pnl = np.cumsum(pnl_history)
            running_max = np.maximum.accumulate(cumulative_pnl)

            # Calculate drawdowns
            drawdowns = (cumulative_pnl - running_max) / np.maximum(running_max, 1)  # Avoid division by zero
            max_drawdown = abs(np.min(drawdowns))

            return max_drawdown

        except Exception as e:
            raise RiskManagementError(
                "Failed to calculate maximum drawdown",
                details={"pnl_history_length": len(pnl_history) if pnl_history else 0},
                cause=e
            ) from e

    def calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio from returns"""
        try:
            if not returns or len(returns) < 2:
                return 0.0

            mean_return = np.mean(returns)
            std_return = np.std(returns)

            if std_return == 0:
                return 0.0

            # Annualized Sharpe ratio
            sharpe_ratio = (mean_return - self.risk_free_rate / 365) / std_return * np.sqrt(365)
            return sharpe_ratio

        except Exception as e:
            raise RiskManagementError(
                "Failed to calculate Sharpe ratio",
                details={"returns_length": len(returns) if returns else 0},
                cause=e
            ) from e

    def assess_correlation_risk(self, positions: List[PortfolioPosition]) -> Dict[str, float]:
        """Assess correlation risk between positions"""
        try:
            if len(positions) < 2:
                return {"avg_correlation": 0.0, "max_correlation": 0.0, "risk_level": "low"}

            # Simplified correlation assessment
            # In practice, this would use historical price correlations
            n_positions = len(positions)

            # Crypto assets tend to be highly correlated
            # Assume higher correlation for similar asset types
            correlations = []

            for i in range(n_positions):
                for j in range(i + 1, n_positions):
                    # Simplified correlation based on asset types
                    symbol1 = positions[i].symbol
                    symbol2 = positions[j].symbol

                    if "BTC" in symbol1 and "BTC" in symbol2:
                        correlation = 0.95
                    elif ("BTC" in symbol1 or "ETH" in symbol1) and ("BTC" in symbol2 or "ETH" in symbol2):
                        correlation = 0.85
                    elif symbol1.endswith("USDT") and symbol2.endswith("USDT"):
                        correlation = 0.70  # Different altcoins
                    else:
                        correlation = 0.60  # Default correlation

                    correlations.append(correlation)

            avg_correlation = np.mean(correlations) if correlations else 0.0
            max_correlation = np.max(correlations) if correlations else 0.0

            # Assess risk level
            if max_correlation > 0.8:
                risk_level = "high"
            elif max_correlation > 0.6:
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                "avg_correlation": avg_correlation,
                "max_correlation": max_correlation,
                "risk_level": risk_level
            }

        except Exception as e:
            raise RiskManagementError(
                "Failed to assess correlation risk",
                details={"positions_count": len(positions)},
                cause=e
            ) from e

    def generate_risk_alerts(
        self,
        portfolio_metrics: RiskMetrics,
        risk_params: RiskParameters
    ) -> List[RiskAlert]:
        """Generate risk alerts based on current metrics"""
        alerts = []

        try:
            # VaR alert
            if portfolio_metrics.var_1d > risk_params.max_portfolio_risk * RiskManagement.DEMO_ACCOUNT_BALANCE:
                alerts.append(RiskAlert(
                    level="warning",
                    message=f"Portfolio VaR (${portfolio_metrics.var_1d:,.2f}) exceeds risk threshold",
                    metric="var_1d",
                    current_value=portfolio_metrics.var_1d,
                    threshold=risk_params.max_portfolio_risk * RiskManagement.DEMO_ACCOUNT_BALANCE
                ))

            # Drawdown alert
            if portfolio_metrics.max_drawdown > risk_params.max_drawdown:
                alerts.append(RiskAlert(
                    level="critical",
                    message=f"Maximum drawdown ({portfolio_metrics.max_drawdown:.1%}) exceeds limit ({risk_params.max_drawdown:.1%})",
                    metric="max_drawdown",
                    current_value=portfolio_metrics.max_drawdown,
                    threshold=risk_params.max_drawdown
                ))

            # Correlation alert
            if portfolio_metrics.correlation_risk == "high":
                alerts.append(RiskAlert(
                    level="warning",
                    message="High correlation detected between positions - consider diversification",
                    metric="correlation_risk",
                    current_value=RiskManagement.HIGH_CORRELATION_THRESHOLD,  # Approximate value for high correlation
                    threshold=risk_params.max_correlation
                ))

            # Sharpe ratio alert
            if portfolio_metrics.sharpe_ratio is not None and portfolio_metrics.sharpe_ratio < 0.5:
                alerts.append(RiskAlert(
                    level="warning",
                    message=f"Low Sharpe ratio ({portfolio_metrics.sharpe_ratio:.2f}) indicates poor risk-adjusted returns",
                    metric="sharpe_ratio",
                    current_value=portfolio_metrics.sharpe_ratio,
                    threshold=0.5
                ))

        except Exception as e:
            raise RiskManagementError(
                "Failed to generate risk alerts",
                details={"portfolio_metrics": str(portfolio_metrics)},
                cause=e
            ) from e

        return alerts


# MCP Server Tools
@server.call_tool()
async def calculate_position_size(
    account_balance: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float,
    method: str = "fixed_percent"
) -> Dict[str, Any]:
    """
    Calculate optimal position size based on risk management

    Args:
        account_balance: Total account balance in USD
        risk_per_trade: Risk per trade as decimal (e.g., 0.02 for 2%)
        entry_price: Planned entry price
        stop_loss_price: Planned stop loss price
        method: Position sizing method (fixed_percent, kelly, volatility)

    Returns:
        Dict containing position size calculation
    """
    try:
        logger.info(f"Calculating position size - Balance: ${account_balance}, Risk: {risk_per_trade:.2%}")

        calculator = RiskCalculator()
        position_size = calculator.calculate_position_size(
            account_balance=account_balance,
            risk_per_trade=risk_per_trade,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            method=method
        )

        # Calculate additional metrics
        price_risk = abs(entry_price - stop_loss_price)
        position_value_percent = (position_size.notional_value / account_balance) * 100

        return {
            "success": True,
            "position_size": {
                "quantity": position_size.quantity,
                "notional_value": position_size.notional_value,
                "risk_amount": position_size.risk_amount,
                "confidence": position_size.confidence
            },
            "risk_metrics": {
                "risk_per_trade_percent": risk_per_trade * 100,
                "position_value_percent": position_value_percent,
                "price_risk": price_risk,
                "max_loss": position_size.risk_amount
            },
            "method": method,
            "timestamp": utc_now().isoformat()
        }

    except Exception as e:
        return handle_error(e, context="calculate_position_size", reraise=False)


@server.call_tool()
async def assess_portfolio_risk(
    positions: List[Dict[str, Any]],
    account_balance: float,
    pnl_history: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Assess overall portfolio risk metrics

    Args:
        positions: List of current positions
        account_balance: Total account balance
        pnl_history: Historical P&L data for drawdown calculation

    Returns:
        Dict containing comprehensive risk assessment
    """
    try:
        logger.info(f"Assessing portfolio risk for {len(positions)} positions")

        calculator = RiskCalculator()

        # Convert positions to PortfolioPosition objects
        portfolio_positions = []
        total_value = account_balance

        for pos_data in positions:
            try:
                position = PortfolioPosition(
                    symbol=pos_data["symbol"],
                    quantity=safe_float(pos_data["quantity"]),
                    entry_price=safe_float(pos_data["entry_price"]),
                    current_price=safe_float(pos_data["current_price"]),
                    market_value=safe_float(pos_data.get("market_value", 0)),
                    unrealized_pnl=safe_float(pos_data.get("unrealized_pnl", 0)),
                    unrealized_pnl_percent=safe_float(pos_data.get("unrealized_pnl_percent", 0)),
                    weight=safe_float(pos_data.get("weight", 0))
                )
                portfolio_positions.append(position)
            except Exception as e:
                logger.error(f"Error processing position: {e}")
                continue

        # Calculate risk metrics
        var_1d = calculator.calculate_portfolio_var(portfolio_positions)
        correlation_analysis = calculator.assess_correlation_risk(portfolio_positions)

        # Calculate max drawdown if P&L history provided
        max_drawdown = 0.0
        sharpe_ratio = None
        if pnl_history and len(pnl_history) > 1:
            max_drawdown = calculator.calculate_max_drawdown(pnl_history)
            sharpe_ratio = calculator.calculate_sharpe_ratio(pnl_history)

        # Create risk metrics object
        portfolio_metrics = RiskMetrics(
            var_1d=var_1d,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            portfolio_beta=None,  # Would require market data
            correlation_risk=correlation_analysis["risk_level"]
        )

        # Generate risk alerts
        risk_params = RiskParameters()
        alerts = calculator.generate_risk_alerts(portfolio_metrics, risk_params)

        # Calculate portfolio concentration
        position_weights = [pos.weight for pos in portfolio_positions if pos.weight > 0]
        max_position_weight = max(position_weights) if position_weights else 0
        concentration_risk = "high" if max_position_weight > 0.3 else "medium" if max_position_weight > 0.2 else "low"

        return {
            "success": True,
            "portfolio_metrics": {
                "total_positions": len(portfolio_positions),
                "total_portfolio_value": total_value,
                "var_1d": var_1d,
                "var_1d_percent": (var_1d / total_value * 100) if total_value > 0 else 0,
                "max_drawdown": max_drawdown,
                "max_drawdown_percent": max_drawdown * 100,
                "sharpe_ratio": sharpe_ratio,
                "correlation_analysis": correlation_analysis,
                "concentration_risk": concentration_risk,
                "max_position_weight": max_position_weight
            },
            "risk_alerts": [
                {
                    "level": alert.level,
                    "message": alert.message,
                    "metric": alert.metric,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold
                }
                for alert in alerts
            ],
            "recommendations": [
                "Diversify positions to reduce correlation risk" if correlation_analysis["risk_level"] == "high" else None,
                "Reduce position sizes to lower VaR" if var_1d > total_value * 0.05 else None,
                "Review stop-loss levels" if max_drawdown > 0.10 else None
            ],
            "timestamp": utc_now().isoformat()
        }

    except Exception as e:
        return handle_error(e, context="assess_portfolio_risk", reraise=False)


@server.call_tool()
async def generate_risk_alerts(
    current_drawdown: float,
    daily_pnl: float,
    var_breaches: int = 0,
    correlation_level: str = "medium"
) -> Dict[str, Any]:
    """
    Generate risk alerts based on current portfolio status

    Args:
        current_drawdown: Current drawdown as decimal (e.g., 0.05 for 5%)
        daily_pnl: Today's P&L in USD
        var_breaches: Number of recent VaR breaches
        correlation_level: Portfolio correlation level (low, medium, high)

    Returns:
        Dict containing risk alerts and recommendations
    """
    try:
        logger.info("Generating risk alerts")

        calculator = RiskCalculator()
        alerts = []
        recommendations = []

        # Drawdown alerts
        if current_drawdown > RiskManagement.CRITICAL_DRAWDOWN_THRESHOLD:
            alerts.append({
                "level": "critical",
                "message": f"Critical drawdown level reached: {current_drawdown:.1%}",
                "metric": "drawdown",
                "action_required": "Consider reducing position sizes or stopping trading"
            })
        elif current_drawdown > RiskManagement.WARNING_DRAWDOWN_THRESHOLD:
            alerts.append({
                "level": "warning",
                "message": f"Elevated drawdown: {current_drawdown:.1%}",
                "metric": "drawdown",
                "action_required": "Monitor closely and review risk management"
            })

        # Daily P&L alerts
        if daily_pnl < -RiskManagement.SIGNIFICANT_DAILY_LOSS:
            alerts.append({
                "level": "warning",
                "message": f"Significant daily loss: ${daily_pnl:,.2f}",
                "metric": "daily_pnl",
                "action_required": "Review trading decisions and market conditions"
            })

        # VaR breach alerts
        if var_breaches > RiskManagement.VAR_BREACH_WARNING_THRESHOLD:
            alerts.append({
                "level": "warning",
                "message": f"Multiple VaR breaches detected: {var_breaches}",
                "metric": "var_breaches",
                "action_required": "Review risk model and position sizing"
            })

        # Correlation alerts
        if correlation_level == "high":
            alerts.append({
                "level": "warning",
                "message": "High correlation between positions detected",
                "metric": "correlation",
                "action_required": "Diversify portfolio to reduce systematic risk"
            })

        # Generate recommendations
        if current_drawdown > RiskManagement.ELEVATED_DRAWDOWN_THRESHOLD:
            recommendations.append("Reduce position sizes by 25-50%")
            recommendations.append("Tighten stop-loss levels")

        if correlation_level == "high":
            recommendations.append("Add uncorrelated assets to portfolio")
            recommendations.append("Consider market-neutral strategies")

        if var_breaches > 1:
            recommendations.append("Recalibrate risk model parameters")
            recommendations.append("Review historical volatility assumptions")

        # Risk score calculation
        risk_score = 0
        if current_drawdown > RiskManagement.STOP_LOSS_PERCENT:
            risk_score += 30
        if daily_pnl < -RiskManagement.MODERATE_DAILY_LOSS:
            risk_score += 20
        if var_breaches > 0:
            risk_score += 15
        if correlation_level == "high":
            risk_score += 20

        risk_level = "low" if risk_score < 25 else "medium" if risk_score < 60 else "high"

        return {
            "success": True,
            "risk_level": risk_level,
            "risk_score": min(100, risk_score),
            "alerts": alerts,
            "recommendations": [r for r in recommendations if r],
            "metrics_summary": {
                "current_drawdown": current_drawdown,
                "daily_pnl": daily_pnl,
                "var_breaches": var_breaches,
                "correlation_level": correlation_level
            },
            "timestamp": utc_now().isoformat()
        }

    except Exception as e:
        return handle_error(e, context="generate_risk_alerts", reraise=False)


@server.call_tool()
async def optimize_kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    max_kelly: float = 0.25
) -> Dict[str, Any]:
    """
    Calculate optimal position size using Kelly Criterion

    Args:
        win_rate: Win rate as decimal (e.g., 0.6 for 60%)
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount
        max_kelly: Maximum Kelly fraction to use (risk control)

    Returns:
        Dict containing Kelly Criterion calculation
    """
    try:
        logger.info(f"Optimizing Kelly Criterion - Win rate: {win_rate:.1%}")

        if win_rate <= 0 or win_rate >= 1:
            return {
                "success": False,
                "error": "Win rate must be between 0 and 1"
            }

        if avg_win <= 0 or avg_loss <= 0:
            return {
                "success": False,
                "error": "Average win and loss amounts must be positive"
            }

        # Kelly formula: f = (bp - q) / b
        # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
        b = avg_win / avg_loss  # Odds ratio
        p = win_rate
        q = 1 - win_rate

        kelly_fraction = (b * p - q) / b

        # Apply maximum Kelly limit for risk control
        optimal_kelly = max(0, min(kelly_fraction, max_kelly))

        # Calculate expected value
        expected_value = p * avg_win - q * avg_loss

        # Risk of ruin calculation (simplified)
        if kelly_fraction > 0:
            # Approximate risk of ruin for Kelly betting
            risk_of_ruin = (q / p) ** (1 / kelly_fraction) if kelly_fraction < 1 else 1.0
        else:
            risk_of_ruin = 1.0

        return {
            "success": True,
            "kelly_calculation": {
                "raw_kelly_fraction": kelly_fraction,
                "optimal_kelly_fraction": optimal_kelly,
                "recommended_position_size_percent": optimal_kelly * 100,
                "expected_value": expected_value,
                "odds_ratio": b,
                "risk_of_ruin": min(1.0, risk_of_ruin)
            },
            "inputs": {
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "max_kelly_limit": max_kelly
            },
            "interpretation": {
                "recommendation": "increase_size" if optimal_kelly > 0.05 else "decrease_size" if optimal_kelly < 0.02 else "maintain",
                "risk_level": "high" if optimal_kelly > 0.15 else "medium" if optimal_kelly > 0.05 else "low"
            },
            "timestamp": utc_now().isoformat()
        }

    except Exception as e:
        return handle_error(e, context="optimize_kelly_criterion", reraise=False)


async def main():
    """Main server entry point"""
    logger.info("Starting Crypto Risk Management MCP Server")

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    try:
        async with stdio_server() as streams:
            await server.run(
                streams[0], streams[1],
                server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())