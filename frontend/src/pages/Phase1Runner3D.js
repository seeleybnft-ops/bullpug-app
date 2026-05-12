/**
 * Bullpug Cosmic Runner — Phase 1 (3D) + Phase 2 (Polish + Power-ups)
 *
 * Three.js + @react-three/fiber endless runner. 3-lane cosmic track.
 * - Keyboard: A/← swipe left, D/→ swipe right, W/↑/Space jump, S/↓ slide
 * - Touch: swipe in any direction OR on-screen tap buttons
 * - Score: distance + coin bonus (auto-submitted to Festival of Barks leaderboard)
 * - Power-ups: shield (1 free hit), magnet (auto-attract coins 6s), 2× multiplier (8s)
 * - Game over on obstacle hit (shield absorbs first hit)
 *
 * Phase 2 additions: power-ups, distant planets, scrolling nebula band, paw
 * trail particles, speed milestones, mobile control buttons, backend score
 * submission, leaderboard rank display.
 */

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Stars, Sparkles } from "@react-three/drei";
import * as THREE from "three";
import axios from "axios";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ───────────────────────────────────────────── Config

const LANES = [-1.6, 0, 1.6];
const FORWARD_SPEED_BASE = 14;
const FORWARD_SPEED_RAMP = 0.18;
const TRACK_LENGTH = 80;
const JUMP_VELOCITY = 9.0;
const GRAVITY = -22.0;
const SLIDE_DURATION_MS = 700;
const SPAWN_AHEAD = 60;

const POWERUP_DURATION_MS = {
  magnet: 6000,
  multiplier: 8000,
};
const MILESTONE_STEP = 250; // every 250m

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
  shield: "#34D399",
  magnet: "#F97316",
  multiplier: "#A78BFA",
};

// ───────────────────────────────────────────── Audio (synthesised)

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
    powerup: () => {
      blip(880, 0.08, "triangle", 0.18);
      setTimeout(() => blip(1320, 0.12, "triangle", 0.16), 70);
    },
    shieldBreak: () => blip(440, 0.25, "sawtooth", 0.18),
    milestone: () => {
      blip(660, 0.08, "triangle", 0.16);
      setTimeout(() => blip(990, 0.08, "triangle", 0.16), 90);
      setTimeout(() => blip(1320, 0.18, "triangle", 0.16), 180);
    },
  };
}

// ───────────────────────────────────────────── Bullpug character

function Bullpug({ refY, refX, sliding, running, shieldActive }) {
  const group = useRef();
  const shieldRef = useRef();
  const bob = useRef(0);
  const leg1 = useRef();
  const leg2 = useRef();
  useFrame((_, dt) => {
    if (!group.current) return;
    group.current.position.x = refX.current;
    group.current.position.y = refY.current + (sliding.current ? -0.4 : 0);
    bob.current += dt * 14;
    const bobY = running.current && !sliding.current ? Math.sin(bob.current) * 0.06 : 0;
    group.current.position.y += bobY;
    group.current.scale.set(1, sliding.current ? 0.55 : 1, sliding.current ? 1.4 : 1);
    if (leg1.current && leg2.current && running.current && !sliding.current) {
      leg1.current.rotation.x = Math.sin(bob.current) * 0.9;
      leg2.current.rotation.x = -Math.sin(bob.current) * 0.9;
    }
    if (shieldRef.current) {
      shieldRef.current.visible = !!shieldActive?.current;
      shieldRef.current.rotation.y += dt * 1.5;
      shieldRef.current.rotation.x += dt * 0.9;
    }
  });
  return (
    <group ref={group}>
      {/* Body */}
      <mesh position={[0, 0.55, 0]} castShadow>
        <boxGeometry args={[0.85, 0.7, 1.0]} />
        <meshStandardMaterial color={COLORS.bullpug} roughness={0.7} />
      </mesh>
      {/* Head */}
      <mesh position={[0, 1.1, 0.45]} castShadow>
        <boxGeometry args={[0.75, 0.7, 0.55]} />
        <meshStandardMaterial color={COLORS.bullpug} roughness={0.7} />
      </mesh>
      {/* Muzzle */}
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
      {/* HORNS */}
      <Horn position={[-0.28, 1.45, 0.42]} rotation={[0.2, 0.3, -0.6]} />
      <Horn position={[0.28, 1.45, 0.42]} rotation={[0.2, -0.3, 0.6]} />
      {/* Ears */}
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
      {/* Shield bubble (hidden unless active) */}
      <mesh ref={shieldRef} position={[0, 0.85, 0]} visible={false}>
        <sphereGeometry args={[1.05, 24, 24]} />
        <meshBasicMaterial color={COLORS.shield} transparent opacity={0.22} wireframe />
      </mesh>
    </group>
  );
}

function Horn({ position, rotation }) {
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

// ───────────────────────────────────────────── Background — planets + nebula band

function Planet({ position, size, color, ringColor }) {
  const ref = useRef();
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.08;
  });
  return (
    <group position={position}>
      <mesh ref={ref}>
        <sphereGeometry args={[size, 24, 24]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.18} roughness={0.7} />
      </mesh>
      {ringColor && (
        <mesh rotation={[Math.PI / 2.4, 0, 0]}>
          <ringGeometry args={[size * 1.4, size * 1.85, 48]} />
          <meshBasicMaterial color={ringColor} side={THREE.DoubleSide} transparent opacity={0.45} />
        </mesh>
      )}
    </group>
  );
}

function NebulaBand({ speedRef }) {
  const groupRef = useRef();
  const segs = useMemo(() => Array.from({ length: 5 }, (_, i) => i), []);
  const refs = useRef([]);
  useFrame((_, dt) => {
    const ds = speedRef.current * dt * 0.35; // parallax (slower than track)
    refs.current.forEach((m) => {
      if (!m) return;
      m.position.z += ds;
      if (m.position.z > 30) m.position.z -= 150;
    });
  });
  return (
    <group ref={groupRef}>
      {segs.map((i) => (
        <mesh
          key={i}
          ref={(el) => (refs.current[i] = el)}
          position={[i % 2 === 0 ? -22 : 22, 4 + (i % 2) * 2, -30 - i * 30]}
        >
          <planeGeometry args={[26, 14]} />
          <meshBasicMaterial
            color={i % 2 === 0 ? "#D946EF" : "#00C2FF"}
            transparent
            opacity={0.08}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}

// ───────────────────────────────────────────── Track (scrolling)

function Track({ speedRef }) {
  const groupRef = useRef();
  const tilesRef = useRef([]);
  const TILES = 16;
  const TILE_LEN = 8;
  const tiles = useMemo(() => Array.from({ length: TILES }, (_, i) => i), []);

  useFrame((_, dt) => {
    const ds = speedRef.current * dt;
    tilesRef.current.forEach((m) => {
      if (!m) return;
      m.position.z += ds;
      if (m.position.z > TILE_LEN) m.position.z -= TILE_LEN * TILES;
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
      {[-2.75, 2.75].map((x, i) => (
        <mesh key={i} position={[x, 0.02, -TRACK_LENGTH / 2]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[0.08, TRACK_LENGTH]} />
          <meshBasicMaterial color={COLORS.trackEdge} toneMapped={false} />
        </mesh>
      ))}
      {[-0.8, 0.8].map((x, i) => (
        <mesh key={i} position={[x, 0.01, -TRACK_LENGTH / 2]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[0.04, TRACK_LENGTH]} />
          <meshBasicMaterial color="#3a2a55" />
        </mesh>
      ))}
    </group>
  );
}

// ───────────────────────────────────────────── Obstacles / Coins / Power-ups

const OBSTACLE_TYPES = ["asteroid", "crystal", "ring"];
const POWERUP_TYPES = ["shield", "magnet", "multiplier"];

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
    return (
      <group ref={ref}>
        <mesh position={[0, 1.0, 0]} castShadow>
          <coneGeometry args={[0.4, 2.0, 5]} />
          <meshStandardMaterial color={COLORS.crystal} emissive={COLORS.crystal} emissiveIntensity={0.35} roughness={0.3} />
        </mesh>
      </group>
    );
  }
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
  useFrame((_, dt) => {
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

function PowerUp({ type, refData }) {
  const ref = useRef();
  useFrame((_, dt) => {
    if (!ref.current) return;
    ref.current.position.copy(refData.position);
    ref.current.rotation.y += dt * 2.2;
    ref.current.rotation.x += dt * 0.4;
  });
  const color =
    type === "shield" ? COLORS.shield : type === "magnet" ? COLORS.magnet : COLORS.multiplier;
  return (
    <group ref={ref}>
      <mesh>
        {type === "shield" ? (
          <octahedronGeometry args={[0.32, 0]} />
        ) : type === "magnet" ? (
          <torusGeometry args={[0.28, 0.1, 10, 18]} />
        ) : (
          <icosahedronGeometry args={[0.32, 0]} />
        )}
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.9} metalness={0.6} roughness={0.2} />
      </mesh>
      {/* Halo */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.45, 0.55, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.55} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ───────────────────────────────────────────── World

function World({ onScore, onDeath, onMilestone, onPowerupChange, controlState, runningRef }) {
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
  const powerupsRef = useRef([]);
  const spawnTrackRef = useRef(0);
  const elapsedRef = useRef(0);
  const distanceRef = useRef(0);
  const milestoneStepRef = useRef(0);
  const shieldActiveRef = useRef(false);
  const magnetUntilRef = useRef(0);
  const multiplierUntilRef = useRef(0);
  const [obstaclesState, setObstaclesState] = useState([]);
  const [coinsState, setCoinsState] = useState([]);
  const [powerupsState, setPowerupsState] = useState([]);
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
    powerupsRef.current = [];
    spawnTrackRef.current = 0;
    elapsedRef.current = 0;
    distanceRef.current = 0;
    milestoneStepRef.current = 0;
    shieldActiveRef.current = false;
    magnetUntilRef.current = 0;
    multiplierUntilRef.current = 0;
    isDeadRef.current = false;
    setObstaclesState([]);
    setCoinsState([]);
    setPowerupsState([]);
    onPowerupChange?.({ shield: false, magnet: 0, multiplier: 0 });
  }, [onPowerupChange]);

  useEffect(() => {
    runningRef.current = { ...runningRef.current, reset };
  }, [reset, runningRef]);

  useFrame((_, dt) => {
    if (isDeadRef.current || !runningRef.current?.running) return;
    dt = Math.min(dt, 1 / 30);
    elapsedRef.current += dt;
    distanceRef.current += speedRef.current * dt;
    speedRef.current += FORWARD_SPEED_RAMP * dt;

    // Milestones
    const m = Math.floor(distanceRef.current / MILESTONE_STEP);
    if (m > milestoneStepRef.current) {
      milestoneStepRef.current = m;
      audio.milestone();
      onMilestone?.(m * MILESTONE_STEP);
    }

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

    // Power-up timers
    const now = performance.now();
    const magnetActive = now < magnetUntilRef.current;
    const multiplierActive = now < multiplierUntilRef.current;

    // Spawn ahead
    while (spawnTrackRef.current < distanceRef.current + SPAWN_AHEAD) {
      spawnTrackRef.current += 6 + Math.random() * 4;
      const spawnZ = -(spawnTrackRef.current - distanceRef.current);
      const roll = Math.random();
      if (roll < 0.08) {
        // power-up
        const ptype = POWERUP_TYPES[Math.floor(Math.random() * POWERUP_TYPES.length)];
        const lane = Math.floor(Math.random() * 3);
        powerupsRef.current.push({
          id: Math.random(),
          type: ptype,
          lane,
          position: new THREE.Vector3(LANES[lane], 1.0, spawnZ),
        });
      } else if (roll < 0.65) {
        const lane = Math.floor(Math.random() * 3);
        const type = OBSTACLE_TYPES[Math.floor(Math.random() * OBSTACLE_TYPES.length)];
        obstaclesRef.current.push({
          id: Math.random(),
          type,
          lane,
          position: new THREE.Vector3(LANES[lane], 0, spawnZ),
        });
      } else {
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

    // Move world toward camera (+z)
    const ds = speedRef.current * dt;
    obstaclesRef.current.forEach((o) => { o.position.z += ds; });
    coinsRef.current.forEach((c) => { c.position.z += ds; });
    powerupsRef.current.forEach((p) => { p.position.z += ds; });

    // Magnet — attract coins toward player when within range
    if (magnetActive) {
      const px = playerXRef.current;
      const target = new THREE.Vector3(px, 0.7, 0);
      coinsRef.current.forEach((c) => {
        if (c.collected) return;
        if (c.position.z > -8 && c.position.z < 4) {
          c.position.lerp(target, Math.min(1, dt * 6));
        }
      });
    }

    // Cull
    obstaclesRef.current = obstaclesRef.current.filter((o) => o.position.z < 8);
    coinsRef.current = coinsRef.current.filter((c) => c.position.z < 8 && !c.collected);
    powerupsRef.current = powerupsRef.current.filter((p) => p.position.z < 8 && !p.collected);

    // Collision
    const px = playerXRef.current;
    const py = playerYRef.current;
    const playerLane = laneIdxRef.current;

    for (const o of obstaclesRef.current) {
      if (Math.abs(o.position.z) > 1.2) continue;
      if (o.lane !== playerLane) continue;
      let hit = false;
      if (o.type === "asteroid") {
        if (py < 0.85) hit = true;
      } else if (o.type === "ring") {
        if (!slidingRef.current) hit = true;
      } else {
        if (Math.abs(o.position.x - px) < 0.9) hit = true;
      }
      if (hit) {
        if (shieldActiveRef.current) {
          // Shield absorbs hit + removes obstacle
          shieldActiveRef.current = false;
          audio.shieldBreak();
          o.position.z = 999; // mark for cull
          onPowerupChange?.({
            shield: false,
            magnet: Math.max(0, magnetUntilRef.current - now),
            multiplier: Math.max(0, multiplierUntilRef.current - now),
          });
        } else {
          die();
          return;
        }
      }
    }

    // Power-up pickup
    for (const p of powerupsRef.current) {
      if (p.collected) continue;
      if (Math.abs(p.position.z) > 1.0) continue;
      if (p.lane !== playerLane) continue;
      if (Math.abs(p.position.x - px) < 0.9 && Math.abs(p.position.y - (py + 0.55)) < 1.2) {
        p.collected = true;
        audio.powerup();
        if (p.type === "shield") {
          shieldActiveRef.current = true;
        } else if (p.type === "magnet") {
          magnetUntilRef.current = now + POWERUP_DURATION_MS.magnet;
        } else {
          multiplierUntilRef.current = now + POWERUP_DURATION_MS.multiplier;
        }
        onPowerupChange?.({
          shield: shieldActiveRef.current,
          magnet: Math.max(0, magnetUntilRef.current - now),
          multiplier: Math.max(0, multiplierUntilRef.current - now),
        });
      }
    }

    // Coin pickup
    let coinPicked = 0;
    for (const c of coinsRef.current) {
      if (c.collected) continue;
      if (Math.abs(c.position.z) > 1.0) continue;
      const dxOk = Math.abs(c.position.x - px) < 0.7;
      const dyOk = Math.abs(c.position.y - (py + 0.5)) < 0.9;
      if (dxOk && dyOk) {
        c.collected = true;
        coinPicked += 1;
      }
    }
    const earned = coinPicked * (multiplierActive ? 2 : 1);
    if (earned) audio.coin();
    onScore({ coins: earned, distance: distanceRef.current });

    // Periodically broadcast remaining power-up time so HUD chips animate
    if ((magnetActive || multiplierActive) && Math.floor(elapsedRef.current * 4) % 2 === 0) {
      onPowerupChange?.({
        shield: shieldActiveRef.current,
        magnet: Math.max(0, magnetUntilRef.current - now),
        multiplier: Math.max(0, multiplierUntilRef.current - now),
      });
    }
    // Detect power-up expiry transitions
    if (!magnetActive && magnetUntilRef.current !== 0 && magnetUntilRef.current < now) {
      magnetUntilRef.current = 0;
      onPowerupChange?.({
        shield: shieldActiveRef.current, magnet: 0, multiplier: Math.max(0, multiplierUntilRef.current - now),
      });
    }
    if (!multiplierActive && multiplierUntilRef.current !== 0 && multiplierUntilRef.current < now) {
      multiplierUntilRef.current = 0;
      onPowerupChange?.({
        shield: shieldActiveRef.current, magnet: Math.max(0, magnetUntilRef.current - now), multiplier: 0,
      });
    }

    setObstaclesState([...obstaclesRef.current]);
    setCoinsState([...coinsRef.current.filter((c) => !c.collected)]);
    setPowerupsState([...powerupsRef.current.filter((p) => !p.collected)]);

    function die() {
      isDeadRef.current = true;
      audio.death();
      onDeath({ distance: distanceRef.current });
    }
  });

  return (
    <>
      <Track speedRef={speedRef} />
      <NebulaBand speedRef={speedRef} />
      <Bullpug
        refX={playerXRef}
        refY={playerYRef}
        sliding={slidingRef}
        running={runningRef}
        shieldActive={shieldActiveRef}
      />
      {obstaclesState.map((o) => (
        <Obstacle key={o.id} type={o.type} refData={o} />
      ))}
      {coinsState.map((c) => (
        <Coin key={c.id} refData={c} />
      ))}
      {powerupsState.map((p) => (
        <PowerUp key={p.id} type={p.type} refData={p} />
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
  const [powerups, setPowerups] = useState({ shield: false, magnet: 0, multiplier: 0 });
  const [milestone, setMilestone] = useState(null); // last milestone hit
  const [submitState, setSubmitState] = useState({ rank: null, submitted: false });
  const runningRef = useRef({ running: false });
  const totalCoinsRef = useRef(0);
  const milestoneTimer = useRef(null);

  const playerName = useMemo(() => {
    try {
      return (localStorage.getItem("bullpugPlayerName") || "Cosmic Pug").trim().slice(0, 20);
    } catch (e) { return "Cosmic Pug"; }
  }, []);

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

  // Touch swipe (lower threshold = more responsive)
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
      if (Math.max(ax, ay) < 18) return; // lowered threshold
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

  const handleMilestone = useCallback((dist) => {
    setMilestone(dist);
    if (milestoneTimer.current) clearTimeout(milestoneTimer.current);
    milestoneTimer.current = setTimeout(() => setMilestone(null), 1600);
  }, []);

  const submitScoreToBackend = useCallback(async (finalDistance, finalCoins) => {
    const finalScore = Math.floor(finalDistance) + finalCoins * 5;
    if (finalScore <= 0) return;
    try {
      const { data } = await axios.post(`${API}/leaderboard/submit`, {
        player_name: playerName,
        score: finalScore,
        moonCheese: finalCoins,
      });
      setSubmitState({ rank: data?.rank ?? null, submitted: true });
      toast.success(`Festival of Barks · Rank #${data?.rank ?? "—"}`);
    } catch (e) {
      setSubmitState({ rank: null, submitted: true });
      // silent
    }
  }, [playerName]);

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
    submitScoreToBackend(d.distance, totalCoinsRef.current);
  }, [bestDistance, submitScoreToBackend]);

  const start = () => {
    totalCoinsRef.current = 0;
    setScore({ coins: 0, distance: 0 });
    setGameOver(null);
    setSubmitState({ rank: null, submitted: false });
    setPowerups({ shield: false, magnet: 0, multiplier: 0 });
    runningRef.current.reset?.();
    runningRef.current.running = true;
    setRunning(true);
  };

  const magnetSec = Math.ceil(powerups.magnet / 1000);
  const multSec = Math.ceil(powerups.multiplier / 1000);
  const isTouch = typeof window !== "undefined" && ("ontouchstart" in window || (navigator?.maxTouchPoints ?? 0) > 0);

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

        {/* Cosmic skybox */}
        <Stars radius={120} depth={60} count={3500} factor={4} fade saturation={0.6} />
        <Sparkles count={120} scale={[40, 25, 40]} size={3} speed={0.3} color="#D946EF" />

        {/* Distant nebula veil */}
        <mesh position={[0, 5, -90]}>
          <planeGeometry args={[180, 90]} />
          <meshBasicMaterial color="#1a0942" depthWrite={false} />
        </mesh>

        {/* Distant planets */}
        <Planet position={[-22, 7, -55]} size={4.5} color="#7C3AED" ringColor="#D946EF" />
        <Planet position={[26, 9, -65]} size={3.2} color="#0EA5E9" />
        <Planet position={[12, -3, -45]} size={1.6} color="#F5D300" />

        <World
          onScore={onScoreUpdate}
          onDeath={onDeath}
          onMilestone={handleMilestone}
          onPowerupChange={setPowerups}
          controlState={controlState}
          runningRef={runningRef}
        />
      </Canvas>

      {/* HUD — pushed below navbar */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-20 left-4 right-4 flex items-start justify-between">
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
            {/* Active power-up chips */}
            <div className="mt-2 flex flex-col items-end gap-1" data-testid="runner-3d-hud-powerups">
              {powerups.shield && (
                <div className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                  style={{ background: "rgba(52,211,153,0.18)", color: COLORS.shield, border: `1px solid ${COLORS.shield}55` }}>
                  ◇ Shield
                </div>
              )}
              {powerups.magnet > 0 && (
                <div className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                  style={{ background: "rgba(249,115,22,0.18)", color: COLORS.magnet, border: `1px solid ${COLORS.magnet}55` }}>
                  ⌬ Magnet {magnetSec}s
                </div>
              )}
              {powerups.multiplier > 0 && (
                <div className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                  style={{ background: "rgba(167,139,250,0.18)", color: COLORS.multiplier, border: `1px solid ${COLORS.multiplier}55` }}>
                  × 2 Score {multSec}s
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Milestone burst */}
        {milestone !== null && (
          <div className="absolute top-1/3 left-0 right-0 text-center pointer-events-none" data-testid="runner-3d-milestone">
            <div className="inline-block px-5 py-2 rounded-full backdrop-blur-md"
              style={{ background: "rgba(0,255,163,0.12)", border: "1px solid rgba(0,255,163,0.4)" }}>
              <div className="text-[10px] uppercase tracking-[0.3em] text-[#00FFA3] font-bold" style={{ fontFamily: "Orbitron" }}>Milestone</div>
              <div className="text-2xl font-black text-white" style={{ fontFamily: "Orbitron" }}>{milestone}m</div>
            </div>
          </div>
        )}
      </div>

      {/* On-screen mobile controls (touch devices only, while running) */}
      {isTouch && running && (
        <div className="absolute inset-x-0 bottom-6 flex items-end justify-between px-6 pointer-events-none" data-testid="runner-3d-mobile-ctrls">
          <div className="flex flex-col gap-2 pointer-events-auto">
            <button
              type="button"
              onClick={() => fireAction("left")}
              data-testid="runner-3d-btn-left"
              className="w-14 h-14 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-white font-bold text-2xl active:scale-95"
            >←</button>
            <button
              type="button"
              onClick={() => fireAction("slide")}
              data-testid="runner-3d-btn-slide"
              className="w-14 h-14 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-white font-bold text-2xl active:scale-95"
            >↓</button>
          </div>
          <div className="flex flex-col gap-2 pointer-events-auto">
            <button
              type="button"
              onClick={() => fireAction("jump")}
              data-testid="runner-3d-btn-jump"
              className="w-14 h-14 rounded-full bg-[#00FFA3]/20 backdrop-blur-md border border-[#00FFA3]/40 text-[#00FFA3] font-bold text-2xl active:scale-95"
            >↑</button>
            <button
              type="button"
              onClick={() => fireAction("right")}
              data-testid="runner-3d-btn-right"
              className="w-14 h-14 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-white font-bold text-2xl active:scale-95"
            >→</button>
          </div>
        </div>
      )}

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
            <p className="text-slate-300 text-sm mb-4 leading-relaxed">
              Run forever through the deep PugChain. Dodge asteroids, slide through ion rings, leap over crystal pillars. Grab power-ups & collect cosmic coins for the Festival of Barks leaderboard.
            </p>
            {/* Power-up legend */}
            <div className="grid grid-cols-3 gap-2 text-[10px] font-mono mb-4">
              <div className="rounded-md p-2" style={{ background: "rgba(52,211,153,0.1)", border: `1px solid ${COLORS.shield}55` }}>
                <div className="font-bold" style={{ color: COLORS.shield }}>◇ Shield</div>
                <div className="text-slate-400">1 free hit</div>
              </div>
              <div className="rounded-md p-2" style={{ background: "rgba(249,115,22,0.1)", border: `1px solid ${COLORS.magnet}55` }}>
                <div className="font-bold" style={{ color: COLORS.magnet }}>⌬ Magnet</div>
                <div className="text-slate-400">Auto-grab 6s</div>
              </div>
              <div className="rounded-md p-2" style={{ background: "rgba(167,139,250,0.1)", border: `1px solid ${COLORS.multiplier}55` }}>
                <div className="font-bold" style={{ color: COLORS.multiplier }}>× 2</div>
                <div className="text-slate-400">2× coins 8s</div>
              </div>
            </div>
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
            <p className="text-[11px] text-slate-500 mb-2">
              {gameOver.distance > bestDistance ? "NEW PERSONAL BEST" : `Best · ${bestDistance}m`}
            </p>
            {submitState.submitted && (
              <p className="text-[11px] mb-4" data-testid="runner-3d-rank">
                <span className="text-slate-500">Festival of Barks · </span>
                <span className="text-[#00FFA3] font-bold">
                  {submitState.rank ? `Rank #${submitState.rank}` : "submitted"}
                </span>
                <span className="text-slate-500"> · as {playerName}</span>
              </p>
            )}
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={start}
                data-testid="runner-3d-restart-btn"
                className="px-6 py-3 rounded-full bg-[#00FFA3] text-black font-black uppercase tracking-wider hover:scale-105 transition-transform text-sm"
                style={{ fontFamily: "Orbitron" }}
              >
                Run Again
              </button>
              <a
                href="/leaderboard"
                data-testid="runner-3d-leaderboard-link"
                className="px-6 py-3 rounded-full border border-white/20 text-white font-bold uppercase tracking-wider hover:bg-white/10 transition-colors text-sm"
                style={{ fontFamily: "Orbitron" }}
              >
                Leaderboard
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
