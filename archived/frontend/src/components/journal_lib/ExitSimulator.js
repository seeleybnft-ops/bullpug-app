/**
 * ExitSimulator Component - Monte Carlo simulations for exit strategies
 * Extracted from TradingJournal for better maintainability
 */

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Target, FileText, Calculator, ChevronDown, Activity } from "lucide-react";
import { Line as ChartLine, Bar as ChartBar } from "react-chartjs-2";
import AISuggestionBubble from "@/components/AISuggestionBubble";

export default function ExitSimulator({ 
  trades, tokenAmount, setTokenAmount, entryPrice, setEntryPrice,
  volatility, setVolatility, drift, setDrift, days, setDays,
  simulations, setSimulations, taxRate, setTaxRate,
  showTradeSelector, setShowTradeSelector, selectedTrade, selectTradeForSim,
  runSimulation, simLoading, simResults, simTab, setSimTab,
  pathsChart, histChart, simChartOpts, exportSimPDF, reportRef
}) {
  return (
    <div className="space-y-6" data-testid="exit-simulator">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Target className="w-5 h-5 text-[#D946EF]" />
            Exit Simulator
          </h3>
          <p className="text-xs text-slate-500 mt-1">Monte Carlo simulations for your exit strategy</p>
        </div>
        {simResults && (
          <Button onClick={exportSimPDF} variant="outline" className="border-white/20 text-slate-400 hover:text-white rounded-xl px-4 py-2 text-xs uppercase">
            <FileText className="w-3 h-3 mr-1" /> Export PDF
          </Button>
        )}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Input Panel */}
        <div className="glass-card rounded-2xl p-6 border border-white/5">
          <h4 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Calculator className="w-4 h-4 text-[#00FFA3]" /> Input Parameters
          </h4>
          
          {/* Quick Trade Selection */}
          {trades.length > 0 && (
            <div className="mb-6">
              <label className="block text-xs text-slate-500 mb-2">Load from Logged Trade</label>
              <div className="relative">
                <button
                  onClick={() => setShowTradeSelector(!showTradeSelector)}
                  className="w-full flex items-center justify-between p-3 bg-black/30 border border-white/10 rounded-xl text-sm text-white hover:border-[#D946EF]/50 transition-colors"
                  data-testid="trade-selector-btn"
                >
                  <span>{selectedTrade ? `${selectedTrade.asset} - $${selectedTrade.entry_price}` : "Select a trade..."}</span>
                  <ChevronDown className={`w-4 h-4 transition-transform ${showTradeSelector ? 'rotate-180' : ''}`} />
                </button>
                {showTradeSelector && (
                  <div className="absolute z-10 w-full mt-2 bg-[#0a0a12] border border-white/10 rounded-xl shadow-xl max-h-48 overflow-y-auto">
                    {trades.slice(0, 10).map((trade, i) => (
                      <button
                        key={i}
                        onClick={() => selectTradeForSim(trade)}
                        className="w-full flex items-center justify-between p-3 hover:bg-white/5 text-sm text-left border-b border-white/5 last:border-0"
                      >
                        <span className="text-white">{trade.asset}</span>
                        <span className="text-slate-400">${trade.entry_price}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1.5">Tokens</label>
                <Input value={tokenAmount} onChange={(e) => setTokenAmount(e.target.value)} type="number" className="bg-black/30 border-white/10 text-white h-10 rounded-lg text-sm" data-testid="mc-tokens" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1.5">Entry Price</label>
                <Input value={entryPrice} onChange={(e) => setEntryPrice(e.target.value)} type="number" step="0.000001" className="bg-black/30 border-white/10 text-white h-10 rounded-lg text-sm" data-testid="mc-entry" />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-slate-500">Volatility (σ)</span>
                <span className="text-[#00FFA3] font-mono">{volatility[0]}%</span>
              </div>
              <Slider value={volatility} onValueChange={setVolatility} min={10} max={200} step={5} data-testid="mc-vol" />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-slate-500">Drift (μ)</span>
                <span className="text-[#00C2FF] font-mono">{drift[0] > 0 ? '+' : ''}{drift[0]}%</span>
              </div>
              <Slider value={drift} onValueChange={setDrift} min={-50} max={200} step={5} data-testid="mc-drift" />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-slate-500">Days</span>
                <span className="text-white font-mono">{days[0]}</span>
              </div>
              <Slider value={days} onValueChange={setDays} min={7} max={365} step={1} data-testid="mc-days" />
            </div>

            <div>
              <div className="flex justify-between text-xs mb-2">
                <span className="text-slate-500">Simulations</span>
                <span className="text-white font-mono">{simulations[0].toLocaleString()}</span>
              </div>
              <Slider value={simulations} onValueChange={setSimulations} min={100} max={10000} step={100} data-testid="mc-sims" />
            </div>

            <div>
              <label className="block text-xs text-slate-500 mb-1.5">Tax Rate (%)</label>
              <Input value={taxRate} onChange={(e) => setTaxRate(e.target.value)} type="number" min="0" max="100" className="bg-black/30 border-white/10 text-white h-10 rounded-lg text-sm" data-testid="mc-tax" />
            </div>

            <Button onClick={runSimulation} disabled={simLoading} className="w-full bg-gradient-to-r from-[#D946EF] to-[#00C2FF] text-white font-bold py-5 rounded-xl uppercase text-sm" data-testid="run-sim-btn">
              {simLoading ? <Activity className="w-4 h-4 mr-2 animate-spin" /> : <Calculator className="w-4 h-4 mr-2" />}
              {simLoading ? "Simulating..." : "Run Simulation"}
            </Button>
          </div>
        </div>

        {/* Results Panel */}
        <div className="lg:col-span-2 space-y-6" ref={reportRef}>
          {!simResults ? (
            <div className="glass-card rounded-2xl p-16 text-center border border-white/5">
              <Target className="w-14 h-14 mx-auto mb-4 text-slate-700" />
              <p className="text-slate-500 text-sm">Configure parameters and run simulation</p>
              <p className="text-slate-600 text-xs mt-1">Monte Carlo GBM model will generate price paths</p>
            </div>
          ) : (
            <>
              {/* Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "Mean P&L", value: `$${simResults.mean_pnl.toLocaleString()}`, color: simResults.mean_pnl >= 0 ? "#00FFA3" : "#ff3b30" },
                  { label: "Median P&L", value: `$${simResults.median_pnl.toLocaleString()}`, color: simResults.median_pnl >= 0 ? "#00FFA3" : "#ff3b30" },
                  { label: "Profit Prob", value: `${simResults.prob_profit}%`, color: "#00C2FF" },
                  { label: "2x Prob", value: `${simResults.prob_2x}%`, color: "#D946EF" },
                ].map((s, i) => (
                  <div key={i} className="glass-card rounded-xl p-4 text-center border border-white/5">
                    <p className="text-[10px] text-slate-500 uppercase mb-1">{s.label}</p>
                    <p className="text-lg font-bold font-mono" style={{ color: s.color }}>{s.value}</p>
                  </div>
                ))}
              </div>

              {/* Charts */}
              <div className="glass-card rounded-2xl p-6 border border-white/5">
                <div className="flex gap-2 mb-4">
                  <button onClick={() => setSimTab("paths")} className={`px-4 py-2 rounded-lg text-xs font-bold uppercase ${simTab === "paths" ? "bg-[#00FFA3]/20 text-[#00FFA3]" : "text-slate-500"}`}>
                    Price Paths
                  </button>
                  <button onClick={() => setSimTab("hist")} className={`px-4 py-2 rounded-lg text-xs font-bold uppercase ${simTab === "hist" ? "bg-[#D946EF]/20 text-[#D946EF]" : "text-slate-500"}`}>
                    Distribution
                  </button>
                </div>
                <div className="h-[300px]">
                  {simTab === "paths" && pathsChart && <ChartLine data={pathsChart} options={simChartOpts} />}
                  {simTab === "hist" && histChart && <ChartBar data={histChart} options={simChartOpts} />}
                </div>
              </div>

              {/* Probability Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {[
                  { label: "5x", value: simResults.prob_5x, color: "#FFD700" },
                  { label: "10x", value: simResults.prob_10x, color: "#FF8C00" },
                  { label: ">50% Loss", value: simResults.prob_loss50, color: "#ff3b30" },
                  { label: "Best", value: `$${simResults.max_pnl.toLocaleString()}`, color: "#00FFA3", isValue: true },
                  { label: "Worst", value: `$${simResults.min_pnl.toLocaleString()}`, color: "#ff3b30", isValue: true },
                ].map((p, i) => (
                  <div key={i} className="glass-card rounded-xl p-3 text-center border border-white/5">
                    <p className="text-[9px] text-slate-500 uppercase mb-0.5">{p.label}</p>
                    <p className="text-sm font-bold font-mono" style={{ color: p.color }}>{p.isValue ? p.value : `${p.value}%`}</p>
                  </div>
                ))}
              </div>

              {/* AI Suggestion for Exit Sim */}
              <AISuggestionBubble context="exit_simulator" simulationResults={simResults} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
