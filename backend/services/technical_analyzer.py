"""
Technical Analysis Service

Technical analysis engine for generating trade signals.
Includes RSI, MACD, Bollinger Bands, and Moving Averages.
"""

import numpy as np
from typing import Dict, List, Any


class TechnicalAnalyzer:
    """Technical analysis engine for generating trade signals"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    @staticmethod
    def calculate_macd(prices: List[float]) -> Dict[str, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < 26:
            return {"macd": 0, "signal": 0, "histogram": 0}
        
        prices_arr = np.array(prices)
        
        # Calculate MACD line series (EMA12 - EMA26) for entire history
        ema_12_series = TechnicalAnalyzer._ema_series(prices_arr, 12)
        ema_26_series = TechnicalAnalyzer._ema_series(prices_arr, 26)
        
        macd_series = ema_12_series - ema_26_series
        
        # Signal line is 9-period EMA of MACD line
        signal_series = TechnicalAnalyzer._ema_series(macd_series, 9)
        
        # Get latest values
        macd_line = macd_series[-1]
        signal_line = signal_series[-1]
        histogram = macd_line - signal_line
        
        return {
            "macd": round(macd_line, 6),
            "signal": round(signal_line, 6),
            "histogram": round(histogram, 6)
        }
    
    @staticmethod
    def _ema_series(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA series for entire price history"""
        if len(prices) < period:
            return np.full(len(prices), np.mean(prices))
        
        multiplier = 2 / (period + 1)
        ema_values = np.zeros(len(prices))
        ema_values[0] = prices[0]
        
        for i in range(1, len(prices)):
            ema_values[i] = (prices[i] - ema_values[i-1]) * multiplier + ema_values[i-1]
        
        return ema_values
    
    @staticmethod
    def _ema(prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return float(np.mean(prices))
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            current_price = prices[-1] if prices else 0
            return {"upper": current_price, "middle": current_price, "lower": current_price, "position": 0.5}
        
        prices_arr = np.array(prices[-period:])
        middle = np.mean(prices_arr)
        std = np.std(prices_arr)
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        current_price = prices[-1]
        band_width = upper - lower
        position = (current_price - lower) / band_width if band_width > 0 else 0.5
        
        return {
            "upper": round(upper, 6),
            "middle": round(middle, 6),
            "lower": round(lower, 6),
            "position": round(position, 4)  # 0 = at lower band, 1 = at upper band
        }
    
    @staticmethod
    def calculate_moving_averages(prices: List[float]) -> Dict[str, float]:
        """Calculate various moving averages"""
        result = {}
        
        for period in [7, 14, 21, 50]:
            if len(prices) >= period:
                result[f"sma_{period}"] = round(np.mean(prices[-period:]), 6)
            else:
                result[f"sma_{period}"] = round(np.mean(prices), 6) if prices else 0
        
        return result
    
    @staticmethod
    def analyze(prices: List[float], current_price: float) -> Dict[str, Any]:
        """Run full technical analysis"""
        rsi = TechnicalAnalyzer.calculate_rsi(prices)
        macd = TechnicalAnalyzer.calculate_macd(prices)
        bollinger = TechnicalAnalyzer.calculate_bollinger_bands(prices)
        mas = TechnicalAnalyzer.calculate_moving_averages(prices)
        
        # Trend determination
        if len(prices) >= 14:
            short_trend = prices[-1] > np.mean(prices[-7:])
            long_trend = prices[-1] > np.mean(prices[-14:])
        else:
            short_trend = True
            long_trend = True
        
        return {
            "rsi": rsi,
            "macd": macd,
            "bollinger": bollinger,
            "moving_averages": mas,
            "current_price": current_price,
            "short_trend": "bullish" if short_trend else "bearish",
            "long_trend": "bullish" if long_trend else "bearish"
        }
