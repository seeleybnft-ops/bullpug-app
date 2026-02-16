import { useState } from "react";
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip as ChartTooltip, Legend, Filler } from "chart.js";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import axios from "axios";
import { BarChart3, TrendingUp, TrendingDown, DollarSign, Calculator } from "lucide-react";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, ChartTooltip, Legend, Filler);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ExitSimulator() {
  const [tokenAmount, setTokenAmount] = useState("1000000");
  const [entryPrice, setEntryPrice] = useState("0.00042");
  const [exitPricesStr, setExitPricesStr] = useState("0.0005, 0.001, 0.005, 0.01, 0.05, 0.1");
  const [taxRate, setTaxRate] = useState("15");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const simulate = async () => {
    const exitPrices = exitPricesStr.split(",").map(s => parseFloat(s.trim())).filter(n => !isNaN(n));
    if (exitPrices.length === 0) return toast.error("Enter valid exit prices");
    if (!tokenAmount || !entryPrice) return toast.error("Fill all fields");
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/exit-simulator`, {
        token_amount: parseFloat(tokenAmount),
        entry_price: parseFloat(entryPrice),
        exit_prices: exitPrices,
        tax_rate: parseFloat(taxRate),
      });
      setResults(data);
    } catch (e) {
      toast.error("Simulation failed");
    }
    setLoading(false);
  };

  const chartData = results ? {
    labels: results.results.map(r => `$${r.exit_price}`),
    datasets: [
      {
        label: "Net P&L",
        data: results.results.map(r => r.net_pnl),
        borderColor: "#00FFA3",
        backgroundColor: "rgba(0,255,163,0.1)",
        fill: true,
        tension: 0.4,
        pointRadius: 6,
        pointBackgroundColor: results.results.map(r => r.net_pnl >= 0 ? "#00FFA3" : "#FF3B30"),
      },
      {
        label: "Gross P&L",
        data: results.results.map(r => r.pnl),
        borderColor: "#D946EF",
        backgroundColor: "rgba(217,70,239,0.05)",
        fill: true,
        tension: 0.4,
        borderDash: [5, 5],
        pointRadius: 4,
      },
    ],
  } : null;

  const chartOpts = {
    responsive: true,
    plugins: {
      legend: { labels: { color: "#94a3b8", font: { size: 11 } } },
      tooltip: { backgroundColor: "#13131F", borderColor: "rgba(255,255,255,0.1)", borderWidth: 1 },
    },
    scales: {
      x: { ticks: { color: "#64748b", font: { size: 10 } }, grid: { color: "rgba(255,255,255,0.03)" } },
      y: { ticks: { color: "#64748b", font: { size: 10 }, callback: v => `$${v.toLocaleString()}` }, grid: { color: "rgba(255,255,255,0.03)" } },
    },
  };

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-5xl mx-auto px-6 md:px-12">
        <div className="text-center mb-10">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase mb-3" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            Exit <span className="text-[#00C2FF]">Simulator</span>
          </h1>
          <p className="text-slate-500 text-sm">Plan your perfect exit strategy for $BULLPUG positions</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="glass-card rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              <Calculator className="w-4 h-4 text-[#00C2FF]" /> Parameters
            </h3>
            <div>
              <label className="text-xs text-slate-500 uppercase mb-1 block">Token Amount</label>
              <Input type="number" value={tokenAmount} onChange={e => setTokenAmount(e.target.value)}
                data-testid="token-amount-input" className="bg-black/50 border-white/10 text-white" />
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase mb-1 block">Entry Price ($)</label>
              <Input type="number" step="0.0001" value={entryPrice} onChange={e => setEntryPrice(e.target.value)}
                data-testid="entry-price-input" className="bg-black/50 border-white/10 text-white" />
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase mb-1 block">Exit Prices (comma-separated)</label>
              <Input value={exitPricesStr} onChange={e => setExitPricesStr(e.target.value)}
                data-testid="exit-prices-input" className="bg-black/50 border-white/10 text-white text-xs" />
            </div>
            <div>
              <label className="text-xs text-slate-500 uppercase mb-1 block">Tax Rate (%)</label>
              <Input type="number" value={taxRate} onChange={e => setTaxRate(e.target.value)}
                data-testid="tax-rate-input" className="bg-black/50 border-white/10 text-white" />
            </div>
            <Button onClick={simulate} disabled={loading} data-testid="simulate-btn"
              className="w-full bg-[#00C2FF] text-black font-bold rounded-xl py-5 text-sm uppercase hover:scale-[1.02] transition-transform">
              {loading ? "Simulating..." : "Simulate Exit"}
            </Button>
          </div>

          <div className="lg:col-span-2 space-y-6">
            {results && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <div className="glass-card rounded-xl p-4 text-center">
                    <DollarSign className="w-5 h-5 mx-auto mb-1 text-slate-400" />
                    <p className="text-xs text-slate-500">Investment</p>
                    <p className="text-lg font-black" style={{ fontFamily: 'Orbitron, sans-serif' }}>${results.investment.toLocaleString()}</p>
                  </div>
                  <div className="glass-card rounded-xl p-4 text-center">
                    <TrendingUp className="w-5 h-5 mx-auto mb-1 text-[#00FFA3]" />
                    <p className="text-xs text-slate-500">Best Exit</p>
                    <p className="text-lg font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>${results.optimal_exit.exit_price}</p>
                  </div>
                  <div className="glass-card rounded-xl p-4 text-center">
                    <BarChart3 className="w-5 h-5 mx-auto mb-1 text-[#F5D300]" />
                    <p className="text-xs text-slate-500">Max Net P&L</p>
                    <p className="text-lg font-black text-[#F5D300]" style={{ fontFamily: 'Orbitron, sans-serif' }}>${results.optimal_exit.net_pnl.toLocaleString()}</p>
                  </div>
                </div>

                <div className="glass-card rounded-2xl p-5">
                  <h3 className="text-sm font-bold uppercase mb-4" style={{ fontFamily: 'Orbitron, sans-serif' }}>P&L Chart</h3>
                  <Line data={chartData} options={chartOpts} />
                </div>

                <div className="glass-card rounded-2xl p-5">
                  <h3 className="text-sm font-bold uppercase mb-4" style={{ fontFamily: 'Orbitron, sans-serif' }}>Exit Scenarios</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-white/10 text-slate-500">
                          <th className="text-left py-2 px-2">Exit Price</th>
                          <th className="text-right py-2 px-2">Value</th>
                          <th className="text-right py-2 px-2">P&L</th>
                          <th className="text-right py-2 px-2">P&L %</th>
                          <th className="text-right py-2 px-2">Tax</th>
                          <th className="text-right py-2 px-2">Net P&L</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.results.map((r, i) => (
                          <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02]">
                            <td className="py-2 px-2 font-bold">${r.exit_price}</td>
                            <td className="py-2 px-2 text-right">${r.value.toLocaleString()}</td>
                            <td className={`py-2 px-2 text-right font-bold ${r.pnl >= 0 ? "text-[#00FFA3]" : "text-red-400"}`}>
                              {r.pnl >= 0 ? "+" : ""}${r.pnl.toLocaleString()}
                            </td>
                            <td className={`py-2 px-2 text-right ${r.pnl_percent >= 0 ? "text-[#00FFA3]" : "text-red-400"}`}>
                              {r.pnl_percent >= 0 ? "+" : ""}{r.pnl_percent}%
                            </td>
                            <td className="py-2 px-2 text-right text-amber-400">${r.tax.toLocaleString()}</td>
                            <td className={`py-2 px-2 text-right font-bold ${r.net_pnl >= 0 ? "text-[#00FFA3]" : "text-red-400"}`}>
                              {r.net_pnl >= 0 ? "+" : ""}${r.net_pnl.toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}

            {!results && (
              <div className="glass-card rounded-2xl p-12 text-center">
                <BarChart3 className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                <p className="text-slate-500 text-sm">Configure your position and hit Simulate to see exit scenarios</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
