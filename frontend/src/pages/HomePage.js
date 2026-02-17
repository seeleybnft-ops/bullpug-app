import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Rocket, Shield, Zap, Coins, BarChart3, Gamepad2, ShoppingCart, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const IMAGES = {
  hero: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/7x0weeyi_download%20-%202026-02-17T063439.078.png",
  game: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/kynwxxke_image%20-%202026-02-17T063523.593.jpg",
  trader: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/21uetroq__b0085b46-ef12-44f5-a395-fe4cf39e34bf.jfif",
  birthday: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/5w17pptk__eda5997e-289f-4f2c-916b-329017a171d6.jfif",
  maid: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/2sae826h_25.10.2024_17.06.12_REC.png",
};

const GALLERY = [
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.01.54_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/09.10.2024_19.19.17_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.02.50_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.02.38_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.03.28_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.04.59_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.06.12_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.10.27_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.07.25_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.11.16_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.11.45_rec.png",
  "https://bullpug.com/wp-content/uploads/2024/10/25.10.2024_17.14.33_rec.png",
];

const TOKEN_DIST = [
  { name: "Community & Liquidity", value: 80, color: "#00FFA3" },
  { name: "Marketing", value: 10, color: "#D946EF" },
  { name: "Developer Team", value: 5, color: "#F5D300" },
  { name: "Ecosystem Reserve", value: 5, color: "#00C2FF" },
];

const ROADMAP = [
  { phase: "Phase 1", title: "Launch", date: "Q1 2026", items: ["Initial lore reveal", "Community building", "Website launch", "Fair launch via Blowfishbot"], status: "current" },
  { phase: "Phase 2", title: "Ecosystem Build", date: "Q2-Q3 2026", items: ["Speed-run game rollout", "Betting arena beta", "Plushie store launch", "Staking activation"], status: "upcoming" },
  { phase: "Phase 3", title: "Expansion", date: "Q4 2026+", items: ["NFT collection", "Governance implementation", "Full betting platform", "Strategic partnerships"], status: "upcoming" },
];

export default function HomePage() {
  const [email, setEmail] = useState("");
  const [stats, setStats] = useState(null);
  const [subscribing, setSubscribing] = useState(false);

  useEffect(() => {
    axios.get(`${API}/tokenomics/stats`).then(r => setStats(r.data)).catch(() => {});
  }, []);

  const handleSubscribe = async () => {
    if (!email) return toast.error("Enter your email");
    setSubscribing(true);
    try {
      const { data } = await axios.post(`${API}/newsletter/subscribe`, { email });
      toast.success(data.message);
      setEmail("");
    } catch (e) {
      toast.error("Subscription failed");
    }
    setSubscribing(false);
  };

  return (
    <div className="pt-16">
      <div className="stars-bg fixed inset-0 -z-10" />

      {/* HERO */}
      <section className="relative min-h-screen flex items-center py-24 md:py-32" data-testid="hero-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6 animate-slide-up">
            <Badge className="bg-[#00FFA3]/10 text-[#00FFA3] border border-[#00FFA3]/30 uppercase tracking-widest text-xs px-4 py-1.5 rounded-full">
              Loyal Guardian of the Memecoin Universe
            </Badge>
            <h1 className="text-5xl sm:text-6xl lg:text-8xl font-black tracking-tighter uppercase leading-none" style={{ fontFamily: 'Orbitron, sans-serif' }}>
              <span className="text-white">BULL</span>
              <span className="text-[#00FFA3] neon-text">PUG</span>
            </h1>
            <p className="text-base md:text-lg text-slate-300 max-w-lg leading-relaxed" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Meet Bullpug, the fearless and loyal guardian of the Memecoin Universe. Born from a cosmic mix-up when the stars of the Bull constellation collided with the energy of a pug-shaped nebula.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/betting">
                <Button data-testid="hero-betting-btn" className="bg-[#00FFA3] text-black font-bold uppercase tracking-wider hover:scale-105 transition-transform shadow-[0_0_20px_rgba(0,255,163,0.4)] rounded-full px-8 py-5 text-sm">
                  <Zap className="w-4 h-4 mr-2" /> Enter Arena
                </Button>
              </Link>
              <Link to="/game">
                <Button data-testid="hero-game-btn" variant="outline" className="border-2 border-[#F5D300] text-[#F5D300] hover:bg-[#F5D300]/10 rounded-full px-8 py-5 text-sm font-bold uppercase tracking-wider">
                  <Gamepad2 className="w-4 h-4 mr-2" /> Play Game
                </Button>
              </Link>
            </div>
            <div className="flex gap-4 pt-2">
              <a href="https://x.com/Bullpugcoin" target="_blank" rel="noopener noreferrer" data-testid="hero-x-link" className="text-slate-500 hover:text-[#00FFA3] transition-colors text-sm">@bullpugcoin</a>
              <a href="https://t.me/bullpugcoinchat" target="_blank" rel="noopener noreferrer" data-testid="hero-telegram-link" className="text-slate-500 hover:text-[#00FFA3] transition-colors text-sm">Telegram</a>
            </div>
          </div>
          <div className="relative flex justify-center">
            <div className="absolute inset-0 bg-[#00FFA3]/5 rounded-full blur-[120px]" />
            <img src={IMAGES.hero} alt="Bullpug Guardian" className="relative z-10 w-[350px] h-[350px] md:w-[480px] md:h-[480px] object-contain animate-float drop-shadow-[0_0_50px_rgba(0,255,163,0.25)]" />
          </div>
        </div>
      </section>

      {/* LORE */}
      <section className="py-24 md:py-32" data-testid="lore-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-center mb-4" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            The <span className="text-[#D946EF]">Legend</span>
          </h2>
          <p className="text-center text-slate-500 mb-16 max-w-xl mx-auto text-sm" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>The origin story of the most powerful guardian in the memecoin universe</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { icon: <Shield className="w-7 h-7 text-[#00FFA3]" />, title: "The Collision", desc: "The mighty Bull constellation collided with a whimsical pug-shaped nebula, infusing raw power with endearing loyalty." },
              { icon: <Moon className="w-7 h-7 text-[#D946EF]" />, title: "The Guardian Rises", desc: "Bullpug patrols the blockchain, shielding holders from bearish threats and guiding them toward bullish horizons." },
              { icon: <Zap className="w-7 h-7 text-[#F5D300]" />, title: "Become a Guardian (Coming Soon)", desc: "Holders become 'Guardians,' earning rewards through participation. Staking tokens unlocks chapters of evolving lore." },
            ].map((item, i) => (
              <div key={i} className="glass-card rounded-2xl p-8 hover:-translate-y-1 transition-all duration-300">
                <div className="mb-4">{item.icon}</div>
                <h3 className="text-lg font-bold mb-3" style={{ fontFamily: 'Orbitron, sans-serif' }}>{item.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="py-24 md:py-32" data-testid="features-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-center mb-16" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            <span className="text-[#00FFA3]">Ecosystem</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: <Zap size={18} />, title: "Betting Arena", desc: "Provably fair coin toss & winner-take-all pots", link: "/betting", img: IMAGES.trader, color: "#00FFA3" },
              { icon: <Gamepad2 size={18} />, title: "Speed Run Game", desc: "Navigate cosmic challenges as Bullpug, collect Mooncake", link: "/game", img: IMAGES.game, color: "#F5D300" },
              { icon: <BarChart3 size={18} />, title: "Exit Simulator", desc: "Monte Carlo simulations for exit strategies", link: "/exit-simulator", img: IMAGES.birthday, color: "#00C2FF" },
            ].map((f, i) => (
              <Link to={f.link} key={i} className="group" data-testid={`feature-card-${i}`}>
                <div className="glass-card rounded-2xl overflow-hidden hover:-translate-y-1 transition-all duration-300">
                  <div className="h-44 overflow-hidden relative">
                    <img src={f.img} alt={f.title} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#05050A] via-transparent to-transparent" />
                  </div>
                  <div className="p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <span style={{ color: f.color }}>{f.icon}</span>
                      <h3 className="font-bold text-xs uppercase tracking-wider" style={{ fontFamily: 'Orbitron, sans-serif' }}>{f.title}</h3>
                    </div>
                    <p className="text-slate-500 text-xs">{f.desc}</p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* TOKENOMICS */}
      <section className="py-24 md:py-32" data-testid="tokenomics-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-center mb-4" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            Token<span className="text-[#F5D300]">omics</span>
          </h2>
          <p className="text-center text-slate-500 mb-16 text-sm">1 Billion $BULLPUG tokens with deflationary mechanics</p>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-5 glass-card rounded-2xl p-6">
              <h3 className="text-base font-bold mb-4" style={{ fontFamily: 'Orbitron, sans-serif' }}>Supply Distribution</h3>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={TOKEN_DIST} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={4} dataKey="value" stroke="none">
                      {TOKEN_DIST.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: '#13131F', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, color: '#fff', fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-3">
                {TOKEN_DIST.map((d, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-slate-400">
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: d.color }} />
                    <span>{d.name} ({d.value}%)</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="lg:col-span-7 grid grid-cols-2 gap-4">
              {[
                { label: "Total Supply", value: "1,000,000,000", sub: "$BULLPUG" },
                { label: "Burned", value: stats ? `${(stats.burned / 1e6).toFixed(1)}M` : "12.5M", sub: "tokens burned" },
                { label: "Holders", value: stats?.holders?.toLocaleString() || "1,247", sub: "guardians" },
                { label: "Market Cap", value: `$${(stats?.market_cap || 420000).toLocaleString()}`, sub: "and growing" },
              ].map((s, i) => (
                <div key={i} className="glass-card rounded-2xl p-5 hover:border-[#00FFA3]/30 transition-colors">
                  <p className="text-[10px] uppercase tracking-widest text-slate-600 mb-1" style={{ fontFamily: 'Orbitron, sans-serif' }}>{s.label}</p>
                  <p className="text-xl md:text-2xl font-black text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>{s.value}</p>
                  <p className="text-xs text-slate-600 mt-1">{s.sub}</p>
                </div>
              ))}
              <div className="col-span-2 glass-card rounded-2xl p-5">
                <h4 className="text-xs font-bold mb-3 uppercase tracking-wider text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>Transaction Tax: 5%</h4>
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: "Burn", value: "2%", color: "#FF3B30" },
                    { label: "Reflections", value: "2%", color: "#00FFA3" },
                    { label: "Liquidity", value: "1%", color: "#00C2FF" },
                  ].map((t, i) => (
                    <div key={i} className="text-center">
                      <div className="text-xl font-black" style={{ color: t.color, fontFamily: 'Orbitron, sans-serif' }}>{t.value}</div>
                      <div className="text-xs text-slate-500">{t.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* GALLERY */}
      <section className="py-24 md:py-32" data-testid="gallery-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-center mb-16" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            BULLPUG <span className="text-[#D946EF]">Gallery</span>
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {GALLERY.map((img, i) => (
              <div key={i} className="rounded-xl overflow-hidden border border-white/5 hover:border-[#D946EF]/40 transition-all duration-300 group">
                <img src={img} alt={`Bullpug #${i + 1}`} className="w-full h-44 object-cover group-hover:scale-110 transition-transform duration-500" loading="lazy" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ROADMAP */}
      <section className="py-24 md:py-32" data-testid="roadmap-section">
        <div className="max-w-3xl mx-auto px-6 md:px-12">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-center mb-16" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            Road<span className="text-[#00FFA3]">map</span>
          </h2>
          <div className="relative">
            <div className="absolute left-4 md:left-1/2 md:-translate-x-px top-0 bottom-0 w-0.5 bg-gradient-to-b from-[#00FFA3] via-[#D946EF] to-[#F5D300]" />
            {ROADMAP.map((phase, i) => (
              <div key={i} className="relative pl-12 md:pl-0 mb-12">
                <div className="absolute left-4 md:left-1/2 w-3 h-3 rounded-full border-2 border-[#00FFA3] bg-[#05050A] -translate-x-1/2 mt-2 z-10 shadow-[0_0_10px_rgba(0,255,163,0.5)]" />
                <div className={`md:w-5/12 ${i % 2 === 0 ? 'md:ml-auto md:pl-8' : 'md:mr-auto md:pr-8'}`}>
                  <div className="glass-card rounded-2xl p-5 hover:border-[#00FFA3]/30 transition-colors">
                    <Badge className={`mb-3 text-[10px] ${phase.status === 'current' ? 'bg-[#00FFA3]/10 text-[#00FFA3] border-[#00FFA3]/30' : 'bg-white/5 text-slate-500 border-white/10'}`}>
                      {phase.phase} - {phase.date}
                    </Badge>
                    <h3 className="text-lg font-bold mb-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>{phase.title}</h3>
                    <ul className="space-y-1">
                      {phase.items.map((item, j) => (
                        <li key={j} className="text-xs text-slate-400 flex items-center gap-1.5">
                          <Rocket className="w-3 h-3 text-[#00FFA3] flex-shrink-0" /> {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* NEWSLETTER */}
      <section className="py-24 md:py-32" data-testid="newsletter-section">
        <div className="max-w-xl mx-auto px-6 md:px-12 text-center">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-4" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            Subscribe for <span className="text-[#D946EF]">Protection</span>
          </h2>
          <p className="text-slate-500 mb-8 text-sm">Join the Guardian newsletter for launch updates, events, and exclusive content.</p>
          <div className="flex gap-3">
            <Input
              type="email" placeholder="guardian@email.com" value={email}
              onChange={e => setEmail(e.target.value)}
              data-testid="newsletter-email-input"
              className="bg-black/50 border-white/10 rounded-full px-5 text-white placeholder-slate-600 focus:border-[#00FFA3] focus:ring-[#00FFA3]"
            />
            <Button onClick={handleSubscribe} disabled={subscribing} data-testid="newsletter-subscribe-btn"
              className="bg-[#00FFA3] text-black font-bold rounded-full px-6 hover:scale-105 transition-transform shadow-[0_0_20px_rgba(0,255,163,0.4)] flex-shrink-0">
              {subscribing ? "..." : "Subscribe"}
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
