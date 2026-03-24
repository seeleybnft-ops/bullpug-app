"""Pydantic models for the AI Trading Bot."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field


# Position Limits (in SOL)
MIN_POSITION_SOL = 0.05
MAX_POSITION_SOL = 1.0


class TraderSettings(BaseModel):
    """User trading bot settings"""
    wallet_address: str
    enabled: bool = False
    risk_level: str = Field(default="safer", pattern="^(safer|high_risk|both)$")
    max_position_sol: float = Field(default=0.5, ge=MIN_POSITION_SOL, le=MAX_POSITION_SOL)
    min_position_sol: float = Field(default=MIN_POSITION_SOL, ge=MIN_POSITION_SOL)
    stop_loss_percent: float = Field(default=10.0, ge=1.0, le=50.0)
    take_profit_percent: float = Field(default=20.0, ge=5.0, le=200.0)
    max_daily_trades: int = Field(default=5, ge=1, le=20)
    auto_approve: bool = False
    # Auto-Trade Settings
    auto_trade_enabled: bool = False
    auto_trade_mode: str = Field(default="conservative", pattern="^(conservative|moderate|aggressive)$")
    auto_min_confidence: float = Field(default=0.65, ge=0.5, le=0.95)
    auto_max_daily_trades: int = Field(default=3, ge=1, le=10)
    auto_max_position_sol: float = Field(default=0.2, ge=0.01, le=1.0)
    auto_cooldown_minutes: int = Field(default=30, ge=5, le=120)
    auto_require_multiple_signals: bool = True
    auto_pause_on_loss: bool = True
    auto_total_daily_limit_sol: float = Field(default=1.0, ge=0.1, le=5.0)
    auto_stop_loss_percent: float = Field(default=10.0, ge=2.0, le=50.0)
    auto_take_profit_percent: float = Field(default=20.0, ge=5.0, le=200.0)
    # Trailing Stop Settings
    auto_trailing_stop_enabled: bool = False
    auto_trailing_stop_percent: float = Field(default=5.0, ge=1.0, le=20.0)
    auto_scale_in_enabled: bool = False
    auto_scale_in_threshold: float = Field(default=5.0, ge=2.0, le=15.0)
    auto_scale_in_max_adds: int = Field(default=2, ge=1, le=5)
    auto_avoid_volatile_hours: bool = True
    auto_profit_target_alert: bool = True
    # A-TIER: Trading Mode
    trading_mode: str = Field(default="normal", pattern="^(conservative|normal|aggressive|sniper)$")
    # A-TIER: Conviction-Based Position Sizing
    conviction_sizing_enabled: bool = True
    # A-TIER: Multi-Timeframe Confirmation
    multi_timeframe_enabled: bool = True
    # A-TIER: DCA Exit Strategy
    dca_exit_enabled: bool = False
    dca_tp1_percent: float = Field(default=15.0, ge=5.0, le=100.0)
    dca_tp2_percent: float = Field(default=30.0, ge=10.0, le=200.0)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AutoTradeLog(BaseModel):
    """Log entry for auto-executed trades"""
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    wallet_address: str
    token_symbol: str
    token_mint: str
    action: str
    amount_sol: Optional[float] = None
    entry_price: Optional[float] = None
    confidence: float
    strategy: str
    reason: str
    success: bool
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TradeSignal(BaseModel):
    """AI-generated trade signal"""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    wallet_address: str
    token_symbol: str
    token_mint: str
    signal_type: str
    entry_price: float
    suggested_position_sol: float
    stop_loss_price: float
    take_profit_price: float
    confidence: float = Field(ge=0.0, le=1.0)
    strategy: str
    risk_category: str
    reasoning: str
    technical_indicators: Dict[str, Any]
    status: str = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = Field(default_factory=lambda: (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat())


class TradeExecution(BaseModel):
    """Executed trade record"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str
    wallet_address: str
    token_symbol: str
    token_mint: str
    trade_type: str
    amount_sol: float
    amount_tokens: Optional[float] = None
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss_price: float
    take_profit_price: float
    status: str = "open"
    pnl_sol: Optional[float] = None
    pnl_percent: Optional[float] = None
    tx_signature: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    closed_at: Optional[str] = None


class ApproveSignalRequest(BaseModel):
    """Request to approve a trade signal"""
    signal_id: str
    wallet_address: str
    position_sol: Optional[float] = None
    stop_loss_percent: Optional[float] = None
