import { useState, useEffect } from "react";
import axios from "axios";
import { Sparkles } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Tier styles
const TIER_STYLES = {
  legendary: "bg-gradient-to-r from-yellow-400 via-amber-500 to-orange-500 text-black shadow-lg shadow-amber-500/30",
  epic: "bg-gradient-to-r from-purple-500 via-violet-500 to-fuchsia-500 text-white shadow-lg shadow-purple-500/30",
  rare: "bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-500 text-white shadow-md shadow-blue-500/20",
  common: "bg-slate-700 text-slate-200"
};

const TIER_BORDER = {
  legendary: "border-amber-400/50",
  epic: "border-purple-400/50",
  rare: "border-blue-400/50",
  common: "border-slate-500/50"
};

/**
 * Single Badge Component
 */
export function Badge({ badge, size = "md", showTooltip = true }) {
  const [showDetails, setShowDetails] = useState(false);
  
  const sizeClasses = {
    sm: "w-6 h-6 text-sm",
    md: "w-8 h-8 text-lg",
    lg: "w-10 h-10 text-xl"
  };
  
  const tier = badge.tier || "common";
  
  return (
    <div className="relative inline-block">
      <div
        className={`${sizeClasses[size]} rounded-full flex items-center justify-center cursor-pointer
          border-2 ${TIER_BORDER[tier]} ${TIER_STYLES[tier]} transition-transform hover:scale-110`}
        onMouseEnter={() => setShowDetails(true)}
        onMouseLeave={() => setShowDetails(false)}
        title={badge.name}
        data-testid={`badge-${badge.id}`}
      >
        <span>{badge.emoji}</span>
      </div>
      
      {/* Tooltip */}
      {showTooltip && showDetails && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 pointer-events-none">
          <div className="glass-card rounded-lg p-3 min-w-[180px] text-center shadow-xl border border-white/10">
            <div className="text-lg mb-1">{badge.emoji}</div>
            <div className="font-bold text-white text-sm">{badge.name}</div>
            <div className="text-xs text-slate-400 mt-1">{badge.description}</div>
            <div className={`text-[10px] mt-2 px-2 py-0.5 rounded-full inline-block ${TIER_STYLES[tier]}`}>
              {tier.charAt(0).toUpperCase() + tier.slice(1)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Badge Row - displays multiple badges inline
 */
export function BadgeRow({ badges, maxShow = 5, size = "sm" }) {
  if (!badges || badges.length === 0) return null;
  
  const visibleBadges = badges.slice(0, maxShow);
  const remaining = badges.length - maxShow;
  
  return (
    <div className="flex items-center gap-1">
      {visibleBadges.map((badge, i) => (
        <Badge key={badge.id || i} badge={badge} size={size} />
      ))}
      {remaining > 0 && (
        <div className="w-6 h-6 rounded-full bg-slate-700 text-slate-400 text-[10px] flex items-center justify-center">
          +{remaining}
        </div>
      )}
    </div>
  );
}

/**
 * Badge Showcase - full display of user badges
 */
export function BadgeShowcase({ walletAddress }) {
  const [badges, setBadges] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    if (!walletAddress) {
      setLoading(false);
      return;
    }
    
    axios.get(`${API}/badges/user/${walletAddress}`)
      .then(r => setBadges(r.data.badges || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [walletAddress]);
  
  if (loading) {
    return (
      <div className="glass-card rounded-xl p-4 animate-pulse">
        <div className="h-8 bg-slate-700 rounded w-32 mb-3" />
        <div className="flex gap-2">
          {[1,2,3].map(i => (
            <div key={i} className="w-10 h-10 rounded-full bg-slate-700" />
          ))}
        </div>
      </div>
    );
  }
  
  return (
    <div className="glass-card rounded-xl p-5">
      <h3 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2" 
          style={{ fontFamily: 'Orbitron, sans-serif' }}>
        <Sparkles className="w-4 h-4 text-amber-400" />
        Badges ({badges.length})
      </h3>
      
      {badges.length === 0 ? (
        <p className="text-slate-500 text-sm">No badges earned yet. Keep playing!</p>
      ) : (
        <div className="flex flex-wrap gap-3">
          {badges.map((badge, i) => (
            <Badge key={badge.id || i} badge={badge} size="lg" />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * All Badges Grid - shows all available badges
 */
export function AllBadgesGrid() {
  const [badges, setBadges] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    axios.get(`${API}/badges/all`)
      .then(r => setBadges(r.data.badges || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);
  
  if (loading) return null;
  
  // Group by tier
  const grouped = badges.reduce((acc, badge) => {
    const tier = badge.tier || "common";
    if (!acc[tier]) acc[tier] = [];
    acc[tier].push(badge);
    return acc;
  }, {});
  
  const tierOrder = ["legendary", "epic", "rare", "common"];
  
  return (
    <div className="space-y-6">
      {tierOrder.map(tier => (
        grouped[tier] && (
          <div key={tier}>
            <h4 className={`text-xs font-bold uppercase mb-3 ${
              tier === "legendary" ? "text-amber-400" :
              tier === "epic" ? "text-purple-400" :
              tier === "rare" ? "text-blue-400" :
              "text-slate-400"
            }`}>
              {tier.charAt(0).toUpperCase() + tier.slice(1)} Badges
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {grouped[tier].map(badge => (
                <div key={badge.id} className="glass-card rounded-lg p-3 flex items-center gap-3">
                  <Badge badge={badge} size="md" showTooltip={false} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-white truncate">{badge.name}</div>
                    <div className="text-xs text-slate-500 truncate">{badge.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      ))}
    </div>
  );
}

export default BadgeShowcase;
