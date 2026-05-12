import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { Trophy, TrendingUp, Gamepad2, ChevronLeft, ChevronRight, Crown, Zap, Users, Star } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function SpotlightCard({ icon, accent, label, children }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm p-6 h-full">
      <div className="absolute top-0 right-0 w-40 h-40 rounded-full blur-[80px] opacity-20" style={{ background: accent }} />
      <div className="flex items-center gap-2 mb-5">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${accent}15`, color: accent }}>
          {icon}
        </div>
        <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400" style={{ fontFamily: "Orbitron, sans-serif" }}>{label}</span>
      </div>
      {children}
    </div>
  );
}

function PlayerRow({ rank, name, value, valueLabel, accent }) {
  const medals = { 1: "bg-[#F5D300]/20 text-[#F5D300]", 2: "bg-slate-400/20 text-slate-300", 3: "bg-amber-700/20 text-amber-500" };
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-white/[0.04] last:border-0">
      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${medals[rank] || "bg-white/5 text-slate-500"}`}>
        {rank <= 3 ? <Crown className="w-3 h-3" /> : rank}
      </div>
      <span className="text-sm text-slate-200 flex-1 truncate" style={{ fontFamily: "Space Grotesk, sans-serif" }}>{name}</span>
      <span className="text-xs font-mono font-semibold" style={{ color: accent }}>{value} <span className="text-slate-500 text-[10px]">{valueLabel}</span></span>
    </div>
  );
}

export default function CommunitySpotlight() {
  const [activeSlide, setActiveSlide] = useState(0);
  const [gameLeaderboard, setGameLeaderboard] = useState([]);
  const [traderLeaderboard, setTraderLeaderboard] = useState([]);
  const [platformStats, setPlatformStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [gameRes, traderRes, statsRes] = await Promise.all([
          axios.get(`${API}/leaderboard`).catch(() => ({ data: { leaderboard: [] } })),
          axios.get(`${API}/social-trading/leaderboard?limit=5`).catch(() => ({ data: { leaderboard: [] } })),
          axios.get(`${API}/ai-trader/platform-stats`).catch(() => ({ data: {} })),
        ]);
        setGameLeaderboard((gameRes.data?.leaderboard || []).slice(0, 5));
        setTraderLeaderboard(traderRes.data?.leaderboard || []);
        setPlatformStats(statsRes.data);
      } catch (_) {}
      setLoading(false);
    };
    fetchAll();
    const interval = setInterval(fetchAll, 120000);
    return () => clearInterval(interval);
  }, []);

  const slides = [
    { id: "runners", label: "Top Cosmic Runners" },
    { id: "activity", label: "Platform Activity" },
  ];

  const nextSlide = useCallback(() => setActiveSlide(p => (p + 1) % slides.length), [slides.length]);
  const prevSlide = useCallback(() => setActiveSlide(p => (p - 1 + slides.length) % slides.length), [slides.length]);

  useEffect(() => {
    const timer = setInterval(nextSlide, 8000);
    return () => clearInterval(timer);
  }, [nextSlide]);

  if (loading) return null;

  return (
    <section className="py-16 md:py-20" data-testid="community-spotlight-section">
      <div className="max-w-7xl mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between mb-10">
          <div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight" style={{ fontFamily: "Orbitron, sans-serif" }}>
              Community <span className="text-[#D946EF]">Spotlight</span>
            </h2>
            <p className="text-slate-500 text-sm mt-2" style={{ fontFamily: "Space Grotesk, sans-serif" }}>
              Top guardians and live activity across the Bullpug ecosystem
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-2">
            {slides.map((s, i) => (
              <button
                key={s.id}
                onClick={() => setActiveSlide(i)}
                data-testid={`spotlight-dot-${s.id}`}
                className={`h-1.5 rounded-full transition-all duration-300 ${i === activeSlide ? "w-8 bg-[#D946EF]" : "w-3 bg-white/10 hover:bg-white/20"}`}
              />
            ))}
            <div className="flex items-center gap-1 ml-3">
              <button onClick={prevSlide} data-testid="spotlight-prev-btn" className="w-7 h-7 rounded-full border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/30 transition-colors">
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button onClick={nextSlide} data-testid="spotlight-next-btn" className="w-7 h-7 rounded-full border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/30 transition-colors">
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        <div className="relative overflow-hidden">
          <div className="flex transition-transform duration-500 ease-out" style={{ transform: `translateX(-${activeSlide * 100}%)` }}>
            {slides.map(slide => (
              <div key={slide.id} className="min-w-full w-full flex-shrink-0 px-0.5">
                {slide.id === "runners" && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <SpotlightCard icon={<Gamepad2 className="w-4 h-4" />} accent="#F5D300" label="Cosmic Runner Leaderboard">
                      {gameLeaderboard.length > 0 ? (
                        <div>
                          {gameLeaderboard.map((p, i) => (
                            <PlayerRow key={p.id} rank={i + 1} name={p.player_name} value={p.score} valueLabel="pts" accent="#F5D300" />
                          ))}
                          <Link to="/game" className="block mt-4 text-center text-xs text-[#F5D300]/70 hover:text-[#F5D300] transition-colors" data-testid="spotlight-play-game-link">
                            Play Cosmic Runner &rarr;
                          </Link>
                        </div>
                      ) : (
                        <div className="text-center py-6">
                          <Gamepad2 className="w-8 h-8 text-[#F5D300]/30 mx-auto mb-3" />
                          <p className="text-slate-500 text-xs">No runners yet. Be the first!</p>
                          <Link to="/game" className="inline-block mt-3 text-xs text-[#F5D300] hover:underline">Play Now &rarr;</Link>
                        </div>
                      )}
                    </SpotlightCard>
                    <SpotlightCard icon={<Star className="w-4 h-4" />} accent="#00FFA3" label="Top Moon Cheese Collectors">
                      {gameLeaderboard.length > 0 ? (
                        <div>
                          {[...gameLeaderboard].sort((a, b) => (b.mooncakes || 0) - (a.mooncakes || 0)).map((p, i) => (
                            <PlayerRow key={`mc-${p.id}`} rank={i + 1} name={p.player_name} value={p.mooncakes || 0} valueLabel="cheese" accent="#00FFA3" />
                          ))}
                        </div>
                      ) : (
                        <div className="text-center py-6">
                          <Star className="w-8 h-8 text-[#00FFA3]/30 mx-auto mb-3" />
                          <p className="text-slate-500 text-xs">Collect Moon Cheese in Cosmic Runner!</p>
                        </div>
                      )}
                    </SpotlightCard>
                    <SpotlightCard icon={<Trophy className="w-4 h-4" />} accent="#D946EF" label="Hall of Fame">
                      <div className="space-y-4">
                        {gameLeaderboard.length > 0 && (
                          <div className="relative p-4 rounded-xl bg-gradient-to-br from-[#D946EF]/10 to-transparent border border-[#D946EF]/20">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-[#D946EF]/20 flex items-center justify-center">
                                <Crown className="w-5 h-5 text-[#D946EF]" />
                              </div>
                              <div>
                                <p className="text-xs text-slate-400">Current Champion</p>
                                <p className="text-sm font-bold text-white" style={{ fontFamily: "Space Grotesk" }}>{gameLeaderboard[0]?.player_name}</p>
                                <p className="text-xs font-mono text-[#D946EF]">{gameLeaderboard[0]?.score} pts</p>
                              </div>
                            </div>
                          </div>
                        )}
                        <div className="text-center">
                          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Next Prize Payout</p>
                          <p className="text-xs text-slate-300 font-mono">Every 3 days</p>
                        </div>
                        <Link to="/game" className="block text-center text-xs text-[#D946EF]/70 hover:text-[#D946EF] transition-colors">
                          Claim the throne &rarr;
                        </Link>
                      </div>
                    </SpotlightCard>
                  </div>
                )}

                {slide.id === "activity" && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                    <SpotlightCard icon={<Zap className="w-4 h-4" />} accent="#00C2FF" label="Arena · Live">
                      <div className="space-y-4">
                        {[
                          { label: "Pot SOL (live)", value: (platformStats?.pot_total_sol || 0).toFixed(3), color: "#00C2FF" },
                          { label: "Active Players", value: platformStats?.active_traders || 0, color: "#00FFA3" },
                          { label: "Big Wins (24h)", value: platformStats?.big_wins_24h || 0, color: "#D946EF" },
                        ].map((s, i) => (
                          <div key={i} className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0">
                            <span className="text-xs text-slate-400">{s.label}</span>
                            <span className="text-sm font-bold font-mono" style={{ color: s.color }}>{s.value}</span>
                          </div>
                        ))}
                        <Link to="/betting" className="block text-center text-xs text-[#00C2FF]/70 hover:text-[#00C2FF] transition-colors" data-testid="spotlight-open-arena-link">
                          Enter the Arena &rarr;
                        </Link>
                      </div>
                    </SpotlightCard>
                    <SpotlightCard icon={<Trophy className="w-4 h-4" />} accent="#F5D300" label="Competitions">
                      <div className="text-center py-6">
                        <Trophy className="w-8 h-8 text-[#F5D300]/30 mx-auto mb-3" />
                        <p className="text-lg font-bold text-white mb-1" style={{ fontFamily: "Orbitron" }}>Coming Soon</p>
                        <p className="text-slate-500 text-xs max-w-[200px] mx-auto">Weekly trading competitions with SOL prizes for top performers</p>
                      </div>
                    </SpotlightCard>
                    <SpotlightCard icon={<Users className="w-4 h-4" />} accent="#00FFA3" label="Join the Community">
                      <div className="space-y-3 pt-2">
                        <a href="https://x.com/Bullpugcoin" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-[#00FFA3]/30 transition-colors group" data-testid="spotlight-x-link">
                          <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-slate-400 group-hover:text-white transition-colors">X</div>
                          <div>
                            <p className="text-xs font-semibold text-slate-200">@Bullpugcoin</p>
                            <p className="text-[10px] text-slate-500">Follow for alpha</p>
                          </div>
                        </a>
                        <a href="https://t.me/bullpugcoinchat" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-[#00FFA3]/30 transition-colors group" data-testid="spotlight-telegram-link">
                          <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-slate-400 group-hover:text-white transition-colors">TG</div>
                          <div>
                            <p className="text-xs font-semibold text-slate-200">Telegram Chat</p>
                            <p className="text-[10px] text-slate-500">Join the guardians</p>
                          </div>
                        </a>
                        <Link to="/forum" className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] hover:border-[#00FFA3]/30 transition-colors group" data-testid="spotlight-forum-link">
                          <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-slate-400 group-hover:text-white transition-colors">
                            <Users className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-slate-200">Bullpug Forum</p>
                            <p className="text-[10px] text-slate-500">Discuss strategies</p>
                          </div>
                        </Link>
                      </div>
                    </SpotlightCard>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex sm:hidden items-center justify-center gap-2 mt-6">
          {slides.map((s, i) => (
            <button
              key={s.id}
              onClick={() => setActiveSlide(i)}
              className={`h-1.5 rounded-full transition-all duration-300 ${i === activeSlide ? "w-8 bg-[#D946EF]" : "w-3 bg-white/10"}`}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
