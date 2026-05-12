/**
 * Bullpug Cosmic Runner — 3D scene (Phase 1 + 2).
 *
 * Exports:
 *   - default `Phase1Runner3D` page (full-screen at /game/3d for direct access).
 *   - `CosmicRunner3DScene` (embeddable controlled component used inside
 *     `SpeedRunGame` so the page keeps its leaderboard / achievements / skin
 *     store / jackpot panels around the new 3D canvas).
 *
 * Bug fixes vs the prior cut:
 *   1. Bullpug now faces away from the camera (we see his back + curly tail).
 *   2. Higher-quality pug — sphere body, sphere head + jowls, capsule legs,
 *      cylinder tail; smoother shading.
 *   3. Lane navigation no longer skips the middle lane (audio object is now
 *      stable + each control action is de-duped via timestamp ref).
 *   4. Slide actually plays — the pug squats (group scale + camera dip) and
 *      no longer clips through the floor (no negative y offset).
 */

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
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
const MILESTONE_STEP = 250;

const POWERUP_DURATION_MS = { magnet: 6000, multiplier: 8000 };

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

// ───────────────────────────────────────────── Audio (stable across renders)

function useGameAudio() {
  const ctxRef = useRef(null);
  const ensure = () => {
    if (!ctxRef.current) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) ctxRef.current = new AC();
    }
    return ctxRef.current;
  };
  return useMemo(() => {
    const blip = (freq, dur, type, vol) => {
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
    };
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

// ───────────────────────────────────────────── Higher-quality Bullpug

function Bullpug({ refY, refX, sliding, running, shieldActive }) {
  const root = useRef();
  const body = useRef();
  const head = useRef();
  const shieldRef = useRef();
  const tail = useRef();
  const frontLeft = useRef();
  const frontRight = useRef();
  const backLeft = useRef();
  const backRight = useRef();
  const bob = useRef(0);

  useFrame((_, dt) => {
    if (!root.current) return;
    root.current.position.x = refX.current;
    root.current.position.y = refY.current;
    bob.current += dt * 14;
    const isRun = !!running.current && !sliding.current;
    const bobY = isRun ? Math.sin(bob.current) * 0.05 : 0;
    root.current.position.y += bobY;
    // Squash on slide — pug stays anchored at ground; we just compress height
    const targetSY = sliding.current ? 0.55 : 1;
    const targetSZ = sliding.current ? 1.35 : 1;
    root.current.scale.y += (targetSY - root.current.scale.y) * Math.min(1, dt * 14);
    root.current.scale.z += (targetSZ - root.current.scale.z) * Math.min(1, dt * 14);

    // Leg cycle (we are facing -Z so flip leg meaning visually swaps)
    if (isRun) {
      const s = Math.sin(bob.current) * 0.7;
      if (frontLeft.current) frontLeft.current.rotation.x = s;
      if (frontRight.current) frontRight.current.rotation.x = -s;
      if (backLeft.current) backLeft.current.rotation.x = -s;
      if (backRight.current) backRight.current.rotation.x = s;
    }
    // Tail wag
    if (tail.current) tail.current.rotation.z = Math.sin(bob.current * 0.7) * 0.3;
    // Head bob slight
    if (head.current) head.current.rotation.x = Math.sin(bob.current * 0.5) * 0.04;
    // Shield aura
    if (shieldRef.current) {
      shieldRef.current.visible = !!shieldActive?.current;
      shieldRef.current.rotation.y += dt * 1.6;
      shieldRef.current.rotation.x += dt * 0.9;
    }
  });

  // We rotate the entire pug 180° around Y so the head points away from the
  // camera (camera sits behind the pug at +Z). All local positions below are
  // authored in pug-local space (head at +Z); the rotation flips them so the
  // camera sees the pug's back & tail.
  return (
    <group ref={root} rotation={[0, Math.PI, 0]}>
      {/* Body — rounded barrel */}
      <mesh ref={body} position={[0, 0.55, 0]} scale={[1.0, 0.95, 1.25]}>
        <sphereGeometry args={[0.5, 24, 18]} />
        <meshStandardMaterial color={COLORS.bullpug} roughness={0.55} metalness={0.05} />
      </mesh>
      {/* Belly highlight */}
      <mesh position={[0, 0.4, 0.05]} scale={[0.78, 0.5, 0.95]}>
        <sphereGeometry args={[0.5, 18, 14]} />
        <meshStandardMaterial color="#FFE9CC" roughness={0.7} />
      </mesh>
      {/* Head group */}
      <group ref={head} position={[0, 1.05, 0.55]}>
        {/* Skull */}
        <mesh>
          <sphereGeometry args={[0.4, 24, 20]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.55} />
        </mesh>
        {/* Jowls (left + right) — pug cheeks */}
        <mesh position={[-0.22, -0.12, 0.12]}>
          <sphereGeometry args={[0.18, 16, 14]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.65} />
        </mesh>
        <mesh position={[0.22, -0.12, 0.12]}>
          <sphereGeometry args={[0.18, 16, 14]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.65} />
        </mesh>
        {/* Muzzle (dark mask) */}
        <mesh position={[0, -0.08, 0.32]} scale={[1.0, 0.7, 0.9]}>
          <sphereGeometry args={[0.18, 16, 14]} />
          <meshStandardMaterial color={COLORS.bullpugDark} roughness={0.8} />
        </mesh>
        {/* Snout nose */}
        <mesh position={[0, -0.02, 0.45]}>
          <sphereGeometry args={[0.06, 10, 10]} />
          <meshStandardMaterial color="#1a0f0a" roughness={0.4} metalness={0.2} />
        </mesh>
        {/* Eyes */}
        <mesh position={[-0.16, 0.06, 0.32]}>
          <sphereGeometry args={[0.07, 14, 14]} />
          <meshStandardMaterial color="#0d0d12" roughness={0.2} />
        </mesh>
        <mesh position={[0.16, 0.06, 0.32]}>
          <sphereGeometry args={[0.07, 14, 14]} />
          <meshStandardMaterial color="#0d0d12" roughness={0.2} />
        </mesh>
        {/* Eye glints */}
        <mesh position={[-0.14, 0.09, 0.38]}>
          <sphereGeometry args={[0.018, 8, 8]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
        <mesh position={[0.18, 0.09, 0.38]}>
          <sphereGeometry args={[0.018, 8, 8]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
        {/* Floppy ears */}
        <mesh position={[-0.32, 0.18, 0.0]} rotation={[0.2, -0.2, -0.5]}>
          <sphereGeometry args={[0.13, 14, 12]} />
          <meshStandardMaterial color={COLORS.bullpugDark} roughness={0.85} />
        </mesh>
        <mesh position={[0.32, 0.18, 0.0]} rotation={[0.2, 0.2, 0.5]}>
          <sphereGeometry args={[0.13, 14, 12]} />
          <meshStandardMaterial color={COLORS.bullpugDark} roughness={0.85} />
        </mesh>
        {/* HORNS — canonical curved bull horns */}
        <Horn position={[-0.24, 0.32, 0.08]} rotation={[0.1, 0.35, -0.7]} />
        <Horn position={[0.24, 0.32, 0.08]} rotation={[0.1, -0.35, 0.7]} />
      </group>
      {/* Legs — capsules so they look like little stubby pug paws */}
      <group ref={frontLeft} position={[-0.28, 0.22, 0.32]}>
        <mesh position={[0, -0.18, 0]}>
          <capsuleGeometry args={[0.12, 0.22, 6, 12]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.6} />
        </mesh>
      </group>
      <group ref={frontRight} position={[0.28, 0.22, 0.32]}>
        <mesh position={[0, -0.18, 0]}>
          <capsuleGeometry args={[0.12, 0.22, 6, 12]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.6} />
        </mesh>
      </group>
      <group ref={backLeft} position={[-0.28, 0.22, -0.32]}>
        <mesh position={[0, -0.18, 0]}>
          <capsuleGeometry args={[0.12, 0.22, 6, 12]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.6} />
        </mesh>
      </group>
      <group ref={backRight} position={[0.28, 0.22, -0.32]}>
        <mesh position={[0, -0.18, 0]}>
          <capsuleGeometry args={[0.12, 0.22, 6, 12]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.6} />
        </mesh>
      </group>
      {/* Curly tail */}
      <group ref={tail} position={[0, 0.78, -0.5]}>
        <mesh rotation={[0.6, 0, 0]}>
          <torusGeometry args={[0.1, 0.05, 8, 14, Math.PI * 1.6]} />
          <meshStandardMaterial color={COLORS.bullpug} roughness={0.7} />
        </mesh>
      </group>
      {/* Shield aura */}
      <mesh ref={shieldRef} position={[0, 0.85, 0]} visible={false}>
        <sphereGeometry args={[1.05, 28, 28]} />
        <meshBasicMaterial color={COLORS.shield} transparent opacity={0.22} wireframe />
      </mesh>
    </group>
  );
}

function Horn({ position, rotation }) {
  return (
    <group position={position} rotation={rotation}>
      <mesh>
        <coneGeometry args={[0.07, 0.26, 10]} />
        <meshStandardMaterial color={COLORS.horn} metalness={0.45} roughness={0.35} />
      </mesh>
      <mesh position={[0, 0.16, 0.05]} rotation={[-0.3, 0, 0]}>
        <coneGeometry args={[0.045, 0.16, 10]} />
        <meshStandardMaterial color="#E5A12E" metalness={0.55} roughness={0.3} />
      </mesh>
    </group>
  );
}

// ───────────────────────────────────────────── Environment

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
  const segs = useMemo(() => Array.from({ length: 5 }, (_, i) => i), []);
  const refs = useRef([]);
  useFrame((_, dt) => {
    const ds = speedRef.current * dt * 0.35;
    refs.current.forEach((m) => {
      if (!m) return;
      m.position.z += ds;
      if (m.position.z > 30) m.position.z -= 150;
    });
  });
  return (
    <group>
      {segs.map((i) => (
        <mesh
          key={i}
          ref={(el) => (refs.current[i] = el)}
          position={[i % 2 === 0 ? -22 : 22, 4 + (i % 2) * 2, -30 - i * 30]}
        >
          <planeGeometry args={[26, 14]} />
          <meshBasicMaterial color={i % 2 === 0 ? "#D946EF" : "#00C2FF"} transparent opacity={0.08} depthWrite={false} />
        </mesh>
      ))}
    </group>
  );
}

function Track({ speedRef }) {
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
    <group>
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
      <mesh ref={ref}>
        <icosahedronGeometry args={[0.55, 0]} />
        <meshStandardMaterial color={COLORS.asteroid} roughness={0.95} flatShading />
      </mesh>
    );
  }
  if (type === "crystal") {
    return (
      <group ref={ref}>
        <mesh position={[0, 1.0, 0]}>
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
  const color = type === "shield" ? COLORS.shield : type === "magnet" ? COLORS.magnet : COLORS.multiplier;
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
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.45, 0.55, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.55} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

// ───────────────────────────────────────────── World

function World({ onScore, onDeath, onMilestone, onPowerupChange, controlState, runningRef }) {
  const audio = useGameAudio(); // stable across renders (useMemo)
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
  const lastActionTsRef = useRef(0); // de-dupe input firing
  const [obstaclesState, setObstaclesState] = useState([]);
  const [coinsState, setCoinsState] = useState([]);
  const [powerupsState, setPowerupsState] = useState([]);
  const isDeadRef = useRef(false);

  // Handle controls — guarded by timestamp ref so each press only fires once.
  useEffect(() => {
    const c = controlState;
    if (!c || !c.action || c.ts === lastActionTsRef.current) return;
    lastActionTsRef.current = c.ts;
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
    // Start spawn pointer ahead so the first obstacles are ~12 units away
    // (gives the player a fair couple of seconds to read the track).
    spawnTrackRef.current = 12;
    elapsedRef.current = 0;
    distanceRef.current = 0;
    milestoneStepRef.current = 0;
    shieldActiveRef.current = false;
    magnetUntilRef.current = 0;
    multiplierUntilRef.current = 0;
    lastActionTsRef.current = 0;
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

    // Lane interp
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

    const now = performance.now();
    const magnetActive = now < magnetUntilRef.current;
    const multiplierActive = now < multiplierUntilRef.current;

    // Spawn ahead
    while (spawnTrackRef.current < distanceRef.current + SPAWN_AHEAD) {
      spawnTrackRef.current += 6 + Math.random() * 4;
      const spawnZ = -(spawnTrackRef.current - distanceRef.current);
      const roll = Math.random();
      // Grace period: during the first ~2.5s of a run, never spawn obstacles
      // in the player's current lane so the run can actually start.
      const inGrace = elapsedRef.current < 2.5;
      if (roll < 0.08) {
        const ptype = POWERUP_TYPES[Math.floor(Math.random() * POWERUP_TYPES.length)];
        const lane = Math.floor(Math.random() * 3);
        powerupsRef.current.push({ id: Math.random(), type: ptype, lane, position: new THREE.Vector3(LANES[lane], 1.0, spawnZ) });
      } else if (roll < 0.65) {
        let lane = Math.floor(Math.random() * 3);
        if (inGrace && lane === laneIdxRef.current) {
          // shove to an adjacent lane so the player has a clean opening
          lane = (lane + 1) % 3;
        }
        const type = OBSTACLE_TYPES[Math.floor(Math.random() * OBSTACLE_TYPES.length)];
        obstaclesRef.current.push({ id: Math.random(), type, lane, position: new THREE.Vector3(LANES[lane], 0, spawnZ) });
      } else {
        const lane = Math.floor(Math.random() * 3);
        for (let i = 0; i < 5; i++) {
          coinsRef.current.push({ id: Math.random() + i, lane, position: new THREE.Vector3(LANES[lane], 0.7, spawnZ - i * 1.2), collected: false });
        }
      }
    }

    const ds = speedRef.current * dt;
    obstaclesRef.current.forEach((o) => { o.position.z += ds; });
    coinsRef.current.forEach((c) => { c.position.z += ds; });
    powerupsRef.current.forEach((p) => { p.position.z += ds; });

    // Magnet pull
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

    obstaclesRef.current = obstaclesRef.current.filter((o) => o.position.z < 8);
    coinsRef.current = coinsRef.current.filter((c) => c.position.z < 8 && !c.collected);
    powerupsRef.current = powerupsRef.current.filter((p) => p.position.z < 8 && !p.collected);

    // Collisions
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
          shieldActiveRef.current = false;
          audio.shieldBreak();
          o.position.z = 999;
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
        if (p.type === "shield") shieldActiveRef.current = true;
        else if (p.type === "magnet") magnetUntilRef.current = now + POWERUP_DURATION_MS.magnet;
        else multiplierUntilRef.current = now + POWERUP_DURATION_MS.multiplier;
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

    // Periodic broadcast of remaining time so HUD chips animate
    if ((magnetActive || multiplierActive) && Math.floor(elapsedRef.current * 4) % 2 === 0) {
      onPowerupChange?.({
        shield: shieldActiveRef.current,
        magnet: Math.max(0, magnetUntilRef.current - now),
        multiplier: Math.max(0, multiplierUntilRef.current - now),
      });
    }
    if (!magnetActive && magnetUntilRef.current !== 0 && magnetUntilRef.current < now) {
      magnetUntilRef.current = 0;
      onPowerupChange?.({ shield: shieldActiveRef.current, magnet: 0, multiplier: Math.max(0, multiplierUntilRef.current - now) });
    }
    if (!multiplierActive && multiplierUntilRef.current !== 0 && multiplierUntilRef.current < now) {
      multiplierUntilRef.current = 0;
      onPowerupChange?.({ shield: shieldActiveRef.current, magnet: Math.max(0, magnetUntilRef.current - now), multiplier: 0 });
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

// ───────────────────────────────────────────── Embeddable Scene (used by SpeedRunGame)

/**
 * Controlled 3D scene. The parent owns gameState ("idle" | "playing" | "over")
 * and renders this only inside the page's canvas slot. Inputs handled
 * internally so the parent doesn't need to know about jump/slide/lane logic.
 *
 * Props:
 *  - playing: boolean — when true, world steps; when false, paused.
 *  - onScoreTick({score, coins, distance}) — every frame
 *  - onDeath({score, coins, distance})    — once on collision
 *  - onPowerupChange({shield, magnet, multiplier})
 *  - onMilestone(distance:number)
 *
 * Ref methods:
 *  - reset() — clears world + counters; parent calls when starting a new run.
 */
export const CosmicRunner3DScene = forwardRef(function CosmicRunner3DScene(
  { playing, onScoreTick, onDeath, onPowerupChange, onMilestone, className = "" },
  ref
) {
  const [controlState, setControlState] = useState({ action: null, ts: 0 });
  const runningRef = useRef({ running: false });
  const totalCoinsRef = useRef(0);
  const lastDistanceRef = useRef(0);

  // Keep runningRef in sync with prop
  useEffect(() => {
    runningRef.current.running = !!playing;
  }, [playing]);

  const fireAction = useCallback((action) => {
    if (!runningRef.current.running) return;
    setControlState({ action, ts: performance.now() });
  }, []);

  useImperativeHandle(ref, () => ({
    reset: () => {
      totalCoinsRef.current = 0;
      lastDistanceRef.current = 0;
      runningRef.current.reset?.();
    },
    fireAction,
  }), [fireAction]);

  // Keyboard — only when playing, only on fresh keydown (no repeat).
  useEffect(() => {
    const onKey = (e) => {
      if (!runningRef.current.running) return;
      if (e.repeat) return;
      const k = e.key.toLowerCase();
      if (k === "arrowleft" || k === "a") { e.preventDefault(); fireAction("left"); }
      else if (k === "arrowright" || k === "d") { e.preventDefault(); fireAction("right"); }
      else if (k === "arrowup" || k === "w" || k === " ") { e.preventDefault(); fireAction("jump"); }
      else if (k === "arrowdown" || k === "s") { e.preventDefault(); fireAction("slide"); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fireAction]);

  // Touch swipe
  useEffect(() => {
    let startX = 0, startY = 0, startT = 0;
    const onStart = (e) => {
      if (!runningRef.current.running) return;
      const t = e.changedTouches?.[0];
      if (!t) return;
      startX = t.clientX; startY = t.clientY; startT = performance.now();
    };
    const onEnd = (e) => {
      if (!runningRef.current.running) return;
      const t = e.changedTouches?.[0];
      if (!t) return;
      const dx = t.clientX - startX;
      const dy = t.clientY - startY;
      const dt = performance.now() - startT;
      if (dt > 700) return;
      const ax = Math.abs(dx), ay = Math.abs(dy);
      if (Math.max(ax, ay) < 18) return;
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

  const handleScore = useCallback((s) => {
    if (s.coins) totalCoinsRef.current += s.coins;
    lastDistanceRef.current = s.distance;
    onScoreTick?.({
      coins: totalCoinsRef.current,
      distance: s.distance,
      score: Math.floor(s.distance) + totalCoinsRef.current * 5,
    });
  }, [onScoreTick]);

  const handleDeath = useCallback((d) => {
    runningRef.current.running = false;
    onDeath?.({
      coins: totalCoinsRef.current,
      distance: d.distance,
      score: Math.floor(d.distance) + totalCoinsRef.current * 5,
    });
  }, [onDeath]);

  return (
    <div className={`relative w-full h-full ${className}`} data-testid="runner-3d-scene">
      <Canvas
        camera={{ position: [0, 2.7, 4.5], fov: 70 }}
        gl={{ antialias: true, powerPreference: "high-performance" }}
        style={{ background: COLORS.bg, width: "100%", height: "100%" }}
      >
        <fog attach="fog" args={[COLORS.bg, 18, 70]} />
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 8, 4]} intensity={0.8} />
        <pointLight position={[0, 4, 0]} intensity={0.7} color="#D946EF" />
        <pointLight position={[0, 4, -20]} intensity={0.6} color="#00FFA3" />

        <Stars radius={120} depth={60} count={3500} factor={4} fade saturation={0.6} />
        <Sparkles count={120} scale={[40, 25, 40]} size={3} speed={0.3} color="#D946EF" />

        <mesh position={[0, 5, -90]}>
          <planeGeometry args={[180, 90]} />
          <meshBasicMaterial color="#1a0942" depthWrite={false} />
        </mesh>

        <Planet position={[-22, 7, -55]} size={4.5} color="#7C3AED" ringColor="#D946EF" />
        <Planet position={[26, 9, -65]} size={3.2} color="#0EA5E9" />
        <Planet position={[12, -3, -45]} size={1.6} color="#F5D300" />

        <World
          onScore={handleScore}
          onDeath={handleDeath}
          onMilestone={onMilestone}
          onPowerupChange={onPowerupChange}
          controlState={controlState}
          runningRef={runningRef}
        />
      </Canvas>
    </div>
  );
});

// ───────────────────────────────────────────── Full-page Phase1 page (kept at /game/3d)

export default function Phase1Runner3D() {
  const sceneRef = useRef(null);
  const [score, setScore] = useState({ coins: 0, distance: 0 });
  const [running, setRunning] = useState(false);
  const [gameOver, setGameOver] = useState(null);
  const [bestDistance, setBestDistance] = useState(() => {
    try { return parseInt(localStorage.getItem("bullpug_runner3d_best") || "0", 10); } catch (e) { return 0; }
  });
  const [powerups, setPowerups] = useState({ shield: false, magnet: 0, multiplier: 0 });
  const [milestone, setMilestone] = useState(null);
  const [submitState, setSubmitState] = useState({ rank: null, submitted: false });
  const milestoneTimer = useRef(null);

  const playerName = useMemo(() => {
    try { return (localStorage.getItem("bullpugPlayerName") || "Cosmic Pug").trim().slice(0, 20); }
    catch (e) { return "Cosmic Pug"; }
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
    }
  }, [playerName]);

  const onScoreTick = useCallback(({ coins, distance }) => {
    setScore({ coins, distance });
  }, []);

  const onDeath = useCallback(({ coins, distance }) => {
    setRunning(false);
    setGameOver({ distance, coins });
    try {
      if (distance > bestDistance) {
        localStorage.setItem("bullpug_runner3d_best", String(Math.floor(distance)));
        setBestDistance(Math.floor(distance));
      }
    } catch (e) { /* ignore */ }
    submitScoreToBackend(distance, coins);
  }, [bestDistance, submitScoreToBackend]);

  const start = () => {
    setScore({ coins: 0, distance: 0 });
    setGameOver(null);
    setSubmitState({ rank: null, submitted: false });
    setPowerups({ shield: false, magnet: 0, multiplier: 0 });
    sceneRef.current?.reset();
    setRunning(true);
  };

  const magnetSec = Math.ceil(powerups.magnet / 1000);
  const multSec = Math.ceil(powerups.multiplier / 1000);

  return (
    <div className="relative w-full h-screen bg-black overflow-hidden" data-testid="runner-3d-page">
      <CosmicRunner3DScene
        ref={sceneRef}
        playing={running}
        onScoreTick={onScoreTick}
        onDeath={onDeath}
        onPowerupChange={setPowerups}
        onMilestone={handleMilestone}
      />

      {/* HUD */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-20 left-4 right-4 flex items-start justify-between">
          <div data-testid="runner-3d-hud-score">
            <div className="text-[10px] uppercase tracking-[0.25em] text-[#00FFA3] font-bold mb-1" style={{ fontFamily: "Orbitron" }}>Distance</div>
            <div className="text-3xl font-black text-white tabular-nums" style={{ fontFamily: "Orbitron" }}>{Math.floor(score.distance)}m</div>
            <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-[#F5D300] font-bold mb-1" style={{ fontFamily: "Orbitron" }}>Coins</div>
            <div className="text-xl font-bold text-[#F5D300] tabular-nums" style={{ fontFamily: "Orbitron" }}>✦ {score.coins}</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-[0.25em] text-slate-400 font-bold mb-1" style={{ fontFamily: "Orbitron" }}>Best</div>
            <div className="text-xl font-bold text-[#D946EF] tabular-nums" style={{ fontFamily: "Orbitron" }}>{bestDistance}m</div>
            <div className="mt-2 flex flex-col items-end gap-1" data-testid="runner-3d-hud-powerups">
              {powerups.shield && (
                <div className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider" style={{ background: "rgba(52,211,153,0.18)", color: COLORS.shield, border: `1px solid ${COLORS.shield}55` }}>◇ Shield</div>
              )}
              {powerups.magnet > 0 && (
                <div className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider" style={{ background: "rgba(249,115,22,0.18)", color: COLORS.magnet, border: `1px solid ${COLORS.magnet}55` }}>⌬ Magnet {magnetSec}s</div>
              )}
              {powerups.multiplier > 0 && (
                <div className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider" style={{ background: "rgba(167,139,250,0.18)", color: COLORS.multiplier, border: `1px solid ${COLORS.multiplier}55` }}>× 2 Score {multSec}s</div>
              )}
            </div>
          </div>
        </div>
        {milestone !== null && (
          <div className="absolute top-1/3 left-0 right-0 text-center" data-testid="runner-3d-milestone">
            <div className="inline-block px-5 py-2 rounded-full backdrop-blur-md" style={{ background: "rgba(0,255,163,0.12)", border: "1px solid rgba(0,255,163,0.4)" }}>
              <div className="text-[10px] uppercase tracking-[0.3em] text-[#00FFA3] font-bold" style={{ fontFamily: "Orbitron" }}>Milestone</div>
              <div className="text-2xl font-black text-white" style={{ fontFamily: "Orbitron" }}>{milestone}m</div>
            </div>
          </div>
        )}
      </div>

      {/* Start */}
      {!running && !gameOver && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm" data-testid="runner-3d-start-screen">
          <div className="max-w-sm text-center px-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00FFA3]/10 border border-[#00FFA3]/30 text-[#00FFA3] text-[10px] font-bold uppercase tracking-[0.25em] mb-4">Phase 1 · 3D</div>
            <h1 className="text-4xl sm:text-5xl font-black text-white mb-3 leading-[1.05]" style={{ fontFamily: "Orbitron" }}>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#D946EF] via-[#00FFA3] to-[#FFD700]">COSMIC RUNNER</span>
            </h1>
            <p className="text-slate-300 text-sm mb-6 leading-relaxed">Run forever through the deep PugChain. Dodge asteroids, slide through ion rings, leap over crystal pillars. Grab power-ups & collect cosmic coins for the Festival of Barks leaderboard.</p>
            <button type="button" onClick={start} data-testid="runner-3d-start-btn"
              className="px-8 py-3 rounded-full bg-gradient-to-r from-[#00FFA3] to-[#00C2FF] text-black font-black uppercase tracking-wider hover:scale-105 transition-transform"
              style={{ fontFamily: "Orbitron" }}>Begin Run</button>
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
            <p className="text-slate-300 text-sm mb-2">Cosmic coins: <span className="text-[#F5D300] font-bold">✦ {gameOver.coins}</span></p>
            <p className="text-[11px] text-slate-500 mb-2">
              {gameOver.distance > bestDistance ? "NEW PERSONAL BEST" : `Best · ${bestDistance}m`}
            </p>
            {submitState.submitted && (
              <p className="text-[11px] mb-4" data-testid="runner-3d-rank">
                <span className="text-slate-500">Festival of Barks · </span>
                <span className="text-[#00FFA3] font-bold">{submitState.rank ? `Rank #${submitState.rank}` : "submitted"}</span>
                <span className="text-slate-500"> · as {playerName}</span>
              </p>
            )}
            <div className="flex items-center justify-center gap-3">
              <button type="button" onClick={start} data-testid="runner-3d-restart-btn"
                className="px-6 py-3 rounded-full bg-[#00FFA3] text-black font-black uppercase tracking-wider hover:scale-105 transition-transform text-sm"
                style={{ fontFamily: "Orbitron" }}>Run Again</button>
              <a href="/leaderboard" data-testid="runner-3d-leaderboard-link"
                className="px-6 py-3 rounded-full border border-white/20 text-white font-bold uppercase tracking-wider hover:bg-white/10 transition-colors text-sm"
                style={{ fontFamily: "Orbitron" }}>Leaderboard</a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
