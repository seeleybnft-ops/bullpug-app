import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Rocket, Clock, Swords, Trophy, Users, Zap, Bell } from "lucide-react";
import { Link } from "react-router-dom";
import "@/styles/animations.css";

export default function BettingArena() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [notified, setNotified] = useState(false);

  const handleNotify = (e) => {
    e.preventDefault();
    if (email) {
      // Store in localStorage for now
      const waitlist = JSON.parse(localStorage.getItem("p2p_waitlist") || "[]");
      if (!waitlist.includes(email)) {
        waitlist.push(email);
        localStorage.setItem("p2p_waitlist", JSON.stringify(waitlist));
      }
      setNotified(true);
    }
  };

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-4xl mx-auto px-6 md:px-12">
        
        {/* Hero Section */}
        <div className="text-center mb-12">
          <Badge className="mb-4 bg-[#F5D300]/20 text-[#F5D300] border-[#F5D300]/30 text-sm px-4 py-1">
            <Clock className="w-4 h-4 mr-2 inline" />
            Coming Soon
          </Badge>
          
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase mb-4" 
              style={{ fontFamily: 'Orbitron, sans-serif' }} 
              data-testid="arena-title">
            P2P <span className="text-[#00FFA3] neon-text">Arena</span>
          </h1>
          
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Peer-to-peer betting powered by Solana smart contracts. 
            Challenge other players to coin flips, build your reputation, and compete in community jackpots.
          </p>
        </div>

        {/* Feature Preview Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <div className="glass-card rounded-2xl p-6 text-center border border-white/10 hover:border-[#00FFA3]/30 transition-all">
            <div className="w-16 h-16 rounded-2xl bg-[#00FFA3]/20 flex items-center justify-center mx-auto mb-4">
              <Swords className="w-8 h-8 text-[#00FFA3]" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">P2P Coin Flip</h3>
            <p className="text-sm text-slate-400">
              Challenge any player to a 50/50 coin flip. Winner takes all (minus small rake).
            </p>
          </div>
          
          <div className="glass-card rounded-2xl p-6 text-center border border-white/10 hover:border-[#D946EF]/30 transition-all">
            <div className="w-16 h-16 rounded-2xl bg-[#D946EF]/20 flex items-center justify-center mx-auto mb-4">
              <Trophy className="w-8 h-8 text-[#D946EF]" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Community Jackpot</h3>
            <p className="text-sm text-slate-400">
              Join the pot and compete for massive prizes. More entries = higher chance to win.
            </p>
          </div>
          
          <div className="glass-card rounded-2xl p-6 text-center border border-white/10 hover:border-[#00C2FF]/30 transition-all">
            <div className="w-16 h-16 rounded-2xl bg-[#00C2FF]/20 flex items-center justify-center mx-auto mb-4">
              <Users className="w-8 h-8 text-[#00C2FF]" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Reputation System</h3>
            <p className="text-sm text-slate-400">
              Build your streak, earn badges, and climb the leaderboard as you win more bets.
            </p>
          </div>
        </div>

        {/* Why Coming Soon */}
        <div className="glass-card rounded-2xl p-8 mb-12 border border-[#F5D300]/20 bg-[#F5D300]/5">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#F5D300]/20 flex items-center justify-center flex-shrink-0">
              <Rocket className="w-6 h-6 text-[#F5D300]" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white mb-2">Why Coming Soon?</h3>
              <p className="text-slate-400 text-sm mb-4">
                We're building a trustless P2P betting system using Solana smart contracts. 
                This ensures your funds are secure and outcomes are provably fair - no middleman, no trust required.
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge className="bg-white/10 text-slate-300 border-white/20">
                  <Zap className="w-3 h-3 mr-1" /> Smart Contract Powered
                </Badge>
                <Badge className="bg-white/10 text-slate-300 border-white/20">
                  Provably Fair
                </Badge>
                <Badge className="bg-white/10 text-slate-300 border-white/20">
                  Non-Custodial
                </Badge>
              </div>
            </div>
          </div>
        </div>

        {/* Notify Me Form */}
        <div className="glass-card rounded-2xl p-8 text-center border border-white/10">
          {!notified ? (
            <>
              <Bell className="w-12 h-12 text-[#D946EF] mx-auto mb-4" />
              <h3 className="text-xl font-bold text-white mb-2">Get Notified When We Launch</h3>
              <p className="text-slate-400 text-sm mb-6">
                Be the first to know when P2P Arena goes live. Early supporters may receive special perks!
              </p>
              <form onSubmit={handleNotify} className="flex gap-3 max-w-md mx-auto">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  className="flex-1 px-4 py-3 rounded-xl bg-black/40 border border-white/10 text-white placeholder:text-slate-500 focus:border-[#D946EF]/50 focus:outline-none"
                  required
                />
                <Button type="submit" className="bg-[#D946EF] hover:bg-[#D946EF]/80 px-6">
                  Notify Me
                </Button>
              </form>
            </>
          ) : (
            <>
              <div className="w-16 h-16 rounded-full bg-[#00FFA3]/20 flex items-center justify-center mx-auto mb-4">
                <Zap className="w-8 h-8 text-[#00FFA3]" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">You're on the list!</h3>
              <p className="text-slate-400 text-sm mb-6">
                We'll notify you at <span className="text-[#00FFA3]">{email}</span> when P2P Arena launches.
              </p>
            </>
          )}
        </div>

        {/* Back to Trading */}
        <div className="text-center mt-8">
          <p className="text-slate-500 text-sm mb-4">While you wait, check out our other features:</p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/ai-trader">
              <Button variant="outline" className="border-white/20 text-slate-300 hover:text-white">
                AI Trading Bot
              </Button>
            </Link>
            <Link to="/game">
              <Button variant="outline" className="border-white/20 text-slate-300 hover:text-white">
                Cosmic Runner
              </Button>
            </Link>
            <Link to="/pug-burn">
              <Button variant="outline" className="border-white/20 text-slate-300 hover:text-white">
                PugBurn
              </Button>
            </Link>
          </div>
        </div>
        
      </div>
    </div>
  );
}
