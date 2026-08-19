import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useWallet } from "@solana/wallet-adapter-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Rocket, Shield, Zap, Coins, BarChart3, Gamepad2, ShoppingCart, Moon, Bot, Flame, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import axios from "axios";
import RecentWinners from "@/components/RecentWinners";
import MarketDashboard from "@/components/MarketDashboard";
import JackpotTicker from "@/components/JackpotTicker";
import LatestDropWidget from "@/components/LatestDropWidget";
import CommunitySpotlight from "@/components/CommunitySpotlight";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const IMAGES = {
  hero: "/bullpug-canon.jpg",
  game: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/kynwxxke_image%20-%202026-02-17T063523.593.jpg",
  trader: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/21uetroq__b0085b46-ef12-44f5-a395-fe4cf39e34bf.jfif",
  birthday: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/5w17pptk__eda5997e-289f-4f2c-916b-329017a171d6.jfif",
  maid: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/2sae826h_25.10.2024_17.06.12_REC.png",
  journal: "/images/journal-bullpug.jfif",
  aiAssistant: "https://customer-assets.emergentagent.com/job_7cd24e51-411f-4346-a028-e9b4e7530f5e/artifacts/sf7c7buf__6edaf5e6-8d3a-4e67-ae26-f940b4cae7df.jfif",
  tradingBot: "https://customer-assets.emergentagent.com/job_eece36b0-bd7c-41e3-9663-864558bfa54c/artifacts/79azcfdc_image%20-%202026-03-04T094746.318.jpg",
  origins: "/bullpug-canon.jpg",
  arena: "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/21uetroq__b0085b46-ef12-44f5-a395-fe4cf39e34bf.jfif",
};

const GALLERY = [
  "https://customer-assets.emergentagent.com/job_5d6a5e00-50cf-4b65-9a94-df993e3bd9bc/artifacts/hx8owqo5__0b33bdf6-ff6f-4e81-b054-8864266da936.jfif",
  "https://customer-assets.emergentagent.com/job_5d6a5e00-50cf-4b65-9a94-df993e3bd9bc/artifacts/dlqanw32__6edaf5e6-8d3a-4e67-ae26-f940b4cae7df.jfif",
  "https://customer-assets.emergentagent.com/job_5d6a5e00-50cf-4b65-9a94-df993e3bd9bc/artifacts/8722rrxo__19eae00a-c32d-4598-8368-2b9a2cea09f5.jfif",
  "https://customer-assets.emergentagent.com/job_5d6a5e00-50cf-4b65-9a94-df993e3bd9bc/artifacts/ehdeto17__22f76edb-e23d-4bcb-8f0d-2dcbf2d49f75.jfif",
  "https://customer-assets.emergentagent.com/job_5d6a5e00-50cf-4b65-9a94-df993e3bd9bc/artifacts/jx1varuz__330ee0eb-9f7e-4e7c-8eb6-4e3508d2dca4.jfif",
  "https://customer-assets.emergentagent.com/job_5d6a5e00-50cf-4b65-9a94-df993e3bd9bc/artifacts/lbpfaqyq__767efd96-bade-40da-a2e8-e10982c35987.jfif",
];

const TOKEN_DIST = [
  { name: "Liquidity Pool", value: 100, color: "#00FFA3" },
];

// Roadmap — Blowfish reference removed pending clarification;
// Speed Run Game item parked during private testing period.
const ROADMAP = [
  { phase: "Phase 1", title: "Launch", date: "Q1 2026", items: ["Community Building", "Website launch", "Initial lore reveal", "Tinkerpug AI assistant"], status: "current" },
  { phase: "Phase 2", title: "Ecosystem Build", date: "Q2-Q3 2026", items: ["Staking activation", "NFT collection", "Plushie store launch", "Governance implementation", "Strategic partnerships"], status: "upcoming" },
  { phase: "Phase 3", title: "Expansion", date: "Q4 2026", items: ["More to come"], status: "upcoming" },
];

export default function HomePage() {
  const [email, setEmail] = useState("");
  const [stats, setStats] = useState(null);
  const [subscribing, setSubscribing] = useState(false);
  // PugBurn live-fetch — surfaces the connected wallet's reclaimable SOL
  // right in the promo strip, so the hook becomes a personalised CTA.
  const { publicKey } = useWallet();
  const walletAddress = publicKey?.toString();
  const [pugBurnScan, setPugBurnScan] = useState(null); // { count, sol }

  useEffect(() => {
    if (!walletAddress) {
      setPugBurnScan(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const { data } = await axios.get(`${API}/pugburn/scan/${walletAddress}`);
        if (cancelled) return;
        const sol = Number(data?.total_reclaimable_sol || 0);
        const count = data?.vacant_accounts?.length || 0;
        setPugBurnScan({ sol, count });
      } catch (e) {
        if (!cancelled) setPugBurnScan(null);
      }
    })();
    return () => { cancelled = true; };
  }, [walletAddress]);

  useEffect(() => {
    axios.get(`${API}/tokenomics/stats`).then(r => setStats(r.data)).catch(() => {});
  }, []);

  // Bullpug Gallery — live-fetch daily drops + user-generated images, then
  // cycle a rolling 8-tile window every ~6 seconds so the grid feels alive
  // as new drops land. Falls back to the static GALLERY placeholders when
  // the API returns nothing yet (fresh deploy) or the request fails.
  const [galleryFeed, setGalleryFeed] = useState([]);
  const [galleryOffset, setGalleryOffset] = useState(0);
  useEffect(() => {
    let cancelled = false;
    axios
      .get(`${API}/ai/gallery/recent?limit=24`)
      .then((r) => {
        if (cancelled) return;
        const items = (r.data?.images || [])
          .filter((it) => typeof it.image_base64 === "string" && it.image_base64.length > 32);
        setGalleryFeed(items);
      })
      .catch(() => { /* fall through to static placeholders */ });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    if (galleryFeed.length <= 8) return;
    const t = setInterval(() => {
      setGalleryOffset((o) => (o + 1) % galleryFeed.length);
    }, 6000);
    return () => clearInterval(t);
  }, [galleryFeed.length]);

  // Compose the 8 tiles rendered on the page — either a rolling slice of the
  // live feed or the static GALLERY fallback so the section never looks empty.
  const galleryTiles = (() => {
    const TILES = 8;
    if (galleryFeed.length === 0) {
      return GALLERY.slice(0, TILES).map((src, i) => ({
        key: `static-${i}`,
        src,
        alt: `Bullpug #${i + 1}`,
        source: "static",
      }));
    }
    const out = [];
    for (let i = 0; i < TILES; i++) {
      const item = galleryFeed[(galleryOffset + i) % galleryFeed.length];
      out.push({
        key: `${item.src}-${item.created_at}-${i}`,
        src: item.image_base64,
        alt: item.caption || `Bullpug gallery #${i + 1}`,
        source: item.src, // "daily_drop" | "user"
      });
    }
    return out;
  })();

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
              {/* Cosmic Runner CTA parked during private testing — will
                  return when the game re-launches. */}
              <Button
                onClick={() => window.dispatchEvent(new CustomEvent("tinkerpug:open"))}
                data-testid="hero-tinkerpug-btn"
                className="bg-[#00FFA3] text-black font-bold uppercase tracking-wider hover:scale-105 transition-transform shadow-[0_0_20px_rgba(0,255,163,0.4)] rounded-full px-8 py-5 text-sm"
              >
                <Bot className="w-4 h-4 mr-2" /> Ask Tinkerpug
              </Button>
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

      {/* PUGBURN PROMO STRIP — hides when a connected wallet has nothing
          to reclaim, becomes personalised when it does. */}
      {!(pugBurnScan && pugBurnScan.count === 0) && (
      <section className="py-6 md:py-8" data-testid="pugburn-promo-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <Link
            to="/pugburn"
            data-testid="pugburn-promo-card"
            className="group relative block overflow-hidden rounded-2xl border border-[#FF6B6B]/30 bg-gradient-to-r from-[#1a0a0a]/80 via-[#0f0518]/80 to-[#1a0a0a]/80 backdrop-blur-md hover:border-[#FF6B6B]/60 transition-all hover:shadow-[0_0_40px_rgba(255,107,107,0.25)]"
          >
            {/* Animated ember glow */}
            <div className="absolute inset-0 pointer-events-none">
              <div className="absolute -left-10 top-1/2 -translate-y-1/2 w-40 h-40 rounded-full bg-[#FF6B6B]/20 blur-3xl animate-pulse" />
              <div className="absolute -right-10 top-1/2 -translate-y-1/2 w-40 h-40 rounded-full bg-[#F5D300]/10 blur-3xl" />
            </div>

            <div className="relative flex flex-col sm:flex-row items-stretch gap-4 sm:gap-6 p-5 sm:p-6">
              {/* Icon block */}
              <div className="flex items-center justify-center sm:flex-shrink-0">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#FF6B6B] to-[#F5D300] flex items-center justify-center shadow-[0_0_30px_rgba(255,107,107,0.45)] group-hover:scale-110 transition-transform">
                  <Flame className="w-8 h-8 text-black" strokeWidth={2.5} />
                </div>
              </div>

              {/* Copy */}
              <div className="flex-1 min-w-0 text-center sm:text-left">
                <div className="flex items-center justify-center sm:justify-start gap-2 mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-[0.25em] text-[#FF6B6B]" style={{ fontFamily: "Orbitron" }}>
                    {pugBurnScan && pugBurnScan.sol > 0
                      ? "Reclaimable · Just For You"
                      : "Hidden SOL · Free Tool"}
                  </span>
                  {!(pugBurnScan && pugBurnScan.sol > 0) && (
                    <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#F5D300]/15 border border-[#F5D300]/30 text-[#F5D300] text-[10px] font-bold">
                      NEW
                    </span>
                  )}
                  {pugBurnScan && pugBurnScan.sol > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#00FFA3]/15 border border-[#00FFA3]/40 text-[#00FFA3] text-[10px] font-bold animate-pulse" data-testid="pugburn-promo-live-badge">
                      ● LIVE
                    </span>
                  )}
                </div>
                {pugBurnScan && pugBurnScan.sol > 0 ? (
                  <>
                    <h3 className="text-lg sm:text-xl md:text-2xl font-black text-white mb-1" style={{ fontFamily: "Orbitron" }} data-testid="pugburn-promo-headline">
                      You have <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#FFD86B] via-[#F5D300] to-[#FF6B6B]">{pugBurnScan.sol.toFixed(4)} SOL</span> to reclaim
                    </h3>
                    <p className="text-xs sm:text-sm text-slate-400">
                      <span className="text-white font-semibold">{pugBurnScan.count}</span>
                      {pugBurnScan.count === 1 ? " empty token account is " : " empty token accounts are "}
                      locking your SOL. Close them in one click. No fees.
                    </p>
                  </>
                ) : (
                  <>
                    <h3 className="text-lg sm:text-xl font-black text-white mb-1" style={{ fontFamily: "Orbitron" }}>
                      Reclaim SOL from your empty token accounts
                    </h3>
                    <p className="text-xs sm:text-sm text-slate-400">
                      Every old airdrop / dust account locks <span className="text-[#F5D300] font-semibold">~0.002 SOL</span>. PugBurn finds them and gives the SOL back to you. No fees.
                    </p>
                  </>
                )}
              </div>

              {/* CTA */}
              <div className="flex items-center justify-center sm:flex-shrink-0">
                <span className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-[#FF6B6B] text-black font-black uppercase tracking-wider text-xs group-hover:bg-[#F5D300] transition-colors" style={{ fontFamily: "Orbitron" }}>
                  {pugBurnScan && pugBurnScan.sol > 0 ? "Reclaim Now" : "Scan My Wallet"}
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </span>
              </div>
            </div>
          </Link>
        </div>
      </section>
      )}

      {/* MARKET DASHBOARD */}
      <section className="py-12 md:py-16" data-testid="market-dashboard-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 glass-card rounded-2xl p-6 flex flex-col justify-center order-first">
              <h3 className="text-2xl md:text-3xl font-bold mb-4" style={{ fontFamily: 'Orbitron' }}>
                <span className="text-[#00FFA3]">Real-Time</span> Market Intelligence
              </h3>
              <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                Tinkerpug monitors the crypto markets 24/7, tracking Fear & Greed sentiment,
                top movers on Solana, and global market conditions.
                Stay informed with real-time cosmic intelligence.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button
                  onClick={() => window.dispatchEvent(new CustomEvent("tinkerpug:open"))}
                  data-testid="ask-tinkerpug-btn"
                  className="bg-gradient-to-r from-[#D946EF] to-[#00C2FF] text-white font-bold rounded-xl px-6 py-4 text-sm uppercase hover:scale-[1.02] transition-transform"
                >
                  <Bot className="w-4 h-4 mr-2" />
                  Ask Tinkerpug
                </Button>
              </div>
            </div>
            <div className="lg:col-span-1">
              <MarketDashboard />
            </div>
          </div>
        </div>
      </section>

      {/* COSMIC RUNNER JACKPOT — parked during private testing.
          Imports retained so this block can be reinstated verbatim
          when the Cosmic Runner game launches. */}
      {false && <JackpotTicker />}

      {/* TODAY'S BULLPUG DAILY DROP (auto-hides if no drop yet today) */}
      <LatestDropWidget />

      {/* COMMUNITY SPOTLIGHT — parked during private testing period. */}
      {false && <CommunitySpotlight />}

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

      {/* FEATURES / ECOSYSTEM */}
      <section className="py-24 md:py-32" data-testid="features-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-center mb-16" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            <span className="text-[#00FFA3]">Ecosystem</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: <Shield size={18} />, title: "Origins", desc: "The origin story of the most powerful guardian in the memecoin universe", link: "/lore", img: IMAGES.origins, color: "#D946EF" },
              // Cosmic Runner tile parked — Tinkerpug AI takes its slot
              // for the private testing period. Restore the old entry
              // (Gamepad2 icon, `/game` link, IMAGES.game) when the
              // Cosmic Runner game re-launches.
              { icon: <Bot size={18} />, title: "Tinkerpug AI", desc: "Ask Tinkerpug anything — lore, market signals, or generate a Bullpughan scene on demand", onClick: () => window.dispatchEvent(new CustomEvent("tinkerpug:open")), img: IMAGES.aiAssistant, color: "#D946EF" },
              { icon: <Flame size={18} />, title: "Pugburn", desc: "Reclaim locked SOL from old airdrop and dust accounts — no fees", link: "/pugburn", img: IMAGES.arena, color: "#F5D300" },
            ].map((f, i) => {
              const cardInner = (
                <div className={`glass-card rounded-2xl overflow-hidden hover:-translate-y-1 transition-all duration-300 ${f.isNew ? 'ring-2 ring-[#D946EF]/50' : ''} ${f.comingSoon ? 'ring-2 ring-[#F5D300]/30' : ''}`}>
                  <div className="h-44 overflow-hidden relative">
                    <img src={f.img} alt={f.title} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#05050A] via-transparent to-transparent" />
                    {f.isNew && (
                      <div className="absolute top-3 right-3 px-2 py-1 bg-[#D946EF] text-white text-[10px] font-bold rounded-full uppercase">
                        New
                      </div>
                    )}
                    {f.comingSoon && (
                      <div className="absolute top-3 right-3 px-2 py-1 bg-[#F5D300] text-black text-[10px] font-bold rounded-full uppercase">
                        Coming Soon
                      </div>
                    )}
                  </div>
                  <div className="p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <span style={{ color: f.color }}>{f.icon}</span>
                      <h3 className="font-bold text-xs uppercase tracking-wider" style={{ fontFamily: 'Orbitron, sans-serif' }}>{f.title}</h3>
                      {f.comingSoon && <span className="text-[8px] px-1.5 py-0.5 bg-[#F5D300]/20 text-[#F5D300] rounded-full">SOON</span>}
                    </div>
                    <p className="text-slate-500 text-xs">{f.desc}</p>
                  </div>
                </div>
              );
              // Tiles with an onClick trigger a JS event (e.g. open the
              // Tinkerpug chat modal) instead of navigating.
              if (f.onClick) {
                return (
                  <button
                    key={i}
                    type="button"
                    onClick={f.onClick}
                    className="group text-left"
                    data-testid={`feature-card-${i}`}
                  >
                    {cardInner}
                  </button>
                );
              }
              return (
                <Link to={f.link} key={i} className="group" data-testid={`feature-card-${i}`}>
                  {cardInner}
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* TOKENOMICS — parked until $BULLPUG token launches with a
          contract address. Restore this block verbatim once the
          contract is live and update the stats card accordingly. */}
      {false && (
      <section className="py-24 md:py-32" data-testid="tokenomics-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-center mb-4" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            Token<span className="text-[#F5D300]">omics</span>
          </h2>
          <p className="text-center text-slate-500 mb-16 text-sm">1 Billion $BULLPUG tokens with deflationary mechanics</p>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-5 glass-card rounded-2xl p-6">
              <h3 className="text-base font-bold mb-4" style={{ fontFamily: 'Orbitron, sans-serif' }}>Supply Distribution</h3>
              <div className="h-56 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-40 h-40 rounded-full bg-gradient-to-br from-[#00FFA3] to-[#00FFA3]/60 flex items-center justify-center mx-auto mb-4 shadow-[0_0_40px_rgba(0,255,163,0.3)]">
                    <div className="text-center">
                      <div className="text-3xl font-black text-black" style={{ fontFamily: 'Orbitron, sans-serif' }}>100%</div>
                      <div className="text-xs font-bold text-black/70">FAIR LAUNCH</div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="space-y-2 mt-3">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0 bg-[#00FFA3]" />
                  <span>100% to Liquidity Pool</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0 bg-[#D946EF]" />
                  <span>0% Team Allocation</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0 bg-[#F5D300]" />
                  <span>No Presale</span>
                </div>
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
            </div>
          </div>
        </div>
      </section>
      )}

      {/* RECENT JACKPOT WINNERS — parked with the Cosmic Runner game.
          Reinstate together when the game re-launches. */}
      {false && <RecentWinners />}

      {/* GALLERY — cycles through most-recent daily drops + user-generated
          Tinkerpug `/image` outputs. Auto-rotates every ~6s and falls back
          to the static GALLERY placeholders if the API is empty (e.g. very
          first deploy before any images exist). */}
      <section className="py-24 md:py-32" data-testid="gallery-section">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-center mb-4" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            BULLPUG <span className="text-[#D946EF]">Gallery</span>
          </h2>
          <p className="text-slate-500 text-sm text-center mb-16" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Fresh Bullpughan visions — daily drops and community-generated art.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="gallery-grid">
            {galleryTiles.map((img, i) => (
              <div key={img.key} className="rounded-xl overflow-hidden border border-white/5 hover:border-[#D946EF]/40 transition-all duration-300 group relative">
                <img
                  src={img.src}
                  alt={img.alt}
                  className="w-full h-44 object-cover group-hover:scale-110 transition-transform duration-500"
                  loading="lazy"
                  data-testid={`gallery-tile-${i}`}
                />
                {img.source === "user" && (
                  <span className="absolute top-2 left-2 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-black/60 border border-[#D946EF]/40 text-[#D946EF] backdrop-blur-sm">
                    Community
                  </span>
                )}
                {img.source === "daily_drop" && (
                  <span className="absolute top-2 left-2 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-black/60 border border-[#00FFA3]/40 text-[#00FFA3] backdrop-blur-sm">
                    Daily Drop
                  </span>
                )}
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
