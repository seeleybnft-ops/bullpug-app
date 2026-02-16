import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Gamepad2, Play, RotateCcw, Trophy } from "lucide-react";

const GAME_IMG = "https://customer-assets.emergentagent.com/job_cosmic-pug-game/artifacts/kynwxxke_image%20-%202026-02-17T063523.593.jpg";

export default function SpeedRunGame() {
  const canvasRef = useRef(null);
  const [gameState, setGameState] = useState("idle");
  const [score, setScore] = useState(0);
  const [highScore, setHighScore] = useState(() => parseInt(localStorage.getItem("bullpugHighScore") || "0"));
  const gameRef = useRef({ player: { y: 0, vy: 0, jumping: false }, obstacles: [], frame: 0, speed: 4, score: 0, running: false });
  const animRef = useRef(null);
  const spriteRef = useRef(null);

  useEffect(() => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = GAME_IMG;
    img.onload = () => { spriteRef.current = img; };
  }, []);

  const GROUND_Y = 260;
  const PLAYER_SIZE = 50;
  const GRAVITY = 0.8;
  const JUMP_FORCE = -14;

  const startGame = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const g = gameRef.current;
    g.player = { y: GROUND_Y - PLAYER_SIZE, vy: 0, jumping: false };
    g.obstacles = [];
    g.frame = 0;
    g.speed = 4;
    g.score = 0;
    g.running = true;
    setGameState("playing");
    setScore(0);

    const loop = () => {
      if (!g.running) return;
      g.frame++;
      g.speed = 4 + g.frame * 0.002;
      g.score = Math.floor(g.frame / 5);
      setScore(g.score);

      // Physics
      g.player.vy += GRAVITY;
      g.player.y += g.player.vy;
      if (g.player.y >= GROUND_Y - PLAYER_SIZE) {
        g.player.y = GROUND_Y - PLAYER_SIZE;
        g.player.vy = 0;
        g.player.jumping = false;
      }

      // Spawn obstacles
      if (g.frame % Math.max(40, 80 - Math.floor(g.frame / 100)) === 0) {
        const h = 25 + Math.random() * 35;
        g.obstacles.push({ x: 800, w: 20 + Math.random() * 15, h, type: Math.random() > 0.5 ? "meteor" : "spike" });
      }

      // Move obstacles
      g.obstacles = g.obstacles.filter(o => { o.x -= g.speed; return o.x > -50; });

      // Collision
      const px = 60, py = g.player.y, pw = PLAYER_SIZE - 10, ph = PLAYER_SIZE - 5;
      for (const o of g.obstacles) {
        if (px + pw > o.x + 5 && px < o.x + o.w - 5 && py + ph > GROUND_Y - o.h) {
          g.running = false;
          setGameState("over");
          if (g.score > highScore) {
            setHighScore(g.score);
            localStorage.setItem("bullpugHighScore", String(g.score));
          }
          return;
        }
      }

      // Draw
      ctx.fillStyle = "#05050A";
      ctx.fillRect(0, 0, 800, 320);

      // Stars
      for (let i = 0; i < 30; i++) {
        const sx = (i * 137 + g.frame * 0.3) % 800;
        const sy = (i * 97) % 250;
        ctx.fillStyle = `rgba(255,255,255,${0.2 + (i % 3) * 0.2})`;
        ctx.fillRect(sx, sy, 1.5, 1.5);
      }

      // Ground
      ctx.strokeStyle = "#00FFA3";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, GROUND_Y);
      ctx.lineTo(800, GROUND_Y);
      ctx.stroke();
      ctx.fillStyle = "rgba(0,255,163,0.05)";
      ctx.fillRect(0, GROUND_Y, 800, 60);

      // Ground grid
      ctx.strokeStyle = "rgba(0,255,163,0.1)";
      ctx.lineWidth = 0.5;
      for (let gx = -g.frame * g.speed % 40; gx < 800; gx += 40) {
        ctx.beginPath(); ctx.moveTo(gx, GROUND_Y); ctx.lineTo(gx, 320); ctx.stroke();
      }

      // Player
      if (spriteRef.current) {
        ctx.save();
        ctx.drawImage(spriteRef.current, 50, g.player.y, PLAYER_SIZE, PLAYER_SIZE);
        ctx.restore();
      } else {
        ctx.fillStyle = "#D946EF";
        ctx.fillRect(50, g.player.y, PLAYER_SIZE, PLAYER_SIZE);
        ctx.fillStyle = "#fff";
        ctx.font = "10px Orbitron";
        ctx.fillText("BP", 63, g.player.y + 30);
      }

      // Glow under player
      const glowGrad = ctx.createRadialGradient(75, GROUND_Y, 0, 75, GROUND_Y, 30);
      glowGrad.addColorStop(0, "rgba(0,255,163,0.3)");
      glowGrad.addColorStop(1, "transparent");
      ctx.fillStyle = glowGrad;
      ctx.fillRect(45, GROUND_Y - 5, 60, 15);

      // Obstacles
      for (const o of g.obstacles) {
        if (o.type === "meteor") {
          ctx.fillStyle = "#FF3B30";
          ctx.beginPath();
          ctx.moveTo(o.x + o.w / 2, GROUND_Y - o.h);
          ctx.lineTo(o.x + o.w, GROUND_Y);
          ctx.lineTo(o.x, GROUND_Y);
          ctx.closePath();
          ctx.fill();
          ctx.fillStyle = "rgba(255,59,48,0.3)";
          ctx.beginPath();
          ctx.arc(o.x + o.w / 2, GROUND_Y - o.h / 2, o.w, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.fillStyle = "#F5D300";
          ctx.fillRect(o.x, GROUND_Y - o.h, o.w, o.h);
          ctx.fillStyle = "rgba(245,211,0,0.3)";
          ctx.fillRect(o.x - 2, GROUND_Y - o.h - 2, o.w + 4, o.h + 4);
        }
      }

      // Score HUD
      ctx.fillStyle = "#00FFA3";
      ctx.font = "bold 14px Orbitron, monospace";
      ctx.textAlign = "right";
      ctx.fillText(`SCORE: ${g.score}`, 780, 25);
      ctx.fillStyle = "#F5D300";
      ctx.fillText(`BEST: ${Math.max(g.score, highScore)}`, 780, 45);
      ctx.textAlign = "left";

      animRef.current = requestAnimationFrame(loop);
    };
    animRef.current = requestAnimationFrame(loop);
  }, [highScore]);

  const jump = useCallback(() => {
    const g = gameRef.current;
    if (!g.running) return;
    if (!g.player.jumping) {
      g.player.vy = JUMP_FORCE;
      g.player.jumping = true;
    }
  }, []);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.code === "Space" || e.code === "ArrowUp") {
        e.preventDefault();
        if (gameState === "playing") jump();
        else if (gameState !== "playing") startGame();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => { window.removeEventListener("keydown", handleKey); if (animRef.current) cancelAnimationFrame(animRef.current); };
  }, [gameState, jump, startGame]);

  return (
    <div className="pt-20 pb-16 min-h-screen">
      <div className="stars-bg fixed inset-0 -z-10" />
      <div className="max-w-4xl mx-auto px-6 md:px-12">
        <div className="text-center mb-8">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter uppercase mb-3" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            Speed <span className="text-[#F5D300]">Run</span>
          </h1>
          <p className="text-slate-500 text-sm">Navigate cosmic obstacles as Bullpug</p>
        </div>

        <div className="glass-card rounded-2xl p-4 md:p-6">
          <div className="relative mx-auto" style={{ maxWidth: 800 }}>
            <canvas ref={canvasRef} width={800} height={320}
              onClick={() => gameState === "playing" ? jump() : startGame()}
              onTouchStart={() => gameState === "playing" ? jump() : startGame()}
              className="w-full rounded-xl border-2 border-[#00FFA3]/20 cursor-pointer bg-[#05050A]"
              data-testid="game-canvas" />

            {gameState === "idle" && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 rounded-xl">
                <img src={GAME_IMG} alt="Bullpug" className="w-20 h-20 rounded-xl mb-4 border-2 border-[#00FFA3]/50" />
                <Button onClick={startGame} data-testid="start-game-btn"
                  className="bg-[#00FFA3] text-black font-bold rounded-full px-8 py-5 text-sm uppercase hover:scale-105 transition-transform shadow-[0_0_20px_rgba(0,255,163,0.4)]">
                  <Play className="w-5 h-5 mr-2" /> Start Game
                </Button>
                <p className="text-xs text-slate-500 mt-3">Press SPACE or tap to jump</p>
              </div>
            )}

            {gameState === "over" && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 rounded-xl">
                <p className="text-3xl font-black text-red-400 mb-2" style={{ fontFamily: 'Orbitron, sans-serif' }}>GAME OVER</p>
                <p className="text-lg font-bold text-white mb-1" style={{ fontFamily: 'Orbitron, sans-serif' }}>Score: {score}</p>
                {score >= highScore && score > 0 && (
                  <Badge className="bg-[#F5D300]/10 text-[#F5D300] border-[#F5D300]/30 mb-3">New High Score!</Badge>
                )}
                <Button onClick={startGame} data-testid="restart-game-btn"
                  className="bg-[#00FFA3] text-black font-bold rounded-full px-8 py-4 text-sm uppercase hover:scale-105 transition-transform">
                  <RotateCcw className="w-4 h-4 mr-2" /> Play Again
                </Button>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between mt-4 px-2">
            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs text-slate-500">Score</p>
                <p className="text-xl font-black text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>{score}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">High Score</p>
                <p className="text-xl font-black text-[#F5D300]" style={{ fontFamily: 'Orbitron, sans-serif' }}>{highScore}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Gamepad2 className="w-4 h-4" />
              <span>SPACE / Tap to jump</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
