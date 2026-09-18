/**
 * PendingJournalEntries Component
 * Displays auto-trade entries awaiting user review/completion
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Clock, Zap, TrendingUp, TrendingDown, Edit2, CheckCircle, 
  AlertCircle, Sparkles, Brain, Target, MessageSquare
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EMOTION_OPTIONS = [
  { value: "confident", label: "Confident", color: "#00FFA3" },
  { value: "calm", label: "Calm", color: "#00C2FF" },
  { value: "excited", label: "Excited", color: "#D946EF" },
  { value: "anxious", label: "Anxious", color: "#FFB800" },
  { value: "fearful", label: "Fearful", color: "#FF6B6B" },
  { value: "fomo", label: "FOMO", color: "#FF8C00" },
  { value: "neutral", label: "Neutral", color: "#94A3B8" },
  { value: "frustrated", label: "Frustrated", color: "#EF4444" },
];

const GRADE_OPTIONS = ["A+", "A", "B+", "B", "C", "D", "F"];

export default function PendingJournalEntries({ entries, onComplete, onRefresh }) {
  const [expandedEntry, setExpandedEntry] = useState(null);
  const [formData, setFormData] = useState({});
  const [saving, setSaving] = useState(false);

  if (!entries || entries.length === 0) {
    return null;
  }

  const handleExpand = (tradeId) => {
    if (expandedEntry === tradeId) {
      setExpandedEntry(null);
    } else {
      setExpandedEntry(tradeId);
      // Initialize form data with existing entry data
      const entry = entries.find(e => e.trade_id === tradeId);
      if (entry) {
        setFormData({
          emotion_entry: entry.emotion_entry || "",
          entry_reason: entry.entry_reason || "",
          strategy: entry.strategy || "",
          confidence_level: entry.confidence_level || 5,
          mindset_notes: entry.mindset_notes || "",
          what_went_well: entry.what_went_well || "",
          what_went_wrong: entry.what_went_wrong || "",
          lessons: entry.lessons || "",
          trade_grade: entry.trade_grade || "",
        });
      }
    }
  };

  const handleSave = async (tradeId) => {
    setSaving(true);
    try {
      await axios.put(`${API}/journal/pending/${tradeId}/complete`, formData);
      toast.success("Journal entry completed!");
      setExpandedEntry(null);
      if (onComplete) onComplete();
      if (onRefresh) onRefresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save entry");
    }
    setSaving(false);
  };

  const getTimeRemaining = (autoLoggedAt) => {
    const logged = new Date(autoLoggedAt);
    const expires = new Date(logged.getTime() + 24 * 60 * 60 * 1000);
    const now = new Date();
    const remaining = expires - now;
    
    if (remaining <= 0) return "Expiring soon";
    
    const hours = Math.floor(remaining / (1000 * 60 * 60));
    const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${hours}h ${minutes}m remaining`;
  };

  return (
    <div className="mb-6" data-testid="pending-journal-entries">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-[#D946EF]/20 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-[#D946EF]" />
          </div>
          <div>
            <h3 className="font-bold text-white">Pending Journal Entries</h3>
            <p className="text-xs text-slate-500">Auto-trades waiting for your review</p>
          </div>
        </div>
        <Badge className="bg-[#D946EF]/20 text-[#D946EF] animate-pulse">
          {entries.length} pending
        </Badge>
      </div>

      {/* Entries */}
      <div className="space-y-3">
        {entries.map(entry => {
          const isExpanded = expandedEntry === entry.trade_id;
          const isBuy = entry.trade_type === "buy";
          const isProfitable = (entry.pnl || 0) >= 0;
          
          return (
            <div 
              key={entry.trade_id}
              className={`rounded-xl border-2 transition-all ${
                isExpanded 
                  ? "border-[#D946EF] bg-[#D946EF]/5" 
                  : "border-[#D946EF]/30 bg-[#D946EF]/5 hover:border-[#D946EF]/50"
              }`}
              data-testid={`pending-entry-${entry.trade_id}`}
            >
              {/* Entry Header */}
              <div 
                className="p-4 cursor-pointer"
                onClick={() => handleExpand(entry.trade_id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                      isBuy ? "bg-[#00C2FF]/20" : isProfitable ? "bg-[#00FFA3]/20" : "bg-[#FF6B6B]/20"
                    }`}>
                      {isBuy ? (
                        <TrendingUp className="w-6 h-6 text-[#00C2FF]" />
                      ) : isProfitable ? (
                        <TrendingUp className="w-6 h-6 text-[#00FFA3]" />
                      ) : (
                        <TrendingDown className="w-6 h-6 text-[#FF6B6B]" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-lg">{entry.asset}</span>
                        <Badge className={`text-xs ${isBuy ? "bg-[#00C2FF]/20 text-[#00C2FF]" : "bg-[#FF6B6B]/20 text-[#FF6B6B]"}`}>
                          {isBuy ? "BUY" : "SELL"}
                        </Badge>
                        <Badge className="bg-[#D946EF]/20 text-[#D946EF] text-xs">
                          <Zap className="w-3 h-3 mr-1" />
                          Auto-Trade
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        {new Date(entry.date_entry).toLocaleString()} | ${entry.entry_price?.toFixed(6)} | {entry.position_size} SOL
                      </p>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    {!isBuy && entry.pnl_percent !== undefined && (
                      <p className={`font-mono font-bold text-lg ${isProfitable ? "text-[#00FFA3]" : "text-[#FF6B6B]"}`}>
                        {isProfitable ? "+" : ""}{entry.pnl_percent?.toFixed(2)}%
                      </p>
                    )}
                    <div className="flex items-center gap-1 text-xs text-[#D946EF] mt-1">
                      <Clock className="w-3 h-3" />
                      {getTimeRemaining(entry.auto_logged_at)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Expanded Form */}
              {isExpanded && (
                <div className="px-4 pb-4 border-t border-[#D946EF]/20 pt-4 space-y-4">
                  {/* Emotion Selection - Multiple Choice */}
                  <div>
                    <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                      <Brain className="w-4 h-4" />
                      How were you feeling? (Select all that apply)
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {EMOTION_OPTIONS.map(emotion => {
                        const emotions = formData.emotion_entry ? formData.emotion_entry.split(',') : [];
                        const isSelected = emotions.includes(emotion.value);
                        return (
                          <button
                            key={emotion.value}
                            onClick={() => {
                              let newEmotions;
                              if (isSelected) {
                                newEmotions = emotions.filter(e => e !== emotion.value);
                              } else {
                                newEmotions = [...emotions, emotion.value];
                              }
                              setFormData(prev => ({ 
                                ...prev, 
                                emotion_entry: newEmotions.join(',') 
                              }));
                            }}
                            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                              isSelected
                                ? "ring-2 ring-white"
                                : "opacity-70 hover:opacity-100"
                            }`}
                            style={{ 
                              backgroundColor: `${emotion.color}20`, 
                              color: emotion.color 
                            }}
                          >
                            {emotion.label}
                          </button>
                        );
                      })}
                    </div>
                    {formData.emotion_entry && (
                      <p className="text-xs text-slate-500 mt-2">
                        Selected: {formData.emotion_entry.split(',').map(e => 
                          EMOTION_OPTIONS.find(o => o.value === e)?.label
                        ).filter(Boolean).join(', ')}
                      </p>
                    )}
                  </div>

                  {/* Entry Reason */}
                  <div>
                    <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                      <Target className="w-4 h-4" />
                      What did you think about this trade?
                    </label>
                    <textarea
                      value={formData.entry_reason || ""}
                      onChange={(e) => setFormData(prev => ({ ...prev, entry_reason: e.target.value }))}
                      placeholder="Your thoughts on this trade, market conditions, or anything notable..."
                      className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:border-[#D946EF] focus:outline-none resize-none"
                      rows={2}
                    />
                  </div>

                  {/* Confidence Level */}
                  <div>
                    <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                      <Sparkles className="w-4 h-4" />
                      Confidence Level: {formData.confidence_level || 5}/10
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={formData.confidence_level || 5}
                      onChange={(e) => setFormData(prev => ({ ...prev, confidence_level: parseInt(e.target.value) }))}
                      className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer accent-[#D946EF]"
                    />
                  </div>

                  {/* Strategy - Auto-filled from trade trigger */}
                  <div>
                    <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                      Trade Trigger / Strategy
                      {entry.strategy && <Badge className="bg-[#00FFA3]/20 text-[#00FFA3] text-[10px]">Auto-filled</Badge>}
                    </label>
                    <input
                      type="text"
                      value={formData.strategy || ""}
                      onChange={(e) => setFormData(prev => ({ ...prev, strategy: e.target.value }))}
                      placeholder="e.g., Momentum breakout, Take-profit triggered, AI signal"
                      className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:border-[#D946EF] focus:outline-none"
                    />
                  </div>

                  {/* Mindset Notes */}
                  <div>
                    <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                      <MessageSquare className="w-4 h-4" />
                      Additional Notes
                    </label>
                    <textarea
                      value={formData.mindset_notes || ""}
                      onChange={(e) => setFormData(prev => ({ ...prev, mindset_notes: e.target.value }))}
                      placeholder="Any other thoughts, observations, or notes about this trade..."
                      className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:border-[#D946EF] focus:outline-none resize-none"
                      rows={2}
                    />
                  </div>

                  {/* For sells - add reflection fields */}
                  {!isBuy && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-sm text-slate-400 mb-2 block">What went well?</label>
                          <textarea
                            value={formData.what_went_well || ""}
                            onChange={(e) => setFormData(prev => ({ ...prev, what_went_well: e.target.value }))}
                            placeholder="Positive aspects..."
                            className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:border-[#00FFA3] focus:outline-none resize-none"
                            rows={2}
                          />
                        </div>
                        <div>
                          <label className="text-sm text-slate-400 mb-2 block">What could improve?</label>
                          <textarea
                            value={formData.what_went_wrong || ""}
                            onChange={(e) => setFormData(prev => ({ ...prev, what_went_wrong: e.target.value }))}
                            placeholder="Areas for improvement..."
                            className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:border-[#FF6B6B] focus:outline-none resize-none"
                            rows={2}
                          />
                        </div>
                      </div>

                      <div>
                        <label className="text-sm text-slate-400 mb-2 block">Key Lessons</label>
                        <textarea
                          value={formData.lessons || ""}
                          onChange={(e) => setFormData(prev => ({ ...prev, lessons: e.target.value }))}
                          placeholder="What did you learn from this trade?"
                          className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:border-[#D946EF] focus:outline-none resize-none"
                          rows={2}
                        />
                      </div>

                      <div>
                        <label className="text-sm text-slate-400 mb-2 block">Trade Grade</label>
                        <div className="flex gap-2">
                          {GRADE_OPTIONS.map(grade => (
                            <button
                              key={grade}
                              onClick={() => setFormData(prev => ({ ...prev, trade_grade: grade }))}
                              className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                                formData.trade_grade === grade
                                  ? "bg-[#D946EF] text-white"
                                  : "bg-white/5 text-slate-400 hover:bg-white/10"
                              }`}
                            >
                              {grade}
                            </button>
                          ))}
                        </div>
                      </div>
                    </>
                  )}

                  {/* Action Buttons */}
                  <div className="flex items-center justify-between pt-4 border-t border-white/10">
                    <p className="text-xs text-slate-500">
                      <AlertCircle className="w-3 h-3 inline mr-1" />
                      Fields are optional. Entry will auto-log after 24 hours.
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => setExpandedEntry(null)}
                        className="border-white/20 text-slate-400"
                      >
                        Cancel
                      </Button>
                      <Button
                        onClick={() => handleSave(entry.trade_id)}
                        disabled={saving}
                        className="bg-gradient-to-r from-[#D946EF] to-[#00C2FF] text-white"
                      >
                        {saving ? (
                          <span className="flex items-center gap-2">
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Saving...
                          </span>
                        ) : (
                          <span className="flex items-center gap-2">
                            <CheckCircle className="w-4 h-4" />
                            Complete Entry
                          </span>
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
