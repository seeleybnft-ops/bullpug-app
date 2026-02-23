/**
 * GameGuide - Component showing game controls and items guide
 */

import { POWERUP_TYPES, OBSTACLE_TYPES } from './constants';

export default function GameGuide() {
  return (
    <div className="mt-8 glass-card rounded-2xl p-6" data-testid="game-guide">
      <h3 className="text-lg font-bold mb-4 text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>
        COSMIC RUNNER GUIDE
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
        {/* Collectibles */}
        <div className="bg-black/30 rounded-xl p-4">
          <h4 className="text-xs uppercase text-slate-400 mb-2 font-bold">Collectibles</h4>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">🥮</span>
            <div>
              <p className="text-white font-medium">Moon Cheese</p>
              <p className="text-slate-500 text-xs">+25 points each</p>
            </div>
          </div>
        </div>
        
        {/* Power-ups */}
        <div className="bg-black/30 rounded-xl p-4">
          <h4 className="text-xs uppercase text-slate-400 mb-2 font-bold">Power-ups</h4>
          <div className="space-y-2">
            {Object.entries(POWERUP_TYPES).map(([key, powerup]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-lg">{powerup.icon}</span>
                <div>
                  <p className="text-white text-xs font-medium">{powerup.name}</p>
                  <p className="text-slate-500 text-[10px]">{powerup.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Obstacles */}
        <div className="bg-black/30 rounded-xl p-4">
          <h4 className="text-xs uppercase text-slate-400 mb-2 font-bold">Obstacles</h4>
          <div className="space-y-1">
            {Object.entries(OBSTACLE_TYPES).map(([key, obstacle]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-lg">{obstacle.emoji}</span>
                <p className="text-white text-xs">{obstacle.name}</p>
              </div>
            ))}
          </div>
        </div>
        
        {/* Controls */}
        <div className="bg-black/30 rounded-xl p-4">
          <h4 className="text-xs uppercase text-slate-400 mb-2 font-bold">Controls</h4>
          <div className="space-y-1 text-slate-300 text-xs">
            <p><kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-[10px]">A</kbd> / <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-[10px]">←</kbd> Move Left</p>
            <p><kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-[10px]">D</kbd> / <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-[10px]">→</kbd> Move Right</p>
            <p><kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-[10px]">SPACE</kbd> / <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-[10px]">↑</kbd> Jump</p>
            <p className="text-slate-500 text-[10px] mt-2">Mobile: Swipe or tap sides to move, tap up to jump</p>
          </div>
        </div>
      </div>
    </div>
  );
}
