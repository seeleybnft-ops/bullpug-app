/**
 * TradingJournal Page - Unified trading dashboard with multiple tabs
 * Refactored to use extracted sub-components for maintainability
 */

import { useState, useEffect, useRef } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { useAccount } from "wagmi";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import axios from "axios";
import {
  BarChart3, DollarSign, Plus, Download, FileText, Calculator, Activity, Trophy, Star, BookOpen
} from "lucide-react";
import { Line as ChartLine, Bar as ChartBar } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip as ChartTooltip, Legend, Filler } from "chart.js";
import jsPDF from "jspdf";

// Extracted components
import { Dashboard, TradesList, TradeForm, ExitSimulator, CloudBackup } from "@/components/journal";
import JournalAIAssistant from "@/components/JournalAIAssistant";
import DetectedTrades from "@/components/DetectedTrades";
import PortfolioSummary from "@/components/PortfolioSummary";
import AchievementBadges from "@/components/AchievementBadges";
import Watchlist from "@/components/Watchlist";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, ChartTooltip, Legend, Filler);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function TradingJournal() {
  const { publicKey, connected: solanaConnected } = useWallet();
  const { address: evmAddress, isConnected: evmConnected } = useAccount();
  
  // Combined wallet address for AI Assistant (prefer Solana, fallback to EVM)
  const walletAddress = solanaConnected 
    ? publicKey?.toBase58() 
    : (evmConnected ? evmAddress : null);
  
  const [tab, setTab] = useState("dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [trades, setTrades] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingTrade, setEditingTrade] = useState(null);
  const [loading, setLoading] = useState(true);

  // Exit Simulator State
  const [simTab, setSimTab] = useState("paths");
  const [tokenAmount, setTokenAmount] = useState("1000");
  const [entryPrice, setEntryPrice] = useState("0.001");
  const [volatility, setVolatility] = useState([80]);
  const [drift, setDrift] = useState([50]);
  const [days, setDays] = useState([90]);
  const [simulations, setSimulations] = useState([1000]);
  const [taxRate, setTaxRate] = useState("30");
  const [simResults, setSimResults] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [showTradeSelector, setShowTradeSelector] = useState(false);
  const reportRef = useRef(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [dashRes, tradesRes] = await Promise.all([
        axios.get(`${API}/journal/dashboard`),
        axios.get(`${API}/journal/trades?limit=100`)
      ]);
      setDashboard(dashRes.data);
      setTrades(tradesRes.data.trades);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  // Exit Simulator Functions
  const runSimulation = async () => {
    setSimLoading(true);
    try {
      const { data } = await axios.post(`${API}/simulation/monte-carlo`, {
        token_amount: parseFloat(tokenAmount),
        entry_price: parseFloat(entryPrice),
        volatility: volatility[0] / 100,
        drift: drift[0] / 100,
        days: days[0],
        simulations: simulations[0],
        tax_rate: parseFloat(taxRate) / 100,
      });
      setSimResults(data);
      toast.success("Simulation complete!");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Simulation failed");
    }
    setSimLoading(false);
  };

  const selectTradeForSim = (trade) => {
    setSelectedTrade(trade);
    setTokenAmount(String(trade.position_size || 1000));
    setEntryPrice(String(trade.entry_price || 0.001));
    setShowTradeSelector(false);
    toast.success(`Loaded ${trade.asset} trade parameters`);
  };

  const exportSimPDF = () => {
    if (!simResults) return;
    const r = simResults;
    const doc = new jsPDF();
    
    doc.setFillColor(5, 5, 10);
    doc.rect(0, 0, 210, 297, "F");
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(18);
    doc.text("Bullpug Exit Simulator Report", 15, 20);
    doc.setFontSize(9);
    doc.setTextColor(100, 100, 100);
    doc.text(`Generated: ${new Date().toLocaleString()}`, 15, 28);
    doc.text(`Simulation Period: ${r.days} days | Simulations: ${r.simulations}`, 15, 34);

    doc.setTextColor(0, 255, 163);
    doc.setFontSize(12);
    doc.text("Input Parameters", 15, 48);
    doc.setFontSize(9);
    doc.setTextColor(200, 200, 200);
    const params = [
      `Tokens: ${r.token_amount.toLocaleString()} | Entry: $${r.entry_price}`,
      `Volatility: ${(r.volatility * 100).toFixed(0)}% | Drift: ${(r.drift * 100).toFixed(0)}%`,
      `Tax Rate: ${(r.tax_rate * 100).toFixed(0)}%`,
    ];
    params.forEach((p, i) => doc.text(p, 15, 56 + i * 6));

    doc.setTextColor(0, 194, 255);
    doc.setFontSize(12);
    doc.text("Probability Outcomes", 15, 82);
    doc.setFontSize(9);
    doc.setTextColor(200, 200, 200);
    const probs = [
      `Probability of Profit: ${r.prob_profit}%`,
      `Probability of 2x: ${r.prob_2x}%`,
      `Probability of 5x: ${r.prob_5x}%`,
      `Probability of 10x: ${r.prob_10x}%`,
      `Probability of >50% Loss: ${r.prob_loss50}%`,
    ];
    probs.forEach((p, i) => doc.text(p, 15, 90 + i * 6));

    doc.setTextColor(217, 70, 239);
    doc.setFontSize(12);
    doc.text("P&L Summary (after tax)", 15, 130);
    doc.setFontSize(9);
    doc.setTextColor(200, 200, 200);
    const pnlRows = [
      `Mean Net P&L: $${r.mean_pnl.toLocaleString()}`,
      `Median Net P&L: $${r.median_pnl.toLocaleString()}`,
      `Best Case: $${r.max_pnl.toLocaleString()}`,
      `Worst Case: $${r.min_pnl.toLocaleString()}`,
    ];
    pnlRows.forEach((p, i) => doc.text(p, 15, 138 + i * 6));

    doc.setTextColor(100, 100, 100);
    doc.setFontSize(7);
    doc.text("Generated by Bullpug Exit Simulator - Monte Carlo GBM Model", 15, 280);
    doc.text("Disclaimer: This is a simulation. Past performance does not guarantee future results.", 15, 285);

    doc.save("bullpug-exit-simulation.pdf");
    toast.success("PDF exported!");
  };

  // Chart data for Exit Simulator
  const pathsChart = simResults ? {
    labels: simResults.chart.days.map(d => `D${d}`),
    datasets: [
      { label: "95th %ile", data: simResults.chart.bands.p95, borderColor: "rgba(0,255,163,0.15)", backgroundColor: "rgba(0,255,163,0.02)", fill: "+1", borderWidth: 1, pointRadius: 0, tension: 0.3 },
      { label: "75th %ile", data: simResults.chart.bands.p75, borderColor: "rgba(0,255,163,0.3)", backgroundColor: "rgba(0,255,163,0.05)", fill: "+1", borderWidth: 1, pointRadius: 0, tension: 0.3 },
      { label: "Median", data: simResults.chart.bands.p50, borderColor: "#00FFA3", backgroundColor: "rgba(0,255,163,0.1)", fill: "+1", borderWidth: 2, pointRadius: 0, tension: 0.3 },
      { label: "25th %ile", data: simResults.chart.bands.p25, borderColor: "rgba(217,70,239,0.3)", backgroundColor: "rgba(217,70,239,0.05)", fill: "+1", borderWidth: 1, pointRadius: 0, tension: 0.3 },
      { label: "5th %ile", data: simResults.chart.bands.p5, borderColor: "rgba(255,59,48,0.3)", borderWidth: 1, pointRadius: 0, fill: false, tension: 0.3 },
      ...simResults.chart.sample_paths.slice(0, 5).map((path, i) => ({
        label: `Path ${i + 1}`, data: path, borderColor: `hsla(${i * 60}, 80%, 60%, 0.25)`, borderWidth: 0.8, pointRadius: 0, fill: false, tension: 0.3,
      })),
    ],
  } : null;

  const histChart = simResults ? {
    labels: simResults.histogram.map(h => `$${h.min.toFixed(5)}`),
    datasets: [{
      label: "Frequency",
      data: simResults.histogram.map(h => h.count),
      backgroundColor: simResults.histogram.map(h => h.min >= simResults.entry_price ? "rgba(0,255,163,0.6)" : "rgba(255,59,48,0.6)"),
      borderRadius: 2,
    }],
  } : null;

  const simChartOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { backgroundColor: "#13131F", borderColor: "rgba(255,255,255,0.1)", borderWidth: 1 } },
    scales: {
      x: { ticks: { color: "#64748b", font: { size: 8 }, maxTicksLimit: 15 }, grid: { color: "rgba(255,255,255,0.03)" } },
      y: { ticks: { color: "#64748b", font: { size: 9 } }, grid: { color: "rgba(255,255,255,0.03)" } },
    },
  };

  const exportCSV = () => {
    window.open(`${API}/journal/export/csv`, '_blank');
    toast.success("Downloading CSV...");
  };

  const exportPDF = () => {
    if (!dashboard || trades.length === 0) {
      return toast.error("No trades to export");
    }

    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();

    // Title
    doc.setFontSize(20);
    doc.setTextColor(0, 255, 163);
    doc.text("Bullpug Trading Journal", pageWidth / 2, 20, { align: "center" });

    // Summary
    doc.setFontSize(12);
    doc.setTextColor(100);
    doc.text(`Generated: ${new Date().toLocaleString()}`, pageWidth / 2, 28, { align: "center" });

    // Dashboard Stats
    doc.setFontSize(14);
    doc.setTextColor(0);
    doc.text("Performance Summary", 20, 45);

    doc.setFontSize(10);
    const stats = [
      `Total Trades: ${dashboard.total_trades}`,
      `Win Rate: ${dashboard.win_rate}%`,
      `Total P&L: $${dashboard.total_pnl}`,
      `Avg P&L: $${dashboard.avg_pnl}`,
      `Win Streak: ${dashboard.win_streak}`,
      `Loss Streak: ${dashboard.loss_streak}`,
      `Sharpe Ratio: ${dashboard.sharpe_ratio}`,
    ];

    let y = 55;
    stats.forEach(stat => {
      doc.text(stat, 20, y);
      y += 7;
    });

    // Trades Table Header
    y += 10;
    doc.setFontSize(14);
    doc.text("Recent Trades", 20, y);
    y += 10;

    doc.setFontSize(8);
    doc.setTextColor(100);
    doc.text("Date", 20, y);
    doc.text("Asset", 45, y);
    doc.text("Type", 70, y);
    doc.text("Entry", 95, y);
    doc.text("Exit", 115, y);
    doc.text("P&L", 135, y);
    doc.text("Grade", 160, y);
    y += 5;

    // Trades
    doc.setTextColor(0);
    trades.slice(0, 30).forEach(trade => {
      if (y > 280) {
        doc.addPage();
        y = 20;
      }
      doc.text(trade.date_entry?.slice(0, 10) || "-", 20, y);
      doc.text(trade.asset || "-", 45, y);
      doc.text(trade.trade_type || "-", 70, y);
      doc.text(`$${trade.entry_price || 0}`, 95, y);
      doc.text(`$${trade.exit_price || "-"}`, 115, y);
      const pnlColor = (trade.pnl || 0) >= 0 ? [0, 150, 0] : [200, 0, 0];
      doc.setTextColor(...pnlColor);
      doc.text(`$${trade.pnl || 0}`, 135, y);
      doc.setTextColor(0);
      doc.text(trade.trade_grade || "-", 160, y);
      y += 6;
    });

    doc.save("bullpug_trading_journal.pdf");
    toast.success("PDF exported!");
  };

  const deleteTrade = async (tradeId) => {
    if (!window.confirm("Delete this trade?")) return;
    try {
      await axios.delete(`${API}/journal/trade/${tradeId}`);
      toast.success("Trade deleted");
      fetchData();
    } catch (e) {
      toast.error("Failed to delete");
    }
  };

  const formatCurrency = (val) => {
    if (val === null || val === undefined) return "-";
    const sign = val >= 0 ? "+" : "";
    return `${sign}$${Math.abs(val).toLocaleString()}`;
  };

  return (
    <div className="pt-20 pb-16 min-h-screen" data-testid="trading-journal-page">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-7xl mx-auto px-4 md:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              My <span className="text-[#00C2FF]">Journal</span>
            </h1>
            <p className="text-slate-500 text-sm mt-1">Track, analyze, simulate exits & improve your trading</p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={exportCSV}
              variant="outline"
              data-testid="export-csv-btn"
              className="border-white/20 text-slate-400 hover:text-white rounded-xl px-4 py-2 text-xs uppercase"
            >
              <Download className="w-3 h-3 mr-1" /> CSV
            </Button>
            <Button
              onClick={exportPDF}
              variant="outline"
              data-testid="export-pdf-btn"
              className="border-white/20 text-slate-400 hover:text-white rounded-xl px-4 py-2 text-xs uppercase"
            >
              <FileText className="w-3 h-3 mr-1" /> PDF
            </Button>
            <Button
              onClick={() => { setEditingTrade(null); setShowForm(true); }}
              data-testid="new-trade-btn"
              className="bg-[#00FFA3] text-black font-bold rounded-xl px-6 py-5 text-sm uppercase hover:scale-[1.02] transition-transform"
            >
              <Plus className="w-4 h-4 mr-2" /> Log Trade
            </Button>
          </div>
        </div>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="bg-black/40 border border-white/10 rounded-xl p-1 mb-6 flex-wrap">
            <TabsTrigger value="dashboard" data-testid="tab-dashboard" className="data-[state=active]:bg-[#00C2FF]/10 data-[state=active]:text-[#00C2FF] rounded-lg font-bold text-xs uppercase">
              <BarChart3 className="w-4 h-4 mr-2" />Dashboard
            </TabsTrigger>
            <TabsTrigger value="portfolio" data-testid="tab-portfolio" className="data-[state=active]:bg-[#9945FF]/10 data-[state=active]:text-[#9945FF] rounded-lg font-bold text-xs uppercase">
              <DollarSign className="w-4 h-4 mr-2" />Portfolio Value
            </TabsTrigger>
            <TabsTrigger value="import" data-testid="tab-import" className="data-[state=active]:bg-[#627EEA]/10 data-[state=active]:text-[#627EEA] rounded-lg font-bold text-xs uppercase">
              <Download className="w-4 h-4 mr-2" />Import
            </TabsTrigger>
            <TabsTrigger value="trades" data-testid="tab-trades" className="data-[state=active]:bg-[#00FFA3]/10 data-[state=active]:text-[#00FFA3] rounded-lg font-bold text-xs uppercase">
              <BookOpen className="w-4 h-4 mr-2" />Trades
            </TabsTrigger>
            <TabsTrigger value="simulator" data-testid="tab-simulator" className="data-[state=active]:bg-[#D946EF]/10 data-[state=active]:text-[#D946EF] rounded-lg font-bold text-xs uppercase">
              <Calculator className="w-4 h-4 mr-2" />Exit Sim
            </TabsTrigger>
            <TabsTrigger value="achievements" data-testid="tab-achievements" className="data-[state=active]:bg-[#F5D300]/10 data-[state=active]:text-[#F5D300] rounded-lg font-bold text-xs uppercase">
              <Trophy className="w-4 h-4 mr-2" />Achievements
            </TabsTrigger>
            <TabsTrigger value="watchlist" data-testid="tab-watchlist" className="data-[state=active]:bg-[#FFD700]/10 data-[state=active]:text-[#FFD700] rounded-lg font-bold text-xs uppercase">
              <Star className="w-4 h-4 mr-2" />Watchlist
            </TabsTrigger>
            <TabsTrigger value="backups" data-testid="tab-backups" className="data-[state=active]:bg-[#FF6B6B]/10 data-[state=active]:text-[#FF6B6B] rounded-lg font-bold text-xs uppercase">
              <Activity className="w-4 h-4 mr-2" />Backup
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard">
            <Dashboard dashboard={dashboard} trades={trades} loading={loading} formatCurrency={formatCurrency} walletAddress={walletAddress} />
          </TabsContent>

          <TabsContent value="portfolio">
            <PortfolioSummary />
          </TabsContent>

          <TabsContent value="import">
            <DetectedTrades onImport={fetchData} />
          </TabsContent>

          <TabsContent value="trades">
            <TradesList
              trades={trades}
              onEdit={(t) => { setEditingTrade(t); setShowForm(true); }}
              onDelete={deleteTrade}
              formatCurrency={formatCurrency}
            />
          </TabsContent>

          <TabsContent value="simulator">
            <ExitSimulator 
              trades={trades}
              tokenAmount={tokenAmount}
              setTokenAmount={setTokenAmount}
              entryPrice={entryPrice}
              setEntryPrice={setEntryPrice}
              volatility={volatility}
              setVolatility={setVolatility}
              drift={drift}
              setDrift={setDrift}
              days={days}
              setDays={setDays}
              simulations={simulations}
              setSimulations={setSimulations}
              taxRate={taxRate}
              setTaxRate={setTaxRate}
              showTradeSelector={showTradeSelector}
              setShowTradeSelector={setShowTradeSelector}
              selectedTrade={selectedTrade}
              selectTradeForSim={selectTradeForSim}
              runSimulation={runSimulation}
              simLoading={simLoading}
              simResults={simResults}
              simTab={simTab}
              setSimTab={setSimTab}
              pathsChart={pathsChart}
              histChart={histChart}
              simChartOpts={simChartOpts}
              exportSimPDF={exportSimPDF}
              reportRef={reportRef}
            />
          </TabsContent>

          <TabsContent value="achievements">
            <AchievementBadges />
          </TabsContent>

          <TabsContent value="watchlist">
            <Watchlist />
          </TabsContent>

          <TabsContent value="backups">
            <CloudBackup onRestore={fetchData} />
          </TabsContent>
        </Tabs>

        {showForm && (
          <TradeForm
            trade={editingTrade}
            onClose={() => { setShowForm(false); setEditingTrade(null); }}
            onSave={() => { setShowForm(false); setEditingTrade(null); fetchData(); }}
          />
        )}

        {/* AI Trading Assistant - Full featured panel */}
        <JournalAIAssistant 
          walletAddress={walletAddress} 
          solanaAddress={solanaConnected ? publicKey?.toBase58() : null}
          evmAddress={evmConnected ? evmAddress : null}
        />
      </div>
    </div>
  );
}
