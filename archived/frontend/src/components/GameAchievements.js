/**
 * Game Achievements Component
 * 
 * Displays achievements earned from the Cosmic Runner game.
 * Tracks high scores, stages reached, moon cheese collected, and gameplay milestones.
 */

import { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import axios from 'axios';
import {
  Award, Trophy, Share2, Lock, Zap, Star, Crown, Target,
  Rocket, Moon, Shield, Sparkles, Clock, TrendingUp, Loader2
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Game-specific achievement definitions
const GAME_ACHIEVEMENTS = [
  // Score-based achievements
  { id: 'first_run', name: 'First Steps', description: 'Complete your first run', icon: '🚀', rarity: 'common', type: 'score', threshold: 1 },
  { id: 'score_500', name: 'Space Cadet', description: 'Score 500 points in one run', icon: '⭐', rarity: 'common', type: 'score', threshold: 500 },
  { id: 'score_1000', name: 'Cosmic Explorer', description: 'Score 1,000 points in one run', icon: '🌟', rarity: 'rare', type: 'score', threshold: 1000 },
  { id: 'score_2000', name: 'Star Navigator', description: 'Score 2,000 points in one run', icon: '✨', rarity: 'epic', type: 'score', threshold: 2000 },
  { id: 'score_5000', name: 'Galactic Legend', description: 'Score 5,000 points in one run', icon: '🌌', rarity: 'legendary', type: 'score', threshold: 5000 },
  
  // Stage-based achievements
  { id: 'stage_2', name: 'Level Up', description: 'Reach Stage 2', icon: '📈', rarity: 'common', type: 'stage', threshold: 2 },
  { id: 'stage_3', name: 'Going Deep', description: 'Reach Stage 3', icon: '🎯', rarity: 'rare', type: 'stage', threshold: 3 },
  { id: 'stage_4', name: 'Near the Edge', description: 'Reach Stage 4', icon: '🔥', rarity: 'epic', type: 'stage', threshold: 4 },
  { id: 'stage_5', name: 'Multiverse Master', description: 'Reach Stage 5', icon: '🏆', rarity: 'legendary', type: 'stage', threshold: 5 },
  
  // Moon cheese achievements
  { id: 'cheese_10', name: 'Cheese Nibbler', description: 'Collect 10 Moon Cheese', icon: '🧀', rarity: 'common', type: 'cheese', threshold: 10 },
  { id: 'cheese_50', name: 'Cheese Hunter', description: 'Collect 50 Moon Cheese in total', icon: '🌕', rarity: 'rare', type: 'cheese', threshold: 50 },
  { id: 'cheese_100', name: 'Cheese Master', description: 'Collect 100 Moon Cheese in total', icon: '🪐', rarity: 'epic', type: 'cheese', threshold: 100 },
  { id: 'cheese_500', name: 'Moon Cheese Baron', description: 'Collect 500 Moon Cheese in total', icon: '👑', rarity: 'legendary', type: 'cheese', threshold: 500 },
  
  // Power-up achievements
  { id: 'powerup_first', name: 'Power Up!', description: 'Collect your first power-up', icon: '⚡', rarity: 'common', type: 'powerup', threshold: 1 },
  { id: 'shield_master', name: 'Shield Master', description: 'Use Guardian Shield 10 times', icon: '🛡️', rarity: 'rare', type: 'shield', threshold: 10 },
  { id: 'magnet_lover', name: 'Magnetic Personality', description: 'Use Moon Cheese Magnet 10 times', icon: '🧲', rarity: 'rare', type: 'magnet', threshold: 10 },
  { id: 'star_power', name: 'Star Collector', description: 'Use Star Power 10 times', icon: '💫', rarity: 'rare', type: 'star', threshold: 10 },
  
  // Special achievements
  { id: 'survivor', name: 'Survivor', description: 'Play for 60 seconds without hitting an obstacle', icon: '🏃', rarity: 'epic', type: 'time', threshold: 60 },
  { id: 'perfectionist', name: 'Perfectionist', description: 'Complete a run with all cheese collected', icon: '💯', rarity: 'legendary', type: 'special', threshold: 1 },
  { id: 'daily_player', name: 'Regular Pug', description: 'Play 3 days in a row', icon: '📅', rarity: 'rare', type: 'streak', threshold: 3 },
  { id: 'weekly_warrior', name: 'Weekly Warrior', description: 'Play 7 days in a row', icon: '🗓️', rarity: 'epic', type: 'streak', threshold: 7 },
];

// Rarity colors
const RARITY_COLORS = {
  common: { bg: '#00FFA3', text: '#000', glow: 'rgba(0, 255, 163, 0.3)' },
  rare: { bg: '#00C2FF', text: '#000', glow: 'rgba(0, 194, 255, 0.3)' },
  epic: { bg: '#D946EF', text: '#fff', glow: 'rgba(217, 70, 239, 0.4)' },
  legendary: { bg: '#F5D300', text: '#000', glow: 'rgba(245, 211, 0, 0.5)' },
};

export default function GameAchievements({ currentScore, totalMoonCheese, currentStage, showCompact = false }) {
  const { publicKey, connected } = useWallet();
  const [earnedAchievements, setEarnedAchievements] = useState([]);
  const [gameStats, setGameStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [newUnlocks, setNewUnlocks] = useState([]);

  // Load achievements from localStorage (works without wallet connection)
  useEffect(() => {
    const storedAchievements = JSON.parse(localStorage.getItem('bullpugGameAchievements') || '[]');
    const storedStats = JSON.parse(localStorage.getItem('bullpugGameStats') || '{}');
    setEarnedAchievements(storedAchievements);
    setGameStats({
      highScore: storedStats.highScore || parseInt(localStorage.getItem('bullpugHighScore') || '0'),
      totalMoonCheese: storedStats.totalMoonCheese || parseInt(localStorage.getItem('bullpugMoonCheese') || '0'),
      maxStage: storedStats.maxStage || 1,
      totalRuns: storedStats.totalRuns || 0,
      totalPlayTime: storedStats.totalPlayTime || 0,
      shieldsUsed: storedStats.shieldsUsed || 0,
      magnetsUsed: storedStats.magnetsUsed || 0,
      starsUsed: storedStats.starsUsed || 0,
      playStreak: storedStats.playStreak || 0,
      lastPlayDate: storedStats.lastPlayDate || null,
    });
  }, []);

  // Check for newly earned achievements
  const checkAchievements = useCallback((score, cheese, stage) => {
    if (!gameStats) return;
    
    const newlyEarned = [];
    
    GAME_ACHIEVEMENTS.forEach(achievement => {
      // Skip if already earned
      if (earnedAchievements.includes(achievement.id)) return;
      
      let earned = false;
      
      switch (achievement.type) {
        case 'score':
          earned = score >= achievement.threshold || gameStats.highScore >= achievement.threshold;
          break;
        case 'stage':
          earned = stage >= achievement.threshold || gameStats.maxStage >= achievement.threshold;
          break;
        case 'cheese':
          earned = (gameStats.totalMoonCheese + cheese) >= achievement.threshold;
          break;
        case 'powerup':
          earned = (gameStats.shieldsUsed + gameStats.magnetsUsed + gameStats.starsUsed) >= achievement.threshold;
          break;
        case 'shield':
          earned = gameStats.shieldsUsed >= achievement.threshold;
          break;
        case 'magnet':
          earned = gameStats.magnetsUsed >= achievement.threshold;
          break;
        case 'star':
          earned = gameStats.starsUsed >= achievement.threshold;
          break;
        case 'streak':
          earned = gameStats.playStreak >= achievement.threshold;
          break;
        default:
          break;
      }
      
      if (earned) {
        newlyEarned.push(achievement);
      }
    });
    
    if (newlyEarned.length > 0) {
      const updatedEarned = [...earnedAchievements, ...newlyEarned.map(a => a.id)];
      setEarnedAchievements(updatedEarned);
      localStorage.setItem('bullpugGameAchievements', JSON.stringify(updatedEarned));
      
      // Show unlock notifications
      setNewUnlocks(newlyEarned);
      newlyEarned.forEach((achievement, i) => {
        setTimeout(() => {
          toast.success(`Achievement Unlocked: ${achievement.name}!`, {
            description: achievement.description,
            duration: 5000,
          });
        }, i * 1000);
      });
    }
  }, [earnedAchievements, gameStats]);

  // Check achievements when game stats change
  useEffect(() => {
    if (currentScore > 0 || totalMoonCheese > 0 || currentStage > 1) {
      checkAchievements(currentScore, totalMoonCheese, currentStage);
    }
  }, [currentScore, totalMoonCheese, currentStage, checkAchievements]);

  // Save game stats to localStorage when they change
  const updateGameStats = (newStats) => {
    const updated = { ...gameStats, ...newStats };
    setGameStats(updated);
    localStorage.setItem('bullpugGameStats', JSON.stringify(updated));
  };

  // Calculate progress for next achievement
  const getNextAchievement = (type) => {
    const unearned = GAME_ACHIEVEMENTS.filter(
      a => a.type === type && !earnedAchievements.includes(a.id)
    ).sort((a, b) => a.threshold - b.threshold);
    return unearned[0];
  };

  // Compact view for in-game display
  if (showCompact) {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] text-slate-500 uppercase">Achievements:</span>
        {GAME_ACHIEVEMENTS.slice(0, 5).map(achievement => {
          const earned = earnedAchievements.includes(achievement.id);
          const isNew = newUnlocks.find(a => a.id === achievement.id);
          return (
            <div
              key={achievement.id}
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs transition-all ${
                earned ? 'bg-white/10' : 'bg-black/30 opacity-40'
              } ${isNew ? 'ring-2 ring-[#F5D300] animate-pulse' : ''}`}
              title={`${achievement.name}: ${achievement.description}`}
            >
              {achievement.icon}
            </div>
          );
        })}
        <span className="text-[10px] text-slate-400">
          {earnedAchievements.length}/{GAME_ACHIEVEMENTS.length}
        </span>
      </div>
    );
  }

  // Full achievements panel
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Trophy className="w-5 h-5 text-[#F5D300]" />
          <h3 className="font-bold text-white">Game Achievements</h3>
        </div>
        <Badge className="bg-[#F5D300]/10 text-[#F5D300] border-[#F5D300]/30">
          {earnedAchievements.length}/{GAME_ACHIEVEMENTS.length}
        </Badge>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-2">
        <div className="bg-black/30 rounded-lg p-2 text-center">
          <p className="text-lg font-bold text-[#00FFA3]">{gameStats?.highScore || 0}</p>
          <p className="text-[8px] text-slate-500">HIGH SCORE</p>
        </div>
        <div className="bg-black/30 rounded-lg p-2 text-center">
          <p className="text-lg font-bold text-[#F5D300]">{gameStats?.totalMoonCheese || 0}</p>
          <p className="text-[8px] text-slate-500">MOON CHEESE</p>
        </div>
        <div className="bg-black/30 rounded-lg p-2 text-center">
          <p className="text-lg font-bold text-[#D946EF]">{gameStats?.maxStage || 1}</p>
          <p className="text-[8px] text-slate-500">MAX STAGE</p>
        </div>
        <div className="bg-black/30 rounded-lg p-2 text-center">
          <p className="text-lg font-bold text-[#00C2FF]">{gameStats?.totalRuns || 0}</p>
          <p className="text-[8px] text-slate-500">TOTAL RUNS</p>
        </div>
      </div>

      {/* Achievement Grid */}
      <div className="grid grid-cols-4 sm:grid-cols-5 gap-2">
        {GAME_ACHIEVEMENTS.map(achievement => {
          const earned = earnedAchievements.includes(achievement.id);
          const rarity = RARITY_COLORS[achievement.rarity];
          const isNew = newUnlocks.find(a => a.id === achievement.id);
          
          return (
            <div
              key={achievement.id}
              className={`relative p-2 rounded-xl text-center transition-all ${
                earned 
                  ? 'bg-white/5 border border-white/10 hover:border-white/20' 
                  : 'bg-black/30 border border-white/5 opacity-40 grayscale'
              } ${isNew ? 'ring-2 ring-[#F5D300] animate-pulse' : ''}`}
              style={earned ? { boxShadow: rarity.glow } : {}}
              title={`${achievement.name}: ${achievement.description}`}
            >
              <div className="text-xl mb-0.5">{achievement.icon}</div>
              <p className="text-[8px] font-bold text-white truncate">{achievement.name}</p>
              <Badge 
                className="mt-0.5 text-[6px] px-1 py-0"
                style={{ 
                  backgroundColor: `${rarity.bg}20`,
                  color: rarity.bg,
                  border: `1px solid ${rarity.bg}40`
                }}
              >
                {achievement.rarity.toUpperCase()}
              </Badge>
              
              {!earned && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-xl">
                  <Lock className="w-3 h-3 text-slate-500" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Next Achievements */}
      <div className="bg-white/5 rounded-xl p-3 border border-white/5">
        <p className="text-[10px] text-slate-500 uppercase mb-2">Next Milestones</p>
        <div className="space-y-2">
          {['score', 'cheese', 'stage'].map(type => {
            const next = getNextAchievement(type);
            if (!next) return null;
            
            let current = 0;
            if (type === 'score') current = gameStats?.highScore || 0;
            else if (type === 'cheese') current = gameStats?.totalMoonCheese || 0;
            else if (type === 'stage') current = gameStats?.maxStage || 1;
            
            const progress = Math.min(100, (current / next.threshold) * 100);
            
            return (
              <div key={type} className="flex items-center gap-2">
                <span className="text-sm">{next.icon}</span>
                <div className="flex-1">
                  <div className="flex justify-between text-[10px] mb-0.5">
                    <span className="text-white">{next.name}</span>
                    <span className="text-slate-400">{current}/{next.threshold}</span>
                  </div>
                  <div className="h-1.5 bg-black/50 rounded-full overflow-hidden">
                    <div 
                      className="h-full rounded-full transition-all"
                      style={{ 
                        width: `${progress}%`,
                        backgroundColor: RARITY_COLORS[next.rarity].bg
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Share Button */}
      <Button
        className="w-full bg-[#1DA1F2]/10 text-[#1DA1F2] border border-[#1DA1F2]/30 hover:bg-[#1DA1F2]/20"
        onClick={() => {
          const text = `🎮 Cosmic Runner Stats on @BullpugMeme\n\n🏆 High Score: ${gameStats?.highScore || 0}\n🧀 Moon Cheese: ${gameStats?.totalMoonCheese || 0}\n⭐ Achievements: ${earnedAchievements.length}/${GAME_ACHIEVEMENTS.length}\n\nThink you can beat me? 🚀\n\n#Bullpug #CosmicRunner #Solana`;
          const url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`;
          window.open(url, '_blank', 'width=550,height=420');
        }}
      >
        <Share2 className="w-4 h-4 mr-2" />
        Share on X
      </Button>
    </div>
  );
}

// Export for external achievement tracking
export { GAME_ACHIEVEMENTS, RARITY_COLORS };
