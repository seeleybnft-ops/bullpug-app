/**
 * Bullpug Cosmic Runner — Phase 1 (3D)
 *
 * Three.js + @react-three/fiber endless runner. 3-lane track through deep space.
 * - Keyboard: A/← swipe left, D/→ swipe right, W/↑/Space jump, S/↓ slide
 * - Touch: swipe left/right/up/down on the canvas
 * - Score: distance + coin bonus
 * - Game over on obstacle hit
 *
 * Visual theme: cosmic — starfield, nebula gradient, neon track, asteroid + crystal
 *   pillar + ringed-rock obstacles, glowing SOL-like coins. Bullpug is a low-poly
 *   stylised pug with canonical curved bull horns (canon-respect).
 */

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Stars, Sparkles } from "@react-three/drei";
import * as THREE from "three";

// ───────────────────────────────────────────── Config

const LANES = [-1.6, 0, 1.6];          // x positions
const FORWARD_SPEED_BASE = 14;          // units per second
const FORWARD_SPEED_RAMP = 0.18;        // adds per second
const TRACK_LENGTH = 80;                // visible track segments distance
const JUMP_VELOCITY = 9.0;
const GRAVITY = -22.0;
const SLIDE_DURATION_MS = 700;
const SPAWN_AHEAD = 60;                 // spawn obstacles this far ahead
const COIN_VALUE = 5;

const COLORS = {
  bg: "#04030c",
  trackA: "#1a0e2e",
  trackB: "#0b0820",
  trackEdge: "#00FFA3",
  bullpug: "#F0DCC4",
  bullpugDark: "#3A2718",
  horn: "#F5D300",
  coin: "#FFD700",
  asteroid: "#5b6878",
  crystal: "#D946EF",
  ring: "#00C2FF",
};

// ───────────────────────────────────────────── Audio (synthesised, no assets)

function useGameAudio() {
  const ctxRef = useRef(null);
  const ensure = () => {
    if (!ctxRef.current) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) ctxRef.current = new AC();
    }
    return ctxRef.current;
  };
  const blip = useCallback((freq = 880, dur = 0.08, type = "square", vol = 0.18) => {
    const ctx = ensure();
    if (!ctx) return;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = type;
    o.frequency.value = freq;
    g.gain.setValueAtTime(vol, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
    o.connect(g).connect(ctx.destination);
    o.start();
    o.stop(ctx.currentTime + dur);
  }, []);
  return {
    coin: () => blip(1320, 0.05, "triangle", 0.12),
    jump: () => blip(660, 0.12, "sine", 0.16),
    slide: () => blip(220, 0.18, "sawtooth", 0.10),
    death: () => {
      blip(180, 0.18, "square", 0.22);
      setTimeout(() => blip(110, 0.4, "sawtooth", 0.18), 120);
    },
    laneChange: () => blip(520, 0.04, "triangle", 0.10),
  };
}

// ───────────────────────────────────────────── Bullpug character (low-poly + horns)

function Bullpug({ refY, refX, sliding, running }) {
  const group = useRef();
  const bob = useRef(0);
  const leg1 = useRef();
  const leg2 = useRef();
  useFrame((_, dt) => {
    if (!group.current) return;
    group.current.position.x = refX.current;
    group.current.position.y = refY.current + (sliding.current ? -0.4 : 0);
    // Running bob
    bob.current += dt * 14;
    const bobY = running.current && !sliding.current ? Math.sin(bob.current) * 0.06 : 0;
    group.current.position.y += bobY;
    // Body squash on slide
    group.current.scale.set(1, sliding.current ? 0.55 : 1, sliding.current ? 1.4 : 1);
    // Leg cycle
    if (leg1.current && leg2.current && running.current && !sliding.current) {
      leg1.current.rotation.x = Math.sin(bob.current) * 0.9;
      leg2.current.rotation.x = -Math.sin(bob.current) * 0.9;
    }
  });
  return (
    <group ref={group}>
      {/* Body — fawn pug, slightly squashed */}
      <mesh position={[0, 0.55, 0]} castShadow>
        <boxGeometry args={[0.85, 0.7, 1.0]} />
        <meshStandardMaterial color={COLORS.bullpug} roughness={0.7} />
      </mesh>
      {/* Head — bigger, squashed muzzle */}
      <mesh position={[0, 1.1, 0.45]} castShadow>
        <boxGeometry args={[0.75, 0.7, 0.55]} />
        <meshStandardMaterial color={COLORS.bullpug} roughness={0.7} />
      </mesh>
      {/* Muzzle (darker) */}
      <mesh position={[0, 0.95, 0.78]}>
        <boxGeometry args={[0.45, 0.32, 0.2]} />
        <meshStandardMaterial color={COLORS.bullpugDark} roughness={0.85} />
      </mesh>
      {/* Eyes */}
      <mesh position={[-0.2, 1.18, 0.74]}>
        <sphereGeometry args={[0.075, 12, 12]} />
        <meshStandardMaterial color="#0d0d12" />
      </mesh>
      <mesh position={[0.2, 1.18, 0.74]}>
        <sphereGeometry args={[0.075, 12, 12]} />
        <meshStandardMaterial color="#0d0d12" />
      </mesh>
      {/* HORNS — canonical curved bull horns (ivory-to-bronze) */}
      <Horn position={[-0.28, 1.45, 0.42]} rotation={[0.2, 0.3, -0.6]} />
      <Horn position={[0.28, 1.45, 0.42]} rotation={[0.2, -0.3, 0.6]} />
      {/* Floppy ears */}
      <mesh position={[-0.4, 1.3, 0.3]} rotation={[0.1, -0.2, -0.4]}>
        <boxGeometry args={[0.12, 0.35, 0.22]} />
        <meshStandardMaterial color={COLORS.bullpugDark} roughness={0.85} />
      </mesh>
      <mesh position={[0.4, 1.3, 0.3]} rotation={[0.1, 0.2, 0.4]}>
        <boxGeometry args={[0.12, 0.35, 0.22]} />
        <meshStandardMaterial color={COLORS.bullpugDark} roughness={0.85} />
      </mesh>
      {/* Legs */}
      <group ref={leg1}>
        <mesh position={[-0.25, 0.15, 0.35]} castShadow>
          <boxGeometry args={[0.22, 0.4, 0.22]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.7} />
        </mesh>
      </group>
      <group ref={leg2}>
        <mesh position={[0.25, 0.15, 0.35]} castShadow>
          <boxGeometry args={[0.22, 0.4, 0.22]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.7} />
        </mesh>
      </group>
      <mesh position={[-0.25, 0.15, -0.35]} castShadow>
        <boxGeometry args={[0.22, 0.4, 0.22]} />
        <meshStandardMaterial color={COLORS.bullpug} roughness={0.7} />
      </mesh>
      <mesh position={[0.25, 0.15, -0.35]} castShadow>
        <boxGeometry args={[0.22, 0.4, 0.22]} />
        <meshStandardMaterial color={COLORS.bullpug} roughness={0.7} />
      </mesh>
      {/* Tail */}
      <mesh position={[0, 0.75, -0.55]} rotation={[0.5, 0, 0]}>
        <boxGeometry args={[0.15, 0.15, 0.3]} />
        <meshStandardMaterial color={COLORS.bullpug} />
      </mesh>
    </group>
  );
}

function Horn({ position, rotation }) {
  // Stack of shrinking cones for a tapered curved horn look
  return (
    <group position={position} rotation={rotation}>
      <mesh>
        <coneGeometry args={[0.085, 0.32, 8]} />
        <meshStandardMaterial color={COLORS.horn} metalness={0.4} roughness={0.4} />
      </mesh>
      <mesh position={[0, 0.18, 0.06]} rotation={[-0.3, 0, 0]}>
        <coneGeometry args={[0.058, 0.18, 8]} />
        <meshStandardMaterial color="#E5A12E" metalness={0.5} roughness={0.35} />
      </mesh>
    </group>
  );
}

// ───────────────────────────────────────────── Track (scrolling)

function Track({ speedRef }) {
  const groupRef = useRef();
  const tilesRef = useRef([]);
  const TILES = 16;
  const TILE_LEN = 8;

  // Build tile meshes
  const tiles = useMemo(() => Array.from({ length: TILES }, (_, i) => i), []);

  useFrame((_, dt) => {
    const ds = speedRef.current * dt;
    tilesRef.current.forEach((m) => {
      if (!m) return;
      m.position.z += ds;
      if (m.position.z > TILE_LEN) {
        m.position.z -= TILE_LEN * TILES;
      }
    });
  });

  return (
    <group ref={groupRef}>
      {tiles.map((i) => (
        <mesh
          key={i}
          ref={(el) => (tilesRef.current[i] = el)}
          position={[0, 0, -i * TILE_LEN + TILE_LEN]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <planeGeometry args={[5.5, TILE_LEN]} />
          <meshStandardMaterial color={i % 2 === 0 ? COLORS.trackA : COLORS.trackB} roughness={0.6} />
        </mesh>
      ))}
      {/* Track edges — neon mint glow strips */}
      {[-2.75, 2.75].map((x, i) => (
        <mesh key={i} position={[x, 0.02, -TRACK_LENGTH / 2]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[0.08, TRACK_LENGTH]} />
          <meshBasicMaterial color={COLORS.trackEdge} toneMapped={false} />
        </mesh>
      ))}
      {/* Lane divider lines */}
      {[-0.8, 0.8].map((x, i) => (
        <mesh key={i} position={[x, 0.01, -TRACK_LENGTH / 2]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[0.04, TRACK_LENGTH]} />
          <meshBasicMaterial color="#3a2a55" />
        </mesh>
      ))}
    </group>
  );
}

// ───────────────────────────────────────────── Obstacles

const OBSTACLE_TYPES = ["asteroid", "crystal", "ring"];

function Obstacle({ type, refData }) {
  const ref = useRef();
  useFrame(() => {
    if (ref.current) ref.current.position.copy(refData.position);
  });
  if (type === "asteroid") {
    return (
      <mesh ref={ref} castShadow>
        <icosahedronGeometry args={[0.55, 0]} />
        <meshStandardMaterial color={COLORS.asteroid} roughness={0.95} flatShading />
      </mesh>
    );
  }
  if (type === "crystal") {
    // tall crystal pillar — must jump or lane-switch
    return (
      <group ref={ref}>
        <mesh position={[0, 1.0, 0]} castShadow>
          <coneGeometry args={[0.4, 2.0, 5]} />
          <meshStandardMaterial color={COLORS.crystal} emissive={COLORS.crystal} emissiveIntensity={0.35} roughness={0.3} />
        </mesh>
      </group>
    );
  }
  // ring — slide through
  return (
    <group ref={ref}>
      <mesh position={[0, 1.4, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.9, 0.12, 8, 24]} />
        <meshStandardMaterial color={COLORS.ring} emissive={COLORS.ring} emissiveIntensity={0.5} />
      </mesh>
    </group>
  );
}

function Coin({ refData }) {
  const ref = useRef();
  useFrame((state, dt) => {
    if (!ref.current) return;
    ref.current.position.copy(refData.position);
    ref.current.rotation.y += dt * 4;
  });
  return (
    <mesh ref={ref}>
      <cylinderGeometry args={[0.18, 0.18, 0.05, 12]} />
      <meshStandardMaterial color={COLORS.coin} emissive={COLORS.coin} emissiveIntensity={0.5} metalness={0.8} roughness={0.2} />
    </mesh>
  );
}

// ───────────────────────────────────────────── World — manages spawning + collision

function World({ onScore, onDeath, controlState, runningRef }) {
  const audio = useGameAudio();
  const speedRef = useRef(FORWARD_SPEED_BASE);
  const playerXRef = useRef(0);
  const playerYRef = useRef(0);
  const playerVyRef = useRef(0);
  const slidingRef = useRef(false);
  const slideEndRef = useRef(0);
  const laneIdxRef = useRef(1);
  const obstaclesRef = useRef([]);
  const coinsRef = useRef([]);
  const spawnTrackRef = useRef(0);
  const elapsedRef = useRef(0);
  const distanceRef = useRef(0);
  const [obstaclesState, setObstaclesState] = useState([]);
  const [coinsState, setCoinsState] = useState([]);
  const isDeadRef = useRef(false);

  // Handle controls
  useEffect(() => {
    const c = controlState;
    if (c.action === "left" && laneIdxRef.current > 0) {
      laneIdxRef.current -= 1; audio.laneChange();
    } else if (c.action === "right" && laneIdxRef.current < 2) {
      laneIdxRef.current += 1; audio.laneChange();
    } else if (c.action === "jump" && playerYRef.current <= 0.001 && !slidingRef.current) {
      playerVyRef.current = JUMP_VELOCITY; audio.jump();
    } else if (c.action === "slide" && !slidingRef.current && playerYRef.current <= 0.001) {
      slidingRef.current = true;
      slideEndRef.current = performance.now() + SLIDE_DURATION_MS;
      audio.slide();
    }
  }, [controlState, audio]);

  const reset = useCallback(() => {
    speedRef.current = FORWARD_SPEED_BASE;
    playerXRef.current = 0;
    playerYRef.current = 0;
    playerVyRef.current = 0;
    slidingRef.current = false;
    laneIdxRef.current = 1;
    obstaclesRef.current = [];
    coinsRef.current = [];
    spawnTrackRef.current = 0;
    elapsedRef.current = 0;
    distanceRef.current = 0;
    isDeadRef.current = false;
    setObstaclesState([]);
    setCoinsState([]);
  }, []);

  // expose reset via runningRef hack
  useEffect(() => {
    runningRef.current = { ...runningRef.current, reset };
  }, [reset, runningRef]);

  useFrame((_, dt) => {
    if (isDeadRef.current || !runningRef.current?.running) return;
    dt = Math.min(dt, 1 / 30);
    elapsedRef.current += dt;
    distanceRef.current += speedRef.current * dt;
    speedRef.current += FORWARD_SPEED_RAMP * dt;

    // Player lane interp
    const targetX = LANES[laneIdxRef.current];
    playerXRef.current += (targetX - playerXRef.current) * Math.min(1, dt * 12);

    // Jump physics
    if (playerYRef.current > 0 || playerVyRef.current > 0) {
      playerVyRef.current += GRAVITY * dt;
      playerYRef.current += playerVyRef.current * dt;
      if (playerYRef.current < 0) {
        playerYRef.current = 0;
        playerVyRef.current = 0;
      }
    }

    // Slide timer
    if (slidingRef.current && performance.now() > slideEndRef.current) {
      slidingRef.current = false;
    }

    // Spawn ahead
    while (spawnTrackRef.current < distanceRef.current + SPAWN_AHEAD) {
      spawnTrackRef.current += 6 + Math.random() * 4;
      const spawnZ = -(spawnTrackRef.current - distanceRef.current);

      // 60% chance obstacle, 40% chance coin row
      if (Math.random() < 0.65) {
        const lane = Math.floor(Math.random() * 3);
        const type = OBSTACLE_TYPES[Math.floor(Math.random() * OBSTACLE_TYPES.length)];
        obstaclesRef.current.push({
          id: Math.random(),
          type,
          lane,
          position: new THREE.Vector3(LANES[lane], 0, spawnZ),
        });
      } else {
        // coin trail
        const lane = Math.floor(Math.random() * 3);
        for (let i = 0; i < 5; i++) {
          coinsRef.current.push({
            id: Math.random() + i,
            lane,
            position: new THREE.Vector3(LANES[lane], 0.7, spawnZ - i * 1.2),
            collected: false,
          });
        }
      }
    }

    // Move obstacles & coins toward camera (positive Z)
    const ds = speedRef.current * dt;
    obstaclesRef.current.forEach((o) => { o.position.z += ds; });
    coinsRef.current.forEach((c) => { c.position.z += ds; });

    // Cull off-camera
    obstaclesRef.current = obstaclesRef.current.filter((o) => o.position.z < 8);
    coinsRef.current = coinsRef.current.filter((c) => c.position.z < 8 && !c.collected);

    // Collisions — player roughly at z=0..1.0, x=playerX, y=playerY
    const px = playerXRef.current;
    const py = playerYRef.current;
    const playerRadius = 0.5;
    const playerLane = laneIdxRef.current;

    for (const o of obstaclesRef.current) {
      if (Math.abs(o.position.z) > 1.2) continue;
      if (o.lane !== playerLane) continue;
      // Type-specific dodging
      if (o.type === "asteroid") {
        // jump over
        if (py < 0.85) {
          die();
          return;
        }
      } else if (o.type === "ring") {
        // slide under
        if (!slidingRef.current) {
          die();
          return;
        }
      } else {
        // crystal — must lane switch (always fatal in lane)
        if (Math.abs(o.position.x - px) < playerRadius + 0.4) {
          die();
          return;
        }
      }
    }

    let coinPicked = 0;
    for (const c of coinsRef.current) {
      if (c.collected) continue;
      if (Math.abs(c.position.z) > 1.0) continue;
      if (c.lane !== playerLane) continue;
      if (Math.abs(c.position.x - px) < 0.7 && Math.abs(c.position.y - (py + 0.5)) < 0.8) {
        c.collected = true;
        coinPicked += 1;
      }
    }
    if (coinPicked) {
      audio.coin();
      onScore({ coins: coinPicked, distance: distanceRef.current });
    } else {
      onScore({ coins: 0, distance: distanceRef.current });
    }

    setObstaclesState([...obstaclesRef.current]);
    setCoinsState([...coinsRef.current.filter((c) => !c.collected)]);

    function die() {
      isDeadRef.current = true;
      audio.death();
      onDeath({ distance: distanceRef.current });
    }
  });

  return (
    <>
      <Track speedRef={speedRef} />
      <Bullpug refX={playerXRef} refY={playerYRef} sliding={slidingRef} running={runningRef} />
      {obstaclesState.map((o) => (
        <Obstacle key={o.id} type={o.type} refData={o} />
      ))}
      {coinsState.map((c) => (
        <Coin key={c.id} refData={c} />
      ))}
    </>
  );
}

// ───────────────────────────────────────────── Page

export default function Phase1Runner3D() {
  const [score, setScore] = useState({ coins: 0, distance: 0 });
  const [running, setRunning] = useState(false);
  const [gameOver, setGameOver] = useState(null);
  const [bestDistance, setBestDistance] = useState(() => {
    try { return parseInt(localStorage.getItem("bullpug_runner3d_best") || "0", 10); } catch (e) { return 0; }
  });
  const [controlState, setControlState] = useState({ action: null, ts: 0 });
  const runningRef = useRef({ running: false });
  const totalCoinsRef = useRef(0);

  const fireAction = useCallback((action) => {
    if (!runningRef.current.running) return;
    setControlState({ action, ts: performance.now() });
  }, []);

  // Keyboard
  useEffect(() => {
    const onKey = (e) => {
      const k = e.key.toLowerCase();
      if (k === "arrowleft" || k === "a") fireAction("left");
      else if (k === "arrowright" || k === "d") fireAction("right");
      else if (k === "arrowup" || k === "w" || k === " ") { e.preventDefault(); fireAction("jump"); }
      else if (k === "arrowdown" || k === "s") fireAction("slide");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fireAction]);

  // Touch
  useEffect(() => {
    let startX = 0, startY = 0, startT = 0;
    const onStart = (e) => {
      const t = e.changedTouches?.[0];
      if (!t) return;
      startX = t.clientX; startY = t.clientY; startT = performance.now();
    };
    const onEnd = (e) => {
      const t = e.changedTouches?.[0];
      if (!t) return;
      const dx = t.clientX - startX;
      const dy = t.clientY - startY;
      const dt = performance.now() - startT;
      if (dt > 700) return;
      const ax = Math.abs(dx), ay = Math.abs(dy);
      if (Math.max(ax, ay) < 30) return;
      if (ax > ay) fireAction(dx > 0 ? "right" : "left");
      else fireAction(dy > 0 ? "slide" : "jump");
    };
    window.addEventListener("touchstart", onStart, { passive: true });
    window.addEventListener("touchend", onEnd, { passive: true });
    return () => {
      window.removeEventListener("touchstart", onStart);
      window.removeEventListener("touchend", onEnd);
    };
  }, [fireAction]);

  const onScoreUpdate = useCallback((s) => {
    if (s.coins) totalCoinsRef.current += s.coins;
    setScore({ coins: totalCoinsRef.current, distance: s.distance });
  }, []);

  const onDeath = useCallback((d) => {
    runningRef.current.running = false;
    setRunning(false);
    setGameOver(d);
    try {
      if (d.distance > bestDistance) {
        localStorage.setItem("bullpug_runner3d_best", String(Math.floor(d.distance)));
        setBestDistance(Math.floor(d.distance));
      }
    } catch (e) { /* ignore */ }
  }, [bestDistance]);

  const start = () => {
    totalCoinsRef.current = 0;
    setScore({ coins: 0, distance: 0 });
    setGameOver(null);
    runningRef.current.reset?.();
    runningRef.current.running = true;
    setRunning(true);
  };

  return (
    <div className="relative w-full h-screen bg-black overflow-hidden" data-testid="runner-3d-page">
      {/* 3D Canvas */}
      <Canvas
        shadows
        camera={{ position: [0, 2.7, 4.5], fov: 70 }}
        gl={{ antialias: true, powerPreference: "high-performance" }}
        style={{ background: COLORS.bg }}
      >
        <fog attach="fog" args={[COLORS.bg, 18, 70]} />
        <ambientLight intensity={0.35} />
        <directionalLight position={[5, 8, 4]} intensity={0.7} castShadow />
        <pointLight position={[0, 4, 0]} intensity={0.7} color="#D946EF" />
        <pointLight position={[0, 4, -20]} intensity={0.6} color="#00FFA3" />

        {/* Cosmic skybox: starfield + sparkles */}
        <Stars radius={120} depth={60} count={3500} factor={4} fade saturation={0.6} />
        <Sparkles count={120} scale={[40, 25, 40]} size={3} speed={0.3} color="#D946EF" />

        {/* Nebula gradient behind — large emissive sphere with vertex colors via gradient material */}
        <mesh position={[0, 5, -90]} rotation={[0, 0, 0]}>
          <planeGeometry args={[180, 90]} />
          <meshBasicMaterial color="#1a0942" depthWrite={false} />
        </mesh>
        <mesh position={[-25, 4, -55]} rotation={[0, 0.3, 0]}>
          <sphereGeometry args={[6, 16, 12]} />
          <meshBasicMaterial color="#D946EF" transparent opacity={0.18} />
        </mesh>
        <mesh position={[28, 6, -45]} rotation={[0, 0.3, 0]}>
          <sphereGeometry args={[5, 16, 12]} />
          <meshBasicMaterial color="#00C2FF" transparent opacity={0.16} />
        </mesh>

        <World
          onScore={onScoreUpdate}
          onDeath={onDeath}
          controlState={controlState}
          runningRef={runningRef}
        />
      </Canvas>

      {/* HUD */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-4 left-4 right-4 flex items-start justify-between">
          <div data-testid="runner-3d-hud-score">
            <div className="text-[10px] uppercase tracking-[0.25em] text-[#00FFA3] font-bold mb-1" style={{ fontFamily: "Orbitron" }}>
              Distance
            </div>
            <div className="text-3xl font-black text-white tabular-nums" style={{ fontFamily: "Orbitron" }}>
              {Math.floor(score.distance)}m
            </div>
            <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-[#F5D300] font-bold mb-1" style={{ fontFamily: "Orbitron" }}>
              Coins
            </div>
            <div className="text-xl font-bold text-[#F5D300] tabular-nums" style={{ fontFamily: "Orbitron" }}>
              ✦ {score.coins}
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-[0.25em] text-slate-400 font-bold mb-1" style={{ fontFamily: "Orbitron" }}>
              Best
            </div>
            <div className="text-xl font-bold text-[#D946EF] tabular-nums" style={{ fontFamily: "Orbitron" }}>
              {bestDistance}m
            </div>
          </div>
        </div>
      </div>

      {/* Start screen */}
      {!running && !gameOver && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm" data-testid="runner-3d-start-screen">
          <div className="max-w-sm text-center px-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30 text-[#00FFA3] text-[10px] font-bold uppercase tracking-[0.25em] mb-4">
              Phase 1 · 3D
            </div>
            <h1 className="text-4xl sm:text-5xl font-black text-white mb-3 leading-[1.05]" style={{ fontFamily: "Orbitron" }}>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#D946EF] via-[#00FFA3] to-[#FFD700]">
                COSMIC RUNNER
              </span>
            </h1>
            <p className="text-slate-300 text-sm mb-6 leading-relaxed">
              Run forever through the deep PugChain. Dodge asteroids, slide through ion rings, leap over crystal pillars. Collect cosmic coins for the Festival of Barks leaderboard.
            </p>
            <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 font-mono mb-6">
              <div>← / A · Left</div>
              <div>→ / D · Right</div>
              <div>↑ / W / Space · Jump</div>
              <div>↓ / S · Slide</div>
              <div className="col-span-2 mt-1 text-slate-500">Mobile · swipe in any direction</div>
            </div>
            <button
              type="button"
              onClick={start}
              data-testid="runner-3d-start-btn"
              className="px-8 py-3 rounded-full bg-gradient-to-r from-[#00FFA3] to-[#00C2FF] text-black font-black uppercase tracking-wider hover:scale-105 transition-transform"
              style={{ fontFamily: "Orbitron" }}
            >
              Begin Run
            </button>
          </div>
        </div>
      )}

      {/* Game over */}
      {gameOver && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/70 backdrop-blur-sm" data-testid="runner-3d-gameover-screen">
          <div className="max-w-sm text-center px-6">
            <div className="text-[10px] uppercase tracking-[0.25em] text-[#EF4444] font-bold mb-2">Run Ended</div>
            <h2 className="text-4xl font-black text-white mb-4" style={{ fontFamily: "Orbitron" }}>
              {Math.floor(gameOver.distance)}<span className="text-base ml-1 text-slate-400">m</span>
            </h2>
            <p className="text-slate-300 text-sm mb-2">
              Cosmic coins: <span className="text-[#F5D300] font-bold">✦ {score.coins}</span>
            </p>
            <p className="text-[11px] text-slate-500 mb-6">
              {gameOver.distance > bestDistance ? "NEW PERSONAL BEST" : `Best · ${bestDistance}m`}
            </p>
            <button
              type="button"
              onClick={start}
              data-testid="runner-3d-restart-btn"
              className="px-8 py-3 rounded-full bg-[#00FFA3] text-black font-black uppercase tracking-wider hover:scale-105 transition-transform"
              style={{ fontFamily: "Orbitron" }}
            >
              Run Again
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
