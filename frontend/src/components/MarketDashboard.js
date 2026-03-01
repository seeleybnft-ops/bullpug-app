/**
 * MarketDashboard - Real-time market overview widget for homepage
 * Shows Fear & Greed Index, top movers, and market sentiment
 */

import { useState, useEffect } from 'react';
import { Activity, RefreshCw, AlertTriangle, Sparkles } from 'lucide-react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Fear & Greed gauge colors
const getFearGreedColor = (value) => {
  if (value <= 20) return '#FF3B30'; // Extreme Fear - Red
  if (value <= 40) return '#FF8C00'; // Fear - Orange
  if (value <= 60) return '#F5D300'; // Neutral - Yellow
  if (value <= 80) return '#4CD964'; // Greed - Light Green
  return '#00FFA3'; // Extreme Greed - Bright Green
};

// Fear & Greed gauge component
function FearGreedGauge({ value, classification }) {
  const color = getFearGreedColor(value);
  const rotation = (value / 100) * 180 - 90; // -90 to 90 degrees
  
  return (
    <div className="relative w-32 h-20 mx-auto">
      {/* Gauge background */}
      <svg className="w-full h-full" viewBox="0 0 100 60">
        {/* Background arc */}
        <path
          d="M 10 55 A 40 40 0 0 1 90 55"
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Gradient arc segments */}
        <path d="M 10 55 A 40 40 0 0 1 25 25" fill="none" stroke="#FF3B30" strokeWidth="8" strokeLinecap="round" />
        <path d="M 25 25 A 40 40 0 0 1 50 15" fill="none" stroke="#FF8C00" strokeWidth="8" strokeLinecap="round" />
        <path d="M 50 15 A 40 40 0 0 1 75 25" fill="none" stroke="#F5D300" strokeWidth="8" strokeLinecap="round" />
        <path d="M 75 25 A 40 40 0 0 1 90 55" fill="none" stroke="#00FFA3" strokeWidth="8" strokeLinecap="round" />
        
        {/* Needle */}
        <line
          x1="50"
          y1="55"
          x2="50"
          y2="25"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          transform={`rotate(${rotation}, 50, 55)`}
          style={{ filter: `drop-shadow(0 0 4px ${color})` }}
        />
        
        {/* Center dot */}
        <circle cx="50" cy="55" r="4" fill={color} style={{ filter: `drop-shadow(0 0 6px ${color})` }} />
      </svg>
      
      {/* Value display */}
      <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 text-center">
        <span className="text-2xl font-black" style={{ color, fontFamily: 'Orbitron' }}>{value}</span>
        <span className="text-xs text-slate-500">/100</span>
      </div>
    </div>
  );
}

// Top mover card
function MoverCard({ coin, isGainer }) {
  const changeColor = coin.change_24h >= 0 ? '#00FFA3' : '#FF3B30';
  
  return (
    <div className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
      <div className="flex items-center gap-2">
        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
          isGainer ? 'bg-[#00FFA3]/20 text-[#00FFA3]' : 'bg-[#FF3B30]/20 text-[#FF3B30]'
        }`}>
          {isGainer ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
        </div>
        <div>
          <p className="text-xs font-bold text-white">{coin.symbol}</p>
          <p className="text-[9px] text-slate-500">
            ${coin.price < 0.01 ? coin.price.toFixed(6) : coin.price.toFixed(4)}
          </p>
        </div>
      </div>
      <span className="text-xs font-bold" style={{ color: changeColor }}>
        {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h.toFixed(1)}%
      </span>
    </div>
  );
}

export default function MarketDashboard() {
  const [marketData, setMarketData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchMarketData = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/ai/market`);
      setMarketData(data);
      setLastUpdate(new Date());
    } catch (e) {
      console.error('Failed to fetch market data:', e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchMarketData();
    // Refresh every 5 minutes
    const interval = setInterval(fetchMarketData, 300000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !marketData) {
    return (
      <div className="glass-card rounded-2xl p-6 animate-pulse">
        <div className="h-40 bg-white/5 rounded-xl" />
      </div>
    );
  }

  const sentiment = marketData?.sentiment || { value: 50, classification: 'Neutral' };
  const solanaEco = marketData?.solana_ecosystem || {};
  const gainers = solanaEco.top_gainers || [];
  const topVolume = solanaEco.top_volume || [];

  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-white/5" data-testid="market-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/5 bg-gradient-to-r from-[#00FFA3]/5 to-[#D946EF]/5">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#00FFA3]" />
          <h3 className="text-sm font-bold uppercase" style={{ fontFamily: 'Orbitron' }}>Market Pulse</h3>
          <span className="px-1.5 py-0.5 bg-[#00FFA3]/20 text-[#00FFA3] text-[8px] rounded font-medium flex items-center gap-1">
            <span className="w-1 h-1 bg-[#00FFA3] rounded-full animate-pulse" />
            LIVE
          </span>
        </div>
        <button
          onClick={fetchMarketData}
          disabled={loading}
          className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="p-4">
        {/* Fear & Greed Index */}
        <div className="text-center mb-4">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Fear & Greed Index</p>
          <FearGreedGauge value={sentiment.value} classification={sentiment.classification} />
          <p className="text-sm font-bold mt-2" style={{ color: getFearGreedColor(sentiment.value) }}>
            {sentiment.classification}
          </p>
          {sentiment.value <= 25 && (
            <p className="text-[10px] text-slate-500 mt-1 flex items-center justify-center gap-1">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              Market in fear - potential buying opportunity
            </p>
          )}
          {sentiment.value >= 75 && (
            <p className="text-[10px] text-slate-500 mt-1 flex items-center justify-center gap-1">
              <Sparkles className="w-3 h-3 text-[#00FFA3]" />
              Market euphoric - consider taking profits
            </p>
          )}
        </div>

        {/* Last update */}
        {lastUpdate && (
          <p className="text-[9px] text-slate-600 text-center mt-3">
            Updated {lastUpdate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </p>
        )}
      </div>
    </div>
  );
}
