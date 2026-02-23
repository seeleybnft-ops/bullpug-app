import { OBSTACLE_GUIDE, POWERUP_GUIDE } from '@/game/constants';

/**
 * Game Guide component - displays information about all game items, obstacles, and controls
 * Extracted from SpeedRunGame.js for better modularity
 */
export default function GameGuide() {
  return (
    <div className="mt-8 max-w-4xl mx-auto">
      <div className="glass-card rounded-2xl p-6">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <span className="text-[#00FFA3]">📖</span> GAME GUIDE
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Collectibles */}
          <div>
            <h4 className="text-sm font-bold text-[#FFD700] mb-3 flex items-center gap-2">
              <span>✨</span> COLLECTIBLES
            </h4>
            <div className="space-y-3">
              <div className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                <img 
                  src="https://customer-assets.emergentagent.com/job_7cd24e51-411f-4346-a028-e9b4e7530f5e/artifacts/f0lh6k0c_image%20-%202026-02-24T080914.534.jpg" 
                  alt="Moon Cheese" 
                  className="w-8 h-8 rounded-full object-cover"
                />
                <div>
                  <p className="text-sm font-semibold text-white">Moon Cheese</p>
                  <p className="text-xs text-slate-400">+25 points. The cosmic snack Bullpug loves!</p>
                </div>
              </div>
            </div>
          </div>

          {/* Power-ups */}
          <div>
            <h4 className="text-sm font-bold text-[#D946EF] mb-3 flex items-center gap-2">
              <span>⚡</span> POWER-UPS
            </h4>
            <div className="space-y-3">
              {POWERUP_GUIDE.map((powerup) => (
                <div key={powerup.type} className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                  <span className="text-2xl">{powerup.emoji}</span>
                  <div>
                    <p className={`text-sm font-semibold ${powerup.color}`}>{powerup.name}</p>
                    <p className="text-xs text-slate-400">{powerup.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Obstacles */}
          <div>
            <h4 className="text-sm font-bold text-[#FF6B35] mb-3 flex items-center gap-2">
              <span>⚠️</span> OBSTACLES
            </h4>
            <div className="space-y-3">
              {OBSTACLE_GUIDE.map((obstacle) => (
                <div key={obstacle.type} className="flex items-start gap-3 p-2 rounded-lg bg-white/5">
                  <span className="text-2xl">{obstacle.emoji}</span>
                  <div>
                    <p className={`text-sm font-semibold ${obstacle.color}`}>{obstacle.name}</p>
                    <p className="text-xs text-slate-400">{obstacle.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="mt-6 pt-4 border-t border-white/10">
          <h4 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
            <span>🎮</span> CONTROLS
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-lg bg-white/5">
              <div className="text-lg font-mono text-[#00FFA3]">A / ←</div>
              <div className="text-xs text-slate-400">Move Left</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-white/5">
              <div className="text-lg font-mono text-[#00FFA3]">D / →</div>
              <div className="text-xs text-slate-400">Move Right</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-white/5">
              <div className="text-lg font-mono text-[#00FFA3]">SPACE / ↑</div>
              <div className="text-xs text-slate-400">Jump</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-white/5">
              <div className="text-lg text-[#00FFA3]">📱 Swipe</div>
              <div className="text-xs text-slate-400">Mobile Controls</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
