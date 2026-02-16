import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import axios from "axios";
import {
  BarChart3, TrendingUp, TrendingDown, DollarSign, Plus, X, Edit2, Trash2,
  BookOpen, Target, Brain, Activity, Award, AlertTriangle, Calendar, Hash,
  Download, FileText
} from "lucide-react";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";
import jsPDF from "jspdf";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const TRADE_TYPES = ["Long", "Short", "Spot"];
const STRATEGIES = ["Scalping", "Day Trading", "Swing Trading", "Position Trading", "Breakout", "Mean Reversion", "News Trading", "Other"];
const EMOTIONS = ["Confident", "Calm", "Anxious", "Fearful", "Greedy", "FOMO", "Neutral", "Excited", "Frustrated"];
const GRADES = ["A+", "A", "B+", "B", "C+", "C", "D", "F"];
const MARKET_CONDITIONS = ["Bullish", "Bearish", "Ranging", "High Volatility", "Low Volatility", "Uncertain"];

export default function TradingJournal() {
  const [tab, setTab] = useState("dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [trades, setTrades] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingTrade, setEditingTrade] = useState(null);
  const [loading, setLoading] = useState(true);

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
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-7xl mx-auto px-4 md:px-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tighter uppercase" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              Trading <span className="text-[#00C2FF]">Journal</span>
            </h1>
            <p className="text-slate-500 text-sm mt-1">Track, analyze, and improve your trading</p>
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
          <TabsList className="bg-black/40 border border-white/10 rounded-xl p-1 mb-6">
            <TabsTrigger value="dashboard" data-testid="tab-dashboard" className="data-[state=active]:bg-[#00C2FF]/10 data-[state=active]:text-[#00C2FF] rounded-lg font-bold text-xs uppercase">
              <BarChart3 className="w-4 h-4 mr-2" />Dashboard
            </TabsTrigger>
            <TabsTrigger value="trades" data-testid="tab-trades" className="data-[state=active]:bg-[#00FFA3]/10 data-[state=active]:text-[#00FFA3] rounded-lg font-bold text-xs uppercase">
              <BookOpen className="w-4 h-4 mr-2" />Trades
            </TabsTrigger>
            <TabsTrigger value="backups" data-testid="tab-backups" className="data-[state=active]:bg-[#D946EF]/10 data-[state=active]:text-[#D946EF] rounded-lg font-bold text-xs uppercase">
              <Activity className="w-4 h-4 mr-2" />Cloud Backup
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard">
            <Dashboard dashboard={dashboard} trades={trades} loading={loading} formatCurrency={formatCurrency} />
          </TabsContent>

          <TabsContent value="trades">
            <TradesList
              trades={trades}
              onEdit={(t) => { setEditingTrade(t); setShowForm(true); }}
              onDelete={deleteTrade}
              formatCurrency={formatCurrency}
            />
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
      </div>
    </div>
  );
}

function Dashboard({ dashboard, trades, loading, formatCurrency }) {
  if (loading) {
    return (
      <div className="glass-card rounded-2xl p-16 text-center">
        <Activity className="w-10 h-10 mx-auto mb-3 text-slate-600 animate-pulse" />
        <p className="text-slate-500">Loading dashboard...</p>
      </div>
    );
  }

  if (!dashboard || dashboard.total_trades === 0) {
    return (
      <div className="glass-card rounded-2xl p-16 text-center">
        <BookOpen className="w-14 h-14 mx-auto mb-4 text-slate-700" />
        <p className="text-slate-500 text-sm mb-2">No trades logged yet</p>
        <p className="text-slate-600 text-xs">Start logging your trades to see analytics</p>
      </div>
    );
  }

  const pnlData = trades
    .filter(t => t.status === "closed")
    .sort((a, b) => new Date(a.date_entry) - new Date(b.date_entry))
    .reduce((acc, t, i) => {
      const cumPnl = (acc[i - 1]?.cumPnl || 0) + (t.pnl || 0);
      acc.push({ name: t.trade_id, pnl: t.pnl, cumPnl, asset: t.asset });
      return acc;
    }, []);

  const assetData = Object.entries(dashboard.pnl_by_asset || {}).map(([asset, pnl]) => ({
    name: asset, value: Math.abs(pnl), pnl, fill: pnl >= 0 ? "#00FFA3" : "#FF3B30"
  }));

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <SummaryCard icon={<DollarSign />} label="Total P&L" value={formatCurrency(dashboard.total_pnl)} color={dashboard.total_pnl >= 0 ? "#00FFA3" : "#FF3B30"} />
        <SummaryCard icon={<Target />} label="Win Rate" value={`${dashboard.win_rate}%`} color="#00C2FF" />
        <SummaryCard icon={<BarChart3 />} label="Total Trades" value={dashboard.total_trades} color="#D946EF" />
        <SummaryCard icon={<TrendingUp />} label="Wins" value={dashboard.total_wins} color="#00FFA3" />
        <SummaryCard icon={<TrendingDown />} label="Losses" value={dashboard.total_losses} color="#FF3B30" />
        <SummaryCard icon={<Activity />} label="Avg P&L" value={formatCurrency(dashboard.avg_pnl)} color={dashboard.avg_pnl >= 0 ? "#00FFA3" : "#FF3B30"} />
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-xs font-bold uppercase text-[#00FFA3] mb-3 flex items-center gap-2">
            <Award size={14} /> Best Trade
          </h4>
          {dashboard.biggest_win ? (
            <div>
              <p className="text-2xl font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron' }}>
                +${dashboard.biggest_win.pnl?.toLocaleString()}
              </p>
              <p className="text-xs text-slate-400">{dashboard.biggest_win.asset} - {dashboard.biggest_win.trade_id}</p>
            </div>
          ) : <p className="text-slate-500 text-sm">No winning trades yet</p>}
        </div>
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-xs font-bold uppercase text-red-400 mb-3 flex items-center gap-2">
            <AlertTriangle size={14} /> Worst Trade
          </h4>
          {dashboard.biggest_loss ? (
            <div>
              <p className="text-2xl font-black text-red-400" style={{ fontFamily: 'Orbitron' }}>
                -${Math.abs(dashboard.biggest_loss.pnl)?.toLocaleString()}
              </p>
              <p className="text-xs text-slate-400">{dashboard.biggest_loss.asset} - {dashboard.biggest_loss.trade_id}</p>
            </div>
          ) : <p className="text-slate-500 text-sm">No losing trades yet</p>}
        </div>
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-xs font-bold uppercase text-[#D946EF] mb-3 flex items-center gap-2">
            <Hash size={14} /> Most Traded
          </h4>
          {dashboard.most_traded_asset ? (
            <div>
              <p className="text-2xl font-black text-[#D946EF]" style={{ fontFamily: 'Orbitron' }}>
                {dashboard.most_traded_asset.asset}
              </p>
              <p className="text-xs text-slate-400">{dashboard.most_traded_asset.count} trades</p>
            </div>
          ) : <p className="text-slate-500 text-sm">No trades yet</p>}
        </div>
      </div>

      {/* Streaks & Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Win Streak</p>
          <p className="text-xl font-black text-[#00FFA3]">{dashboard.win_streak}</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Loss Streak</p>
          <p className="text-xl font-black text-red-400">{dashboard.loss_streak}</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Avg R:R</p>
          <p className="text-xl font-black text-[#00C2FF]">{dashboard.avg_rr}:1</p>
        </div>
        <div className="glass-card rounded-xl p-4 text-center">
          <p className="text-xs text-slate-500 mb-1">Sharpe Ratio</p>
          <p className="text-xl font-black text-[#F5D300]">{dashboard.sharpe_ratio}</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {pnlData.length > 0 && (
          <div className="glass-card rounded-2xl p-5">
            <h4 className="text-sm font-bold uppercase mb-4" style={{ fontFamily: 'Orbitron' }}>Cumulative P&L</h4>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={pnlData}>
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 9, fill: '#64748b' }} />
                <Tooltip contentStyle={{ backgroundColor: '#13131F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                <Line type="monotone" dataKey="cumPnl" stroke="#00FFA3" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
        {assetData.length > 0 && (
          <div className="glass-card rounded-2xl p-5">
            <h4 className="text-sm font-bold uppercase mb-4" style={{ fontFamily: 'Orbitron' }}>P&L by Asset</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={assetData}>
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 9, fill: '#64748b' }} />
                <Tooltip contentStyle={{ backgroundColor: '#13131F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                  {assetData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Recent Emotions */}
      {dashboard.recent_emotions?.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-xs font-bold uppercase text-[#D946EF] mb-3 flex items-center gap-2">
            <Brain size={14} /> Recent Mindset
          </h4>
          <div className="flex flex-wrap gap-2">
            {dashboard.recent_emotions.map((e, i) => (
              <div key={i} className="text-[10px] px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
                <span className="text-slate-400">{e.asset}:</span>{" "}
                <span className="text-[#00FFA3]">{e.entry || "?"}</span>
                <span className="text-slate-600"> → </span>
                <span className="text-[#D946EF]">{e.exit || "?"}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ icon, label, value, color }) {
  return (
    <div className="glass-card rounded-xl p-4 text-center">
      <div className="w-8 h-8 mx-auto mb-2 rounded-full flex items-center justify-center" style={{ backgroundColor: `${color}15` }}>
        <span style={{ color }}>{icon}</span>
      </div>
      <p className="text-lg font-black" style={{ color, fontFamily: 'Orbitron' }}>{value}</p>
      <p className="text-[10px] text-slate-500 uppercase">{label}</p>
    </div>
  );
}

function TradesList({ trades, onEdit, onDelete, formatCurrency }) {
  const [filter, setFilter] = useState("all");
  const filtered = trades.filter(t => filter === "all" || t.status === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        {["all", "open", "closed"].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-xs font-bold uppercase transition-colors ${
              filter === f ? "bg-[#00C2FF]/10 text-[#00C2FF]" : "bg-white/5 text-slate-400 hover:text-white"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="glass-card rounded-xl p-10 text-center">
          <p className="text-slate-500">No {filter !== "all" ? filter : ""} trades found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(trade => (
            <div key={trade.trade_id} className="glass-card rounded-xl p-4 hover:bg-white/[0.02] transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-sm ${
                    trade.trade_type?.toLowerCase() === "long" ? "bg-[#00FFA3]/10 text-[#00FFA3]" :
                    trade.trade_type?.toLowerCase() === "short" ? "bg-red-500/10 text-red-400" :
                    "bg-[#00C2FF]/10 text-[#00C2FF]"
                  }`}>
                    {trade.asset?.slice(0, 4)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{trade.asset}</span>
                      <Badge className={`text-[9px] ${
                        trade.trade_type?.toLowerCase() === "long" ? "bg-[#00FFA3]/10 text-[#00FFA3]" :
                        trade.trade_type?.toLowerCase() === "short" ? "bg-red-500/10 text-red-400" :
                        "bg-[#00C2FF]/10 text-[#00C2FF]"
                      }`}>
                        {trade.trade_type} {trade.leverage && trade.leverage > 1 ? `${trade.leverage}x` : ""}
                      </Badge>
                      <Badge className={`text-[9px] ${trade.status === "open" ? "bg-amber-500/10 text-amber-400" : "bg-slate-500/10 text-slate-400"}`}>
                        {trade.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      {trade.trade_id} | Entry: ${trade.entry_price} | Size: {trade.position_size}
                      {trade.exit_price && ` | Exit: $${trade.exit_price}`}
                    </p>
                    <p className="text-[10px] text-slate-600 mt-1">
                      <Calendar className="inline w-3 h-3 mr-1" />
                      {new Date(trade.date_entry).toLocaleDateString()}
                      {trade.strategy && <span className="ml-2">| {trade.strategy}</span>}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {trade.status === "closed" && (
                    <p className={`text-xl font-black ${trade.pnl >= 0 ? "text-[#00FFA3]" : "text-red-400"}`} style={{ fontFamily: 'Orbitron' }}>
                      {formatCurrency(trade.pnl)}
                    </p>
                  )}
                  {trade.pnl_percent !== undefined && trade.status === "closed" && (
                    <p className={`text-xs ${trade.pnl_percent >= 0 ? "text-[#00FFA3]" : "text-red-400"}`}>
                      {trade.pnl_percent >= 0 ? "+" : ""}{trade.pnl_percent}%
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-2">
                    <button onClick={() => onEdit(trade)} className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white">
                      <Edit2 size={14} />
                    </button>
                    <button onClick={() => onDelete(trade.trade_id)} className="p-1.5 rounded hover:bg-red-500/10 text-slate-400 hover:text-red-400">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
              {(trade.entry_reason || trade.lessons) && (
                <div className="mt-3 pt-3 border-t border-white/5 grid grid-cols-1 md:grid-cols-2 gap-3">
                  {trade.entry_reason && (
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase mb-1">Entry Reason</p>
                      <p className="text-xs text-slate-300">{trade.entry_reason}</p>
                    </div>
                  )}
                  {trade.lessons && (
                    <div>
                      <p className="text-[10px] text-slate-500 uppercase mb-1">Lessons</p>
                      <p className="text-xs text-slate-300">{trade.lessons}</p>
                    </div>
                  )}
                </div>
              )}
              {trade.tags?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {trade.tags.map((tag, i) => (
                    <span key={i} className="text-[9px] px-2 py-0.5 rounded-full bg-[#D946EF]/10 text-[#D946EF]">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TradeForm({ trade, onClose, onSave }) {
  const [form, setForm] = useState({
    trade_id: trade?.trade_id || "",
    date_entry: trade?.date_entry || new Date().toISOString().split("T")[0],
    date_exit: trade?.date_exit || "",
    asset: trade?.asset || "",
    trade_type: trade?.trade_type || "Long",
    leverage: trade?.leverage || 1,
    entry_price: trade?.entry_price || "",
    position_size: trade?.position_size || "",
    exit_price: trade?.exit_price || "",
    exit_reason: trade?.exit_reason || "",
    stop_loss: trade?.stop_loss || "",
    take_profit: trade?.take_profit || "",
    fees: trade?.fees || 0,
    slippage: trade?.slippage || 0,
    chart_link: trade?.chart_link || "",
    entry_reason: trade?.entry_reason || "",
    strategy: trade?.strategy || "",
    market_conditions: trade?.market_conditions || "",
    expected_rr: trade?.expected_rr || "",
    emotion_entry: trade?.emotion_entry || "",
    emotion_exit: trade?.emotion_exit || "",
    confidence_level: trade?.confidence_level || 5,
    mindset_notes: trade?.mindset_notes || "",
    what_went_well: trade?.what_went_well || "",
    what_went_wrong: trade?.what_went_wrong || "",
    lessons: trade?.lessons || "",
    trade_grade: trade?.trade_grade || "",
    tags: trade?.tags?.join(", ") || "",
    external_influences: trade?.external_influences || "",
    health_notes: trade?.health_notes || "",
    status: trade?.status || "open",
  });
  const [saving, setSaving] = useState(false);
  const [activeSection, setActiveSection] = useState("basic");

  const handleChange = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.asset || !form.entry_price || !form.position_size) {
      return toast.error("Fill required fields: Asset, Entry Price, Position Size");
    }
    setSaving(true);
    try {
      const payload = {
        ...form,
        entry_price: parseFloat(form.entry_price),
        position_size: parseFloat(form.position_size),
        exit_price: form.exit_price ? parseFloat(form.exit_price) : null,
        stop_loss: form.stop_loss ? parseFloat(form.stop_loss) : null,
        take_profit: form.take_profit ? parseFloat(form.take_profit) : null,
        fees: parseFloat(form.fees) || 0,
        slippage: parseFloat(form.slippage) || 0,
        leverage: parseFloat(form.leverage) || 1,
        expected_rr: form.expected_rr ? parseFloat(form.expected_rr) : null,
        confidence_level: parseInt(form.confidence_level) || null,
        tags: form.tags ? form.tags.split(",").map(t => t.trim()).filter(Boolean) : [],
      };

      if (trade) {
        await axios.put(`${API}/journal/trade/${trade.trade_id}`, payload);
        toast.success("Trade updated!");
      } else {
        await axios.post(`${API}/journal/trade`, payload);
        toast.success("Trade logged!");
      }
      onSave();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save");
    }
    setSaving(false);
  };

  const sections = [
    { id: "basic", label: "Basic Info" },
    { id: "prices", label: "Prices & Sizing" },
    { id: "strategy", label: "Strategy" },
    { id: "psychology", label: "Psychology" },
    { id: "review", label: "Review" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="w-full max-w-3xl glass-card rounded-2xl p-6 my-8 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-black uppercase" style={{ fontFamily: 'Orbitron' }}>
            {trade ? "Edit Trade" : "Log New Trade"}
          </h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white">
            <X size={20} />
          </button>
        </div>

        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {sections.map(s => (
            <button
              key={s.id}
              onClick={() => setActiveSection(s.id)}
              className={`px-4 py-2 rounded-lg text-xs font-bold uppercase whitespace-nowrap transition-colors ${
                activeSection === s.id ? "bg-[#00C2FF]/10 text-[#00C2FF]" : "bg-white/5 text-slate-400 hover:text-white"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {activeSection === "basic" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Asset *</label>
                <Input value={form.asset} onChange={e => handleChange("asset", e.target.value.toUpperCase())}
                  placeholder="BTC/USDT" className="bg-black/50 border-white/10 text-white" data-testid="trade-asset" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Trade Type</label>
                <div className="flex gap-2">
                  {TRADE_TYPES.map(t => (
                    <button key={t} type="button" onClick={() => handleChange("trade_type", t)}
                      className={`flex-1 py-2 rounded-lg text-xs font-bold transition-colors ${
                        form.trade_type === t ? "bg-[#00C2FF]/20 text-[#00C2FF] border border-[#00C2FF]/50" : "bg-white/5 text-slate-400 border border-white/10"
                      }`}>
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Entry Date</label>
                <Input type="date" value={form.date_entry} onChange={e => handleChange("date_entry", e.target.value)}
                  className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Exit Date</label>
                <Input type="date" value={form.date_exit} onChange={e => handleChange("date_exit", e.target.value)}
                  className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Leverage</label>
                <Input type="number" step="0.1" value={form.leverage} onChange={e => handleChange("leverage", e.target.value)}
                  placeholder="1" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Status</label>
                <div className="flex gap-2">
                  {["open", "closed"].map(s => (
                    <button key={s} type="button" onClick={() => handleChange("status", s)}
                      className={`flex-1 py-2 rounded-lg text-xs font-bold uppercase transition-colors ${
                        form.status === s ? "bg-[#00FFA3]/20 text-[#00FFA3] border border-[#00FFA3]/50" : "bg-white/5 text-slate-400 border border-white/10"
                      }`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeSection === "prices" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Entry Price *</label>
                <Input type="number" step="any" value={form.entry_price} onChange={e => handleChange("entry_price", e.target.value)}
                  placeholder="50000" className="bg-black/50 border-white/10 text-white" data-testid="trade-entry-price" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Position Size *</label>
                <Input type="number" step="any" value={form.position_size} onChange={e => handleChange("position_size", e.target.value)}
                  placeholder="0.1" className="bg-black/50 border-white/10 text-white" data-testid="trade-position-size" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Exit Price</label>
                <Input type="number" step="any" value={form.exit_price} onChange={e => handleChange("exit_price", e.target.value)}
                  placeholder="52000" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Exit Reason</label>
                <Input value={form.exit_reason} onChange={e => handleChange("exit_reason", e.target.value)}
                  placeholder="Hit TP / Stopped out / Manual close" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Stop Loss</label>
                <Input type="number" step="any" value={form.stop_loss} onChange={e => handleChange("stop_loss", e.target.value)}
                  placeholder="48000" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Take Profit</label>
                <Input type="number" step="any" value={form.take_profit} onChange={e => handleChange("take_profit", e.target.value)}
                  placeholder="55000" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Fees (USD)</label>
                <Input type="number" step="any" value={form.fees} onChange={e => handleChange("fees", e.target.value)}
                  placeholder="2.50" className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Slippage (USD)</label>
                <Input type="number" step="any" value={form.slippage} onChange={e => handleChange("slippage", e.target.value)}
                  placeholder="0.50" className="bg-black/50 border-white/10 text-white" />
              </div>
            </div>
          )}

          {activeSection === "strategy" && (
            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Strategy</label>
                <div className="flex flex-wrap gap-2">
                  {STRATEGIES.map(s => (
                    <button key={s} type="button" onClick={() => handleChange("strategy", s)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                        form.strategy === s ? "bg-[#D946EF]/20 text-[#D946EF] border border-[#D946EF]/50" : "bg-white/5 text-slate-400 border border-white/10"
                      }`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Entry Reason</label>
                <textarea value={form.entry_reason} onChange={e => handleChange("entry_reason", e.target.value)}
                  placeholder="Breakout above resistance, bullish divergence on RSI..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[80px]" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Market Conditions</label>
                  <div className="flex flex-wrap gap-2">
                    {MARKET_CONDITIONS.map(m => (
                      <button key={m} type="button" onClick={() => handleChange("market_conditions", m)}
                        className={`px-2 py-1 rounded text-[10px] font-bold transition-colors ${
                          form.market_conditions === m ? "bg-[#00C2FF]/20 text-[#00C2FF]" : "bg-white/5 text-slate-400"
                        }`}>
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Expected R:R</label>
                  <Input type="number" step="0.1" value={form.expected_rr} onChange={e => handleChange("expected_rr", e.target.value)}
                    placeholder="3" className="bg-black/50 border-white/10 text-white" />
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Chart Link</label>
                <Input value={form.chart_link} onChange={e => handleChange("chart_link", e.target.value)}
                  placeholder="https://tradingview.com/..." className="bg-black/50 border-white/10 text-white" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">External Influences</label>
                <Input value={form.external_influences} onChange={e => handleChange("external_influences", e.target.value)}
                  placeholder="Fed announcement, on-chain whale activity..." className="bg-black/50 border-white/10 text-white" />
              </div>
            </div>
          )}

          {activeSection === "psychology" && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Emotion at Entry</label>
                  <div className="flex flex-wrap gap-2">
                    {EMOTIONS.map(e => (
                      <button key={e} type="button" onClick={() => handleChange("emotion_entry", e)}
                        className={`px-2 py-1 rounded text-[10px] font-bold transition-colors ${
                          form.emotion_entry === e ? "bg-[#00FFA3]/20 text-[#00FFA3]" : "bg-white/5 text-slate-400"
                        }`}>
                        {e}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Emotion at Exit</label>
                  <div className="flex flex-wrap gap-2">
                    {EMOTIONS.map(e => (
                      <button key={e} type="button" onClick={() => handleChange("emotion_exit", e)}
                        className={`px-2 py-1 rounded text-[10px] font-bold transition-colors ${
                          form.emotion_exit === e ? "bg-[#D946EF]/20 text-[#D946EF]" : "bg-white/5 text-slate-400"
                        }`}>
                        {e}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Confidence Level: {form.confidence_level}/10</label>
                <input type="range" min="1" max="10" value={form.confidence_level} onChange={e => handleChange("confidence_level", e.target.value)}
                  className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Mindset Notes</label>
                <textarea value={form.mindset_notes} onChange={e => handleChange("mindset_notes", e.target.value)}
                  placeholder="How were you feeling? Any distractions?"
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[80px]" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Health & Lifestyle</label>
                <Input value={form.health_notes} onChange={e => handleChange("health_notes", e.target.value)}
                  placeholder="Good sleep, well rested..." className="bg-black/50 border-white/10 text-white" />
              </div>
            </div>
          )}

          {activeSection === "review" && (
            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">What Went Well</label>
                <textarea value={form.what_went_well} onChange={e => handleChange("what_went_well", e.target.value)}
                  placeholder="Good entry timing, followed the plan..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[60px]" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">What Went Wrong</label>
                <textarea value={form.what_went_wrong} onChange={e => handleChange("what_went_wrong", e.target.value)}
                  placeholder="Moved stop too early, oversized position..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[60px]" />
              </div>
              <div>
                <label className="text-xs text-slate-500 uppercase mb-1 block">Lessons & Adjustments</label>
                <textarea value={form.lessons} onChange={e => handleChange("lessons", e.target.value)}
                  placeholder="Next time I will..."
                  className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white text-sm min-h-[60px]" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Trade Grade</label>
                  <div className="flex flex-wrap gap-2">
                    {GRADES.map(g => (
                      <button key={g} type="button" onClick={() => handleChange("trade_grade", g)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                          form.trade_grade === g ? "bg-[#F5D300]/20 text-[#F5D300] border border-[#F5D300]/50" : "bg-white/5 text-slate-400 border border-white/10"
                        }`}>
                        {g}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-500 uppercase mb-1 block">Tags (comma separated)</label>
                  <Input value={form.tags} onChange={e => handleChange("tags", e.target.value)}
                    placeholder="breakout, btc, trending" className="bg-black/50 border-white/10 text-white" />
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-4 border-t border-white/10">
            <Button type="button" onClick={onClose} variant="outline"
              className="flex-1 border-white/20 text-slate-400 hover:text-white rounded-xl py-5">
              Cancel
            </Button>
            <Button type="submit" disabled={saving} data-testid="save-trade-btn"
              className="flex-1 bg-[#00FFA3] text-black font-bold rounded-xl py-5 hover:scale-[1.02] transition-transform">
              {saving ? "Saving..." : trade ? "Update Trade" : "Log Trade"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function CloudBackup({ onRestore }) {
  const { publicKey, connected } = useWallet();
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (connected && publicKey) {
      fetchBackups();
    }
  }, [connected, publicKey]);

  const fetchBackups = async () => {
    if (!publicKey) return;
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/journal/backups/${publicKey.toBase58()}`);
      setBackups(data.backups);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const createBackup = async () => {
    if (!publicKey) return;
    setCreating(true);
    try {
      const { data } = await axios.post(`${API}/journal/backup`, {
        wallet_address: publicKey.toBase58()
      });
      toast.success(`Backup created! ${data.trade_count} trades saved.`);
      fetchBackups();
    } catch (e) {
      toast.error("Failed to create backup");
    }
    setCreating(false);
  };

  const restoreBackup = async (backupId) => {
    if (!publicKey) return;
    if (!window.confirm("Restore this backup? This will add trades that don't exist.")) return;
    try {
      const { data } = await axios.post(
        `${API}/journal/restore/${backupId}?wallet_address=${publicKey.toBase58()}`
      );
      toast.success(`Restored ${data.restored_count} trades!`);
      onRestore?.();
    } catch (e) {
      toast.error("Failed to restore backup");
    }
  };

  const deleteBackup = async (backupId) => {
    if (!publicKey) return;
    if (!window.confirm("Delete this backup?")) return;
    try {
      await axios.delete(`${API}/journal/backup/${backupId}?wallet_address=${publicKey.toBase58()}`);
      toast.success("Backup deleted");
      fetchBackups();
    } catch (e) {
      toast.error("Failed to delete backup");
    }
  };

  if (!connected) {
    return (
      <div className="glass-card rounded-xl p-10 text-center">
        <Activity className="w-10 h-10 mx-auto mb-3 text-slate-700" />
        <p className="text-slate-500">Connect wallet to manage backups</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="glass-card rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold uppercase text-[#D946EF]">Cloud Backup</h3>
            <p className="text-xs text-slate-500 mt-1">Your trades are automatically saved to MongoDB</p>
          </div>
          <Button
            onClick={createBackup}
            disabled={creating}
            className="bg-[#D946EF] text-white font-bold rounded-xl px-4"
          >
            {creating ? "Creating..." : "Create Backup"}
          </Button>
        </div>

        <div className="p-4 rounded-lg bg-[#D946EF]/5 border border-[#D946EF]/20">
          <p className="text-xs text-slate-400">
            <strong className="text-[#D946EF]">How it works:</strong> Your trades are stored in the cloud and linked to your wallet address. 
            Create manual backups to save snapshots, and restore anytime to recover your trading history.
          </p>
        </div>
      </div>

      <div className="glass-card rounded-xl p-6">
        <h4 className="text-sm font-bold uppercase text-slate-400 mb-4">Your Backups</h4>
        
        {loading ? (
          <div className="text-center py-6">
            <Activity className="w-8 h-8 mx-auto mb-2 text-slate-600 animate-pulse" />
            <p className="text-slate-500 text-sm">Loading backups...</p>
          </div>
        ) : backups.length === 0 ? (
          <div className="text-center py-6">
            <Activity className="w-8 h-8 mx-auto mb-2 text-slate-700" />
            <p className="text-slate-600 text-sm">No backups yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {backups.map(backup => (
              <div 
                key={backup.id}
                className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5"
              >
                <div>
                  <p className="text-sm font-bold text-white">{backup.trade_count} trades</p>
                  <p className="text-xs text-slate-500">
                    {new Date(backup.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => restoreBackup(backup.id)}
                    className="px-3 py-1.5 rounded-lg bg-[#00FFA3]/10 text-[#00FFA3] text-xs font-bold hover:bg-[#00FFA3]/20"
                  >
                    Restore
                  </button>
                  <button
                    onClick={() => deleteBackup(backup.id)}
                    className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-xs font-bold hover:bg-red-500/20"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

