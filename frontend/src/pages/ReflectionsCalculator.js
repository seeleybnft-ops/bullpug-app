import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import { Coins, TrendingUp, Calendar, DollarSign, Percent, Sparkles, RefreshCw, Info, ExternalLink } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Blowfish fee structure constants
const BLOWFISH_FEE_STRUCTURE = {
  tradingFeePercent: 1.0,     // 1% trading fee on buys/sells
  creatorSharePercent: 80,    // 80% of fees go to token creator/holders
  platformSharePercent: 20,   // 20% goes to Blowfish platform
};

export default function ReflectionsCalculator() {
  const [holdings, setHoldings] = useState("10000000");
  const [volume, setVolume] = useState([89000]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const calculate = async () => {
    if (!holdings || parseFloat(holdings) <= 0) {
      return toast.error("Enter valid token holdings");
    }
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/reflections/calculate`, {
        token_holdings: parseFloat(holdings),
        volume_24h: volume[0],
        reflection_rate: BLOWFISH_FEE_STRUCTURE.tradingFeePercent * (BLOWFISH_FEE_STRUCTURE.creatorSharePercent / 100),
      });
      setResults(data);
      toast.success("Reflections calculated!");
    } catch (e) {
      toast.error("Calculation failed");
    }
    setLoading(false);
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(2)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(2)}K`;
    return num.toLocaleString();
  };

  // Calculate effective reflection rate (1% fee × 80% to holders = 0.8%)
  const effectiveReflectionRate = BLOWFISH_FEE_STRUCTURE.tradingFeePercent * (BLOWFISH_FEE_STRUCTURE.creatorSharePercent / 100);

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-5xl mx-auto px-6 md:px-12">
        <div className="text-center mb-10">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase mb-3" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            Reflections <span className="text-[#D946EF]">Calculator</span>
          </h1>
          <p className="text-slate-500 text-sm">Calculate your passive income from Blowfish trading fees</p>
          <div className="flex items-center justify-center gap-2 mt-3">
            <Badge className="bg-[#D946EF]/10 text-[#D946EF] border-[#D946EF]/30 text-[10px]">
              {BLOWFISH_FEE_STRUCTURE.creatorSharePercent}% Fee Share
            </Badge>
            <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] border-[#00FFA3]/30 text-[10px]">
              Powered by Blowfish
            </Badge>
          </div>
        </div>

        {/* Blowfish Fee Structure Info */}
        <div className="glass-card rounded-2xl p-4 mb-6 border border-[#00FFA3]/20">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-[#00FFA3]/10 flex items-center justify-center flex-shrink-0">
              <Info className="w-5 h-5 text-[#00FFA3]" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white mb-1">Blowfish Fee Distribution</h3>
              <p className="text-xs text-slate-400 mb-2">
                $BULLPUG is deployed via Blowfish with automatic fee distribution. Every trade generates fees that are distributed to token holders.
              </p>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-2 rounded-lg bg-white/5">
                  <p className="text-lg font-bold text-[#D946EF]">{BLOWFISH_FEE_STRUCTURE.tradingFeePercent}%</p>
                  <p className="text-[10px] text-slate-500">Trading Fee</p>
                </div>
                <div className="p-2 rounded-lg bg-white/5">
                  <p className="text-lg font-bold text-[#00FFA3]">{BLOWFISH_FEE_STRUCTURE.creatorSharePercent}%</p>
                  <p className="text-[10px] text-slate-500">To Holders</p>
                </div>
                <div className="p-2 rounded-lg bg-white/5">
                  <p className="text-lg font-bold text-slate-400">{BLOWFISH_FEE_STRUCTURE.platformSharePercent}%</p>
                  <p className="text-[10px] text-slate-500">To Blowfish</p>
                </div>
              </div>
              <a 
                href="https://blowfish.neuko.ai/" 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-[#00FFA3] hover:underline mt-2"
              >
                Learn more about Blowfish <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Calculator Controls */}
          <div className="glass-card rounded-2xl p-6 space-y-5">
            <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              <Coins className="w-4 h-4 text-[#D946EF]" /> Your Holdings
            </h3>
            
            <div>
              <label className="text-xs text-slate-500 uppercase mb-1 block">$BULLPUG Tokens</label>
              <Input 
                type="number" 
                value={holdings} 
                onChange={e => setHoldings(e.target.value)}
                data-testid="holdings-input"
                placeholder="10,000,000"
                className="bg-black/50 border-white/10 text-white text-lg font-bold"
              />
              <div className="flex gap-2 mt-2">
                {["1M", "10M", "50M", "100M"].map(amt => (
                  <button
                    key={amt}
                    onClick={() => setHoldings(amt.replace("M", "000000"))}
                    className="text-[10px] px-2 py-1 rounded bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
                  >
                    {amt}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-500 mb-1">
                <span>24h Trading Volume (USD)</span>
                <span className="text-[#00FFA3] font-bold">${formatNumber(volume[0])}</span>
              </div>
              <Slider 
                value={volume} 
                onValueChange={setVolume} 
                min={10000} 
                max={1000000} 
                step={5000}
                data-testid="volume-slider"
              />
              <p className="text-[10px] text-slate-600 mt-1">Adjust based on market activity</p>
            </div>

            <div className="p-3 rounded-lg bg-[#D946EF]/10 border border-[#D946EF]/30">
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-400">Effective Reflection Rate</span>
                <span className="text-sm font-bold text-[#D946EF]">{effectiveReflectionRate}%</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                {BLOWFISH_FEE_STRUCTURE.tradingFeePercent}% fee × {BLOWFISH_FEE_STRUCTURE.creatorSharePercent}% to holders
              </p>
            </div>

            <Button 
              onClick={calculate} 
              disabled={loading}
              data-testid="calculate-btn"
              className="w-full bg-[#D946EF] text-white font-bold rounded-xl py-5 text-sm uppercase hover:scale-[1.02] transition-transform shadow-[0_0_20px_rgba(217,70,239,0.3)]"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              {loading ? "Calculating..." : "Calculate Reflections"}
            </Button>

            {/* Info Card */}
            <div className="p-4 rounded-xl border border-[#D946EF]/20 bg-[#D946EF]/5">
              <h4 className="text-xs font-bold text-[#D946EF] mb-2 flex items-center gap-1">
                <Sparkles size={12} /> How Reflections Work
              </h4>
              <p className="text-[10px] text-slate-400 leading-relaxed">
                Every $BULLPUG transaction has a 2% reflection fee that gets automatically redistributed to all holders. 
                The more tokens you hold, the larger your share of reflections!
              </p>
            </div>
          </div>

          {/* Results */}
          <div className="lg:col-span-2 space-y-6">
            {results ? (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="glass-card rounded-xl p-4 text-center">
                    <Percent className="w-5 h-5 mx-auto mb-2 text-[#D946EF]" />
                    <p className="text-xl font-black text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                      {results.holder_share_percent}%
                    </p>
                    <p className="text-[10px] text-slate-500 uppercase">Your Share</p>
                  </div>
                  <div className="glass-card rounded-xl p-4 text-center">
                    <TrendingUp className="w-5 h-5 mx-auto mb-2 text-[#00FFA3]" />
                    <p className="text-xl font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                      {results.estimated_apy}%
                    </p>
                    <p className="text-[10px] text-slate-500 uppercase">Est. APY</p>
                  </div>
                  <div className="glass-card rounded-xl p-4 text-center">
                    <DollarSign className="w-5 h-5 mx-auto mb-2 text-[#F5D300]" />
                    <p className="text-xl font-black text-[#F5D300]" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                      ${results.price_usd}
                    </p>
                    <p className="text-[10px] text-slate-500 uppercase">Token Price</p>
                  </div>
                  <div className="glass-card rounded-xl p-4 text-center">
                    <Coins className="w-5 h-5 mx-auto mb-2 text-[#00C2FF]" />
                    <p className="text-xl font-black text-[#00C2FF]" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                      {formatNumber(results.holdings)}
                    </p>
                    <p className="text-[10px] text-slate-500 uppercase">Holdings</p>
                  </div>
                </div>

                {/* Reflections Breakdown */}
                <div className="glass-card rounded-2xl p-6">
                  <h3 className="text-sm font-bold uppercase mb-5 flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                    <Calendar className="w-4 h-4 text-[#00FFA3]" /> Projected Reflections
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                      { period: "Daily", data: results.daily, icon: "24h", color: "#00FFA3" },
                      { period: "Weekly", data: results.weekly, icon: "7d", color: "#00C2FF" },
                      { period: "Monthly", data: results.monthly, icon: "30d", color: "#D946EF" },
                      { period: "Yearly", data: results.yearly, icon: "365d", color: "#F5D300" },
                    ].map(item => (
                      <div key={item.period} className="p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-xs text-slate-500 uppercase">{item.period}</span>
                          <Badge className="text-[9px]" style={{ backgroundColor: `${item.color}20`, color: item.color, borderColor: `${item.color}40` }}>
                            {item.icon}
                          </Badge>
                        </div>
                        <div className="flex items-end justify-between">
                          <div>
                            <p className="text-2xl font-black" style={{ color: item.color, fontFamily: 'Orbitron, sans-serif' }}>
                              ${item.data.usd.toLocaleString()}
                            </p>
                            <p className="text-xs text-slate-500">
                              +{formatNumber(item.data.tokens)} tokens
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Additional Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="glass-card rounded-xl p-5">
                    <h4 className="text-xs font-bold uppercase text-[#00FFA3] mb-3">Reflection Pool</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400">24h Volume</span>
                        <span className="text-white font-bold">${formatNumber(results.volume_24h)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400">Reflection Rate</span>
                        <span className="text-white font-bold">{results.reflection_rate}%</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400">Daily Pool</span>
                        <span className="text-[#00FFA3] font-bold">${formatNumber(results.volume_24h * results.reflection_rate / 100)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="glass-card rounded-xl p-5">
                    <h4 className="text-xs font-bold uppercase text-[#D946EF] mb-3">Your Position</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400">Holdings Value</span>
                        <span className="text-white font-bold">${(results.holdings * results.price_usd).toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400">Share of Supply</span>
                        <span className="text-white font-bold">{results.holder_share_percent}%</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-400">Passive APY</span>
                        <span className="text-[#D946EF] font-bold">{results.estimated_apy}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                <p className="text-[10px] text-slate-600 text-center">
                  * Projections based on current volume. Actual reflections vary with market activity.
                </p>
              </>
            ) : (
              <div className="glass-card rounded-2xl p-16 text-center">
                <Coins className="w-14 h-14 mx-auto mb-4 text-slate-700" />
                <p className="text-slate-500 text-sm mb-2">Enter your holdings to calculate reflections</p>
                <p className="text-slate-600 text-xs">See how much passive income you can earn from the 2% redistribution</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
