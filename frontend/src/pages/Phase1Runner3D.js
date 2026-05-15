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

// Cap DPR so high-density retina displays stay smooth. 1.6 is a good balance
// between razor-sharp edges and consistent 60fps on mid-tier laptops.
const DPR_CAP = [1, 1.6];

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
  moonCheese: "#FFD86B",
  moonCheeseRim: "#E0A642",
  meteorRock: "#5b6878",
  meteorHot: "#FF7A2A",
  debris: "#7c8ba0",
  ring: "#00C2FF",
  shield: "#34D399",
  magnet: "#F97316",
  multiplier: "#A78BFA",
};

// ───────────────────────────────────────────── Skin → 3D material map

/** All visual presets for the pug body driven by SkinStore IDs. */
const SKIN_VISUALS = {
  default: { body: "#F0DCC4", belly: "#FFE9CC", dark: "#3A2718", metalness: 0.05, roughness: 0.6, emissive: "#000000", emissiveIntensity: 0, extra: null },
  ethereal: { body: "#E8D5FF", belly: "#FFFFFF", dark: "#6F4FB1", metalness: 0.25, roughness: 0.35, emissive: "#C084FC", emissiveIntensity: 0.45, extra: "halo" },
  diamond:  { body: "#BDF2FF", belly: "#FFFFFF", dark: "#0C7FA8", metalness: 0.95, roughness: 0.05, emissive: "#00FFFF", emissiveIntensity: 0.35, extra: "shine" },
  gold:     { body: "#FFD700", belly: "#FFE990", dark: "#8A6300", metalness: 0.95, roughness: 0.15, emissive: "#FFB300", emissiveIntensity: 0.25, extra: "shine" },
  silver:   { body: "#D9D9D9", belly: "#F5F5F5", dark: "#4A4A4A", metalness: 0.9,  roughness: 0.18, emissive: "#9CA3AF", emissiveIntensity: 0.15, extra: null },
  heatmap:  { body: "#FF6B35", belly: "#FFB179", dark: "#7A1F00", metalness: 0.4,  roughness: 0.4,  emissive: "#FF4A00", emissiveIntensity: 0.55, extra: null },
  radioactive: { body: "#7FFF00", belly: "#C7FF85", dark: "#1F4D00", metalness: 0.25, roughness: 0.35, emissive: "#7FFF00", emissiveIntensity: 0.7, extra: "sparkle" },
  zombie:   { body: "#7E8F4A", belly: "#A8B677", dark: "#2C3315", metalness: 0.05, roughness: 0.85, emissive: "#A0FF6E", emissiveIntensity: 0.18, extra: "stitches" },
  water:    { body: "#7DE3E8", belly: "#C2F7F9", dark: "#0E5B6B", metalness: 0.55, roughness: 0.2,  emissive: "#00CED1", emissiveIntensity: 0.3, extra: null },
  fire:     { body: "#FF5520", belly: "#FFB279", dark: "#6A1500", metalness: 0.3,  roughness: 0.4,  emissive: "#FF2A00", emissiveIntensity: 0.75, extra: "sparkle" },
  robot:    { body: "#B87333", belly: "#D89757", dark: "#3A2008", metalness: 0.95, roughness: 0.25, emissive: "#FF8B2A", emissiveIntensity: 0.25, extra: "robot" },
  skeletal: { body: "#EFEAD8", belly: "#FFFFFF", dark: "#22222B", metalness: 0.15, roughness: 0.55, emissive: "#A0E8FF", emissiveIntensity: 0.25, extra: "bones" },
};
const getSkinVisuals = (id) => SKIN_VISUALS[id] || SKIN_VISUALS.default;

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

// ───────────────────────────────────────────── Higher-quality Bullpug (skinnable)

/** A full skeletal bullpug — skull with horns, ribcage, spine, leg bones,
 * curly tail vertebrae. Used when skinId === 'skeletal' so the in-game model
 * matches the 2D PHANTOM skin cutout (full skeleton, not a bone-white pug). */
function SkeletonBody({ frontLeft, frontRight, backLeft, backRight, tail, head }) {
  const bone = "#F0EAD2";          // aged ivory
  const boneDark = "#A89A6F";      // shadowed bone
  const eyeGlow = "#A0E8FF";       // phantom eye glow
  return (
    <>
      {/* SKULL */}
      <group ref={head} position={[0, 1.05, 0.55]}>
        {/* Cranium */}
        <mesh>
          <sphereGeometry args={[0.34, 26, 22]} />
          <meshStandardMaterial color={bone} roughness={0.6} metalness={0.1} />
        </mesh>
        {/* Brow ridge */}
        <mesh position={[0, 0.18, 0.22]} scale={[1.0, 0.35, 0.7]}>
          <sphereGeometry args={[0.3, 18, 14]} />
          <meshStandardMaterial color={boneDark} roughness={0.65} />
        </mesh>
        {/* Eye sockets (dark hollows with phantom glow inside) */}
        <mesh position={[-0.14, 0.04, 0.28]} scale={[1, 1, 0.4]}>
          <sphereGeometry args={[0.09, 14, 12]} />
          <meshBasicMaterial color="#0a0a14" />
        </mesh>
        <mesh position={[0.14, 0.04, 0.28]} scale={[1, 1, 0.4]}>
          <sphereGeometry args={[0.09, 14, 12]} />
          <meshBasicMaterial color="#0a0a14" />
        </mesh>
        <mesh position={[-0.14, 0.04, 0.25]}>
          <sphereGeometry args={[0.04, 10, 10]} />
          <meshBasicMaterial color={eyeGlow} />
        </mesh>
        <mesh position={[0.14, 0.04, 0.25]}>
          <sphereGeometry args={[0.04, 10, 10]} />
          <meshBasicMaterial color={eyeGlow} />
        </mesh>
        {/* Nasal cavity */}
        <mesh position={[0, -0.06, 0.32]} scale={[1, 1, 0.3]}>
          <sphereGeometry args={[0.05, 10, 10]} />
          <meshBasicMaterial color="#0a0a14" />
        </mesh>
        {/* Snout / upper jaw */}
        <mesh position={[0, -0.12, 0.32]} scale={[1.0, 0.55, 0.95]}>
          <sphereGeometry args={[0.18, 16, 14]} />
          <meshStandardMaterial color={bone} roughness={0.65} />
        </mesh>
        {/* Lower jaw (slightly offset) */}
        <mesh position={[0, -0.22, 0.28]} scale={[0.95, 0.35, 0.85]}>
          <sphereGeometry args={[0.18, 16, 14]} />
          <meshStandardMaterial color={boneDark} roughness={0.7} />
        </mesh>
        {/* Teeth — small white rectangles between upper and lower jaws */}
        {[-0.08, -0.025, 0.025, 0.08].map((x, i) => (
          <mesh key={i} position={[x, -0.18, 0.46]}>
            <boxGeometry args={[0.025, 0.04, 0.02]} />
            <meshStandardMaterial color="#FFFFFF" roughness={0.4} />
          </mesh>
        ))}
        {/* Skeleton ears — bony stubs, not floppy */}
        <mesh position={[-0.3, 0.18, 0.0]} rotation={[0.2, -0.2, -0.5]} scale={[0.6, 0.9, 0.5]}>
          <coneGeometry args={[0.08, 0.2, 6]} />
          <meshStandardMaterial color={boneDark} roughness={0.85} />
        </mesh>
        <mesh position={[0.3, 0.18, 0.0]} rotation={[0.2, 0.2, 0.5]} scale={[0.6, 0.9, 0.5]}>
          <coneGeometry args={[0.08, 0.2, 6]} />
          <meshStandardMaterial color={boneDark} roughness={0.85} />
        </mesh>
        {/* Horns */}
        <Horn position={[-0.24, 0.32, 0.08]} rotation={[0.1, 0.35, -0.7]} />
        <Horn position={[0.24, 0.32, 0.08]} rotation={[0.1, -0.35, 0.7]} />
      </group>

      {/* SPINE — chain of vertebrae from skull to tail */}
      {Array.from({ length: 7 }).map((_, i) => {
        const z = 0.36 - i * 0.13;
        return (
          <mesh key={`v${i}`} position={[0, 0.75, z]}>
            <sphereGeometry args={[0.07, 12, 12]} />
            <meshStandardMaterial color={bone} roughness={0.55} />
          </mesh>
        );
      })}

      {/* RIBCAGE — 5 curved rib arcs hanging off the spine */}
      {[0.28, 0.18, 0.05, -0.08, -0.21].map((z, i) => (
        <mesh key={`r${i}`} position={[0, 0.55, z]} rotation={[0, 0, Math.PI / 2]}>
          <torusGeometry args={[0.32, 0.038, 8, 18, Math.PI * 1.15]} />
          <meshStandardMaterial color={bone} roughness={0.55} />
        </mesh>
      ))}

      {/* STERNUM */}
      <mesh position={[0, 0.42, 0.05]} scale={[0.18, 0.06, 0.7]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={boneDark} roughness={0.6} />
      </mesh>

      {/* SHOULDER & PELVIS — bony plates */}
      <mesh position={[0, 0.78, 0.38]}>
        <sphereGeometry args={[0.18, 14, 12]} />
        <meshStandardMaterial color={boneDark} roughness={0.55} />
      </mesh>
      <mesh position={[0, 0.78, -0.38]}>
        <sphereGeometry args={[0.2, 14, 12]} />
        <meshStandardMaterial color={boneDark} roughness={0.55} />
      </mesh>

      {/* LEG BONES — 2 cylinders per leg with a joint ball, refs preserved for run-cycle */}
      <group ref={frontLeft} position={[-0.28, 0.38, 0.36]}>
        {/* hip joint */}
        <mesh><sphereGeometry args={[0.08, 10, 10]} /><meshStandardMaterial color={boneDark} /></mesh>
        {/* upper bone */}
        <mesh position={[0, -0.12, 0]}><cylinderGeometry args={[0.04, 0.045, 0.22, 8]} /><meshStandardMaterial color={bone} /></mesh>
        {/* knee */}
        <mesh position={[0, -0.24, 0]}><sphereGeometry args={[0.055, 10, 10]} /><meshStandardMaterial color={boneDark} /></mesh>
        {/* lower bone */}
        <mesh position={[0, -0.36, 0]}><cylinderGeometry args={[0.035, 0.04, 0.2, 8]} /><meshStandardMaterial color={bone} /></mesh>
        {/* paw */}
        <mesh position={[0, -0.49, 0.04]} scale={[1, 0.6, 1.2]}><sphereGeometry args={[0.07, 10, 10]} /><meshStandardMaterial color={bone} /></mesh>
      </group>
      <group ref={frontRight} position={[0.28, 0.38, 0.36]}>
        <mesh><sphereGeometry args={[0.08, 10, 10]} /><meshStandardMaterial color={boneDark} /></mesh>
        <mesh position={[0, -0.12, 0]}><cylinderGeometry args={[0.04, 0.045, 0.22, 8]} /><meshStandardMaterial color={bone} /></mesh>
        <mesh position={[0, -0.24, 0]}><sphereGeometry args={[0.055, 10, 10]} /><meshStandardMaterial color={boneDark} /></mesh>
        <mesh position={[0, -0.36, 0]}><cylinderGeometry args={[0.035, 0.04, 0.2, 8]} /><meshStandardMaterial color={bone} /></mesh>
        <mesh position={[0, -0.49, 0.04]} scale={[1, 0.6, 1.2]}><sphereGeometry args={[0.07, 10, 10]} /><meshStandardMaterial color={bone} /></mesh>
      </group>
      <group ref={backLeft} position={[-0.28, 0.38, -0.36]}>
        <mesh><sphereGeometry args={[0.08, 10, 10]} /><meshStandardMaterial color={boneDark} /></mesh>
        <mesh position={[0, -0.12, 0]}><cylinderGeometry args={[0.04, 0.045, 0.22, 8]} /><meshStandardMaterial color={bone} /></mesh>
        <mesh position={[0, -0.24, 0]}><sphereGeometry args={[0.055, 10, 10]} /><meshStandardMaterial color={boneDark} /></mesh>
        <mesh position={[0, -0.36, 0]}><cylinderGeometry args={[0.035, 0.04, 0.2, 8]} /><meshStandardMaterial color={bone} /></mesh>
        <mesh position={[0, -0.49, -0.04]} scale={[1, 0.6, 1.2]}><sphereGeometry args={[0.07, 10, 10]} /><meshStandardMaterial color={bone} /></mesh>
      </group>
      <group ref={backRight} position={[0.28, 0.38, -0.36]}>
        <mesh><sphereGeometry args={[0.08, 10, 10]} /><meshStandardMaterial color={boneDark} /></mesh>
        <mesh position={[0, -0.12, 0]}><cylinderGeometry args={[0.04, 0.045, 0.22, 8]} /><meshStandardMaterial color={bone} /></mesh>
        <mesh position={[0, -0.24, 0]}><sphereGeometry args={[0.055, 10, 10]} /><meshStandardMaterial color={boneDark} /></mesh>
        <mesh position={[0, -0.36, 0]}><cylinderGeometry args={[0.035, 0.04, 0.2, 8]} /><meshStandardMaterial color={bone} /></mesh>
        <mesh position={[0, -0.49, -0.04]} scale={[1, 0.6, 1.2]}><sphereGeometry args={[0.07, 10, 10]} /><meshStandardMaterial color={bone} /></mesh>
      </group>

      {/* CURLY TAIL — chain of small vertebrae spheres on a wagging group */}
      <group ref={tail} position={[0, 0.78, -0.55]}>
        {[
          { p: [0, 0, 0], s: 0.07 },
          { p: [0.04, 0.04, -0.06], s: 0.065 },
          { p: [0.1, 0.06, -0.08], s: 0.06 },
          { p: [0.14, 0.04, -0.04], s: 0.055 },
          { p: [0.12, -0.02, 0.02], s: 0.05 },
        ].map((v, i) => (
          <mesh key={i} position={v.p}>
            <sphereGeometry args={[v.s, 10, 10]} />
            <meshStandardMaterial color={bone} roughness={0.55} />
          </mesh>
        ))}
      </group>

      {/* Phantom aura — faint cool-blue glow around skeleton */}
      <pointLight position={[0, 0.7, 0]} intensity={0.4} color={eyeGlow} distance={2.4} />
    </>
  );
}

function Bullpug({ refY, refX, sliding, running, shieldActive, skinId = "default" }) {
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
  const sk = useMemo(() => getSkinVisuals(skinId), [skinId]);

  useFrame((_, dt) => {
    if (!root.current) return;
    root.current.position.x = refX.current;
    root.current.position.y = refY.current;
    bob.current += dt * 14;
    const isRun = !!running.current && !sliding.current;
    const bobY = isRun ? Math.sin(bob.current) * 0.05 : 0;
    root.current.position.y += bobY;
    const targetSY = sliding.current ? 0.55 : 1;
    const targetSZ = sliding.current ? 1.35 : 1;
    root.current.scale.y += (targetSY - root.current.scale.y) * Math.min(1, dt * 14);
    root.current.scale.z += (targetSZ - root.current.scale.z) * Math.min(1, dt * 14);
    if (isRun) {
      const s = Math.sin(bob.current) * 0.7;
      if (frontLeft.current) frontLeft.current.rotation.x = s;
      if (frontRight.current) frontRight.current.rotation.x = -s;
      if (backLeft.current) backLeft.current.rotation.x = -s;
      if (backRight.current) backRight.current.rotation.x = s;
    }
    if (tail.current) tail.current.rotation.z = Math.sin(bob.current * 0.7) * 0.3;
    if (head.current) head.current.rotation.x = Math.sin(bob.current * 0.5) * 0.04;
    if (shieldRef.current) {
      shieldRef.current.visible = !!shieldActive?.current;
      shieldRef.current.rotation.y += dt * 1.6;
      shieldRef.current.rotation.x += dt * 0.9;
    }
  });

  // Shared body material spec from the skin lookup.
  const bodyMat = (
    <meshStandardMaterial
      color={sk.body}
      emissive={sk.emissive}
      emissiveIntensity={sk.emissiveIntensity}
      metalness={sk.metalness}
      roughness={sk.roughness}
    />
  );

  return (
    <group ref={root} rotation={[0, Math.PI, 0]}>
      {skinId === "skeletal" ? (
        <SkeletonBody
          frontLeft={frontLeft}
          frontRight={frontRight}
          backLeft={backLeft}
          backRight={backRight}
          tail={tail}
          head={head}
        />
      ) : (
      <>
      {/* Body — rounded barrel */}
      <mesh ref={body} position={[0, 0.55, 0]} scale={[1.0, 0.95, 1.25]}>
        <sphereGeometry args={[0.5, 28, 22]} />
        {bodyMat}
      </mesh>
      {/* Belly highlight */}
      <mesh position={[0, 0.4, 0.05]} scale={[0.78, 0.5, 0.95]}>
        <sphereGeometry args={[0.5, 20, 16]} />
        <meshStandardMaterial color={sk.belly} roughness={Math.max(0.4, sk.roughness)} metalness={sk.metalness * 0.4} />
      </mesh>
      {/* Head group */}
      <group ref={head} position={[0, 1.05, 0.55]}>
        <mesh>
          <sphereGeometry args={[0.4, 28, 24]} />
          {bodyMat}
        </mesh>
        <mesh position={[-0.22, -0.12, 0.12]}>
          <sphereGeometry args={[0.18, 18, 16]} />
          {bodyMat}
        </mesh>
        <mesh position={[0.22, -0.12, 0.12]}>
          <sphereGeometry args={[0.18, 18, 16]} />
          {bodyMat}
        </mesh>
        {/* Muzzle */}
        <mesh position={[0, -0.08, 0.32]} scale={[1.0, 0.7, 0.9]}>
          <sphereGeometry args={[0.18, 16, 14]} />
          <meshStandardMaterial color={sk.dark} roughness={0.8} metalness={sk.metalness * 0.3} />
        </mesh>
        <mesh position={[0, -0.02, 0.45]}>
          <sphereGeometry args={[0.06, 12, 12]} />
          <meshStandardMaterial color="#0a0506" roughness={0.4} metalness={0.2} />
        </mesh>
        {/* Eyes — glow for emissive skins */}
        <mesh position={[-0.16, 0.06, 0.32]}>
          <sphereGeometry args={[0.07, 14, 14]} />
          <meshStandardMaterial color="#0d0d12" emissive={sk.emissive} emissiveIntensity={Math.min(0.8, sk.emissiveIntensity * 0.6)} roughness={0.2} />
        </mesh>
        <mesh position={[0.16, 0.06, 0.32]}>
          <sphereGeometry args={[0.07, 14, 14]} />
          <meshStandardMaterial color="#0d0d12" emissive={sk.emissive} emissiveIntensity={Math.min(0.8, sk.emissiveIntensity * 0.6)} roughness={0.2} />
        </mesh>
        <mesh position={[-0.14, 0.09, 0.38]}>
          <sphereGeometry args={[0.018, 8, 8]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
        <mesh position={[0.18, 0.09, 0.38]}>
          <sphereGeometry args={[0.018, 8, 8]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
        {/* Ears */}
        <mesh position={[-0.32, 0.18, 0.0]} rotation={[0.2, -0.2, -0.5]}>
          <sphereGeometry args={[0.13, 16, 14]} />
          <meshStandardMaterial color={sk.dark} roughness={0.85} />
        </mesh>
        <mesh position={[0.32, 0.18, 0.0]} rotation={[0.2, 0.2, 0.5]}>
          <sphereGeometry args={[0.13, 16, 14]} />
          <meshStandardMaterial color={sk.dark} roughness={0.85} />
        </mesh>
        {/* HORNS */}
        <Horn position={[-0.24, 0.32, 0.08]} rotation={[0.1, 0.35, -0.7]} />
        <Horn position={[0.24, 0.32, 0.08]} rotation={[0.1, -0.35, 0.7]} />
        {/* Skeletal overlay — visible rib hint when skin is skeletal */}
        {sk.extra === "bones" && (
          <>
            <mesh position={[0, -0.32, 0.18]} scale={[1, 0.18, 0.1]}>
              <sphereGeometry args={[0.18, 12, 8]} />
              <meshBasicMaterial color="#0d0d12" />
            </mesh>
          </>
        )}
        {/* Robot antenna */}
        {sk.extra === "robot" && (
          <mesh position={[0, 0.45, 0]}>
            <cylinderGeometry args={[0.015, 0.02, 0.32, 8]} />
            <meshStandardMaterial color="#9CA3AF" metalness={0.9} roughness={0.2} />
          </mesh>
        )}
      </group>
      {/* Legs */}
      <group ref={frontLeft} position={[-0.28, 0.22, 0.32]}>
        <mesh position={[0, -0.18, 0]}>
          <capsuleGeometry args={[0.12, 0.22, 8, 14]} />
          {bodyMat}
        </mesh>
      </group>
      <group ref={frontRight} position={[0.28, 0.22, 0.32]}>
        <mesh position={[0, -0.18, 0]}>
          <capsuleGeometry args={[0.12, 0.22, 8, 14]} />
          {bodyMat}
        </mesh>
      </group>
      <group ref={backLeft} position={[-0.28, 0.22, -0.32]}>
        <mesh position={[0, -0.18, 0]}>
          <capsuleGeometry args={[0.12, 0.22, 8, 14]} />
          {bodyMat}
        </mesh>
      </group>
      <group ref={backRight} position={[0.28, 0.22, -0.32]}>
        <mesh position={[0, -0.18, 0]}>
          <capsuleGeometry args={[0.12, 0.22, 8, 14]} />
          {bodyMat}
        </mesh>
      </group>
      {/* Curly tail */}
      <group ref={tail} position={[0, 0.78, -0.5]}>
        <mesh rotation={[0.6, 0, 0]}>
          <torusGeometry args={[0.1, 0.05, 8, 18, Math.PI * 1.6]} />
          {bodyMat}
        </mesh>
      </group>
      </>
      )}
      {/* Per-skin extras */}
      {sk.extra === "sparkle" && (
        <Sparkles count={26} scale={[1.4, 1.6, 1.4]} size={2.5} speed={0.5} color={sk.emissive} />
      )}
      {sk.extra === "halo" && (
        <mesh position={[0, 1.55, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.32, 0.035, 8, 28]} />
          <meshStandardMaterial color={sk.emissive} emissive={sk.emissive} emissiveIntensity={1.2} />
        </mesh>
      )}
      {/* Shield aura */}
      <mesh ref={shieldRef} position={[0, 0.85, 0]} visible={false}>
        <sphereGeometry args={[1.08, 28, 28]} />
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
          <meshStandardMaterial color={i % 2 === 0 ? COLORS.trackA : COLORS.trackB} roughness={0.55} metalness={0.1} />
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

// ───────────────────────────────────────────── Obstacles / Moon Cheese / Power-ups

/**
 * 5 obstacle types from the 2D legend.
 *  - y: world height the group spawns at (keeps the model off the ground).
 *  - hz: half collision window in Z. Tight per-type so a fast pug doesn't get
 *    "killed" 1.5 metres before the obstacle.
 *  - clear(py, sliding): returns true if the player has dodged it vertically
 *    (jump for ground obstacles, slide for flyers).
 *  - minStage: distance-gated unlock (stage = floor(distance/150)+1, capped 5).
 */
const OBSTACLE_DEFS = {
  meteor:     { y: 0.55, hz: 0.45, minStage: 1, clear: (py) => py >= 0.85 },
  debris:     { y: 0.95, hz: 0.55, minStage: 2, clear: (py) => py >= 1.40 },
  black_hole: { y: 0.06, hz: 0.40, minStage: 3, clear: (py) => py >= 0.50 },
  satellite:  { y: 1.65, hz: 0.50, minStage: 4, clear: (_py, sliding) => !!sliding },
  alien_ship: { y: 2.00, hz: 0.70, minStage: 5, clear: (_py, sliding) => !!sliding },
};
const POWERUP_TYPES = ["shield", "magnet", "multiplier"];

function Obstacle({ type, refData }) {
  const ref = useRef();
  const halo = useRef();
  const beam = useRef();
  useFrame((_, dt) => {
    if (ref.current) {
      ref.current.position.copy(refData.position);
      // Subtle spin keeps shapes interesting without disturbing the hitbox.
      ref.current.rotation.y += dt * 0.6;
    }
    if (halo.current) halo.current.rotation.z += dt * 1.6;
    if (beam.current) beam.current.material.opacity = 0.18 + Math.abs(Math.sin(performance.now() * 0.004)) * 0.18;
  });

  if (type === "meteor") {
    // Fiery comet — bright rock with hot wireframe + trailing flame tail.
    return (
      <group ref={ref}>
        <mesh>
          <icosahedronGeometry args={[0.4, 1]} />
          <meshStandardMaterial color="#FFB179" emissive="#FF4500" emissiveIntensity={0.7} roughness={0.55} flatShading metalness={0.2} />
        </mesh>
        {/* Hot lava cracks */}
        <mesh scale={[1.01, 1.01, 1.01]}>
          <icosahedronGeometry args={[0.4, 0]} />
          <meshBasicMaterial color="#FFE0A0" transparent opacity={0.8} wireframe />
        </mesh>
        {/* Comet tail — three nested cones streaking back */}
        <mesh position={[0, 0, -0.45]} rotation={[Math.PI / 2, 0, 0]}>
          <coneGeometry args={[0.32, 0.9, 16, 1, true]} />
          <meshBasicMaterial color="#FF4500" transparent opacity={0.65} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
        <mesh position={[0, 0, -0.75]} rotation={[Math.PI / 2, 0, 0]}>
          <coneGeometry args={[0.22, 1.4, 16, 1, true]} />
          <meshBasicMaterial color="#FFB179" transparent opacity={0.5} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
        <mesh position={[0, 0, -1.05]} rotation={[Math.PI / 2, 0, 0]}>
          <coneGeometry args={[0.1, 1.8, 12, 1, true]} />
          <meshBasicMaterial color="#FFE0A0" transparent opacity={0.4} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
        {/* Heat halo */}
        <mesh ref={halo} rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.55, 0.78, 32]} />
          <meshBasicMaterial color="#FF7A2A" side={THREE.DoubleSide} transparent opacity={0.55} depthWrite={false} />
        </mesh>
        <pointLight intensity={1.1} color="#FF7A2A" distance={4} />
      </group>
    );
  }

  if (type === "debris") {
    // Floating wreckage — single faceted angular rock (matches the white
    // crystal icon in the in-game legend). Tall enough that low jumps won't
    // clear it.
    return (
      <group ref={ref}>
        <mesh rotation={[0.35, 0.4, 0.1]}>
          <dodecahedronGeometry args={[0.55, 0]} />
          <meshStandardMaterial color="#E3E8F0" emissive="#9FB1C7" emissiveIntensity={0.45} metalness={0.35} roughness={0.35} flatShading />
        </mesh>
        {/* Inner facet — slightly off-axis chunk so silhouette is asymmetric */}
        <mesh position={[0.12, 0.08, -0.05]} rotation={[0.6, -0.3, 0.4]} scale={[0.55, 0.55, 0.55]}>
          <octahedronGeometry args={[0.55, 0]} />
          <meshStandardMaterial color="#FFFFFF" emissive="#C7D8FF" emissiveIntensity={0.5} metalness={0.4} roughness={0.25} flatShading />
        </mesh>
        {/* Halo */}
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.7, 0.92, 32]} />
          <meshBasicMaterial color="#C7D8FF" side={THREE.DoubleSide} transparent opacity={0.45} depthWrite={false} />
        </mesh>
        <pointLight intensity={0.9} color="#C7D8FF" distance={3.5} />
      </group>
    );
  }

  if (type === "black_hole") {
    // Dangerous gravity well — flat dark ellipse with a purple accretion ring.
    return (
      <group ref={ref} rotation={[-Math.PI / 2.2, 0, 0]}>
        {/* Void center */}
        <mesh>
          <circleGeometry args={[0.55, 36]} />
          <meshBasicMaterial color="#0a0014" />
        </mesh>
        {/* Inner deep purple glow */}
        <mesh position={[0, 0, 0.01]}>
          <ringGeometry args={[0.55, 0.62, 36]} />
          <meshBasicMaterial color="#4C1D95" transparent opacity={0.95} side={THREE.DoubleSide} />
        </mesh>
        {/* Accretion ring (rotating) */}
        <mesh ref={halo} position={[0, 0, 0.02]}>
          <ringGeometry args={[0.6, 0.95, 48]} />
          <meshBasicMaterial color="#D946EF" transparent opacity={0.55} side={THREE.DoubleSide} />
        </mesh>
        {/* Outer faint halo */}
        <mesh position={[0, 0, 0.015]}>
          <ringGeometry args={[0.95, 1.15, 48]} />
          <meshBasicMaterial color="#7C3AED" transparent opacity={0.25} side={THREE.DoubleSide} />
        </mesh>
        <pointLight intensity={0.7} color="#D946EF" distance={4} />
      </group>
    );
  }

  if (type === "satellite") {
    // Flying communications satellite — central box body + two flat solar
    // panel wings + dish antenna. Pug slides underneath.
    return (
      <group ref={ref}>
        {/* Main body */}
        <mesh>
          <boxGeometry args={[0.32, 0.32, 0.5]} />
          <meshStandardMaterial color="#D6D8E0" metalness={0.7} roughness={0.3} />
        </mesh>
        {/* Solar panels (left + right) */}
        <mesh position={[-0.55, 0, 0]} rotation={[0, 0, 0]}>
          <boxGeometry args={[0.7, 0.02, 0.35]} />
          <meshStandardMaterial color="#5B4FE6" emissive="#A78BFA" emissiveIntensity={0.7} metalness={0.55} roughness={0.25} />
        </mesh>
        <mesh position={[0.55, 0, 0]}>
          <boxGeometry args={[0.7, 0.02, 0.35]} />
          <meshStandardMaterial color="#5B4FE6" emissive="#A78BFA" emissiveIntensity={0.7} metalness={0.55} roughness={0.25} />
        </mesh>
        {/* Panel grid lines */}
        <mesh position={[-0.55, 0.012, 0]}>
          <boxGeometry args={[0.7, 0.005, 0.02]} />
          <meshBasicMaterial color="#FFFFFF" />
        </mesh>
        <mesh position={[0.55, 0.012, 0]}>
          <boxGeometry args={[0.7, 0.005, 0.02]} />
          <meshBasicMaterial color="#FFFFFF" />
        </mesh>
        {/* Dish antenna */}
        <mesh position={[0, 0.22, 0]} rotation={[Math.PI, 0, 0]}>
          <coneGeometry args={[0.12, 0.18, 16, 1, true]} />
          <meshStandardMaterial color="#FFFFFF" metalness={0.8} roughness={0.25} side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0, 0.12, 0]}>
          <cylinderGeometry args={[0.015, 0.015, 0.12, 6]} />
          <meshStandardMaterial color="#9CA3AF" metalness={0.9} roughness={0.2} />
        </mesh>
        {/* Status blinker */}
        <mesh position={[0, 0, 0.27]}>
          <sphereGeometry args={[0.035, 10, 10]} />
          <meshBasicMaterial color="#EF4444" />
        </mesh>
        {/* Soft glow halo so it reads against dark space */}
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.95, 1.15, 32]} />
          <meshBasicMaterial color="#A78BFA" transparent opacity={0.3} side={THREE.DoubleSide} depthWrite={false} />
        </mesh>
        <pointLight intensity={0.6} color="#A78BFA" distance={3} />
      </group>
    );
  }

  // alien_ship — UFO disc with translucent dome + downward tractor beam
  return (
    <group ref={ref}>
      {/* Saucer body — squashed cylinder */}
      <mesh scale={[1.0, 0.25, 1.0]}>
        <sphereGeometry args={[0.55, 24, 16]} />
        <meshStandardMaterial color="#C7D0DE" metalness={0.85} roughness={0.2} />
      </mesh>
      {/* Lower lights ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, -0.06, 0]}>
        <torusGeometry args={[0.42, 0.04, 8, 32]} />
        <meshBasicMaterial color="#34D399" />
      </mesh>
      {/* Dome */}
      <mesh position={[0, 0.12, 0]}>
        <sphereGeometry args={[0.24, 20, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color="#7DE3E8" emissive="#34D399" emissiveIntensity={0.45} metalness={0.4} roughness={0.15} transparent opacity={0.75} />
      </mesh>
      {/* Tractor beam — yellow cone hanging down (animated alpha) */}
      <mesh ref={beam} position={[0, -0.7, 0]}>
        <coneGeometry args={[0.55, 1.4, 28, 1, true]} />
        <meshBasicMaterial color="#FFD700" transparent opacity={0.3} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <mesh position={[0, -1.38, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.45, 0.55, 32]} />
        <meshBasicMaterial color="#FFD700" transparent opacity={0.5} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <pointLight intensity={0.9} color="#FFD700" distance={4} />
    </group>
  );
}

function MoonCheese({ refData }) {
  const ref = useRef();
  useFrame((_, dt) => {
    if (!ref.current) return;
    ref.current.position.copy(refData.position);
    ref.current.rotation.y += dt * 3.2;
    ref.current.rotation.x = Math.sin(performance.now() * 0.003) * 0.15;
  });
  // A small "moon cheese wheel" — flattened sphere with a few crater dimples.
  return (
    <group ref={ref}>
      <mesh>
        <sphereGeometry args={[0.22, 24, 18]} />
        <meshStandardMaterial color={COLORS.moonCheese} emissive={COLORS.moonCheese} emissiveIntensity={0.35} metalness={0.25} roughness={0.55} />
      </mesh>
      {/* Rim band gives the cheese-wheel feel */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.22, 0.025, 8, 24]} />
        <meshStandardMaterial color={COLORS.moonCheeseRim} metalness={0.6} roughness={0.35} />
      </mesh>
      {/* Craters */}
      <mesh position={[0.08, 0.04, 0.18]} scale={[1, 1, 0.4]}>
        <sphereGeometry args={[0.045, 10, 8]} />
        <meshStandardMaterial color={COLORS.moonCheeseRim} roughness={0.9} />
      </mesh>
      <mesh position={[-0.1, -0.02, 0.17]} scale={[1, 1, 0.4]}>
        <sphereGeometry args={[0.035, 10, 8]} />
        <meshStandardMaterial color={COLORS.moonCheeseRim} roughness={0.9} />
      </mesh>
      <mesh position={[0.02, 0.1, -0.18]} scale={[1, 1, 0.4]}>
        <sphereGeometry args={[0.04, 10, 8]} />
        <meshStandardMaterial color={COLORS.moonCheeseRim} roughness={0.9} />
      </mesh>
      {/* Soft halo */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.3, 0.42, 24]} />
        <meshBasicMaterial color={COLORS.moonCheese} transparent opacity={0.32} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
    </group>
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
          <torusGeometry args={[0.28, 0.1, 12, 22]} />
        ) : (
          <icosahedronGeometry args={[0.32, 0]} />
        )}
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.95} metalness={0.6} roughness={0.2} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.45, 0.55, 28]} />
        <meshBasicMaterial color={color} transparent opacity={0.55} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
    </group>
  );
}

// ───────────────────────────────────────────── World

// ───────────────────────────────────────────── Player drop-shadow (arcade-style)

/**
 * Cheap circular shadow blob that tracks the player's X position and fades
 * out / shrinks as the player jumps. Sits just above the track plane.
 * Avoids the cost of real shadow maps for hundreds of dynamic meshes.
 */
function PlayerShadow({ refX, refY, sliding }) {
  const ref = useRef();
  useFrame(() => {
    const m = ref.current;
    if (!m) return;
    m.position.x = refX.current;
    const y = refY.current || 0;
    // Scale + opacity ramp from 1.0 at floor → 0.35 at peak jump (~y=2)
    const t = Math.max(0, Math.min(1, y / 2.0));
    const widen = sliding?.current ? 1.4 : 1.0;
    m.scale.set(widen * (1 - t * 0.55), 1, 1 - t * 0.55);
    if (m.material) {
      m.material.opacity = 0.55 * (1 - t * 0.75);
    }
  });
  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.011, 0]}>
      <circleGeometry args={[0.6, 28]} />
      <meshBasicMaterial color="#000000" transparent opacity={0.55} depthWrite={false} />
    </mesh>
  );
}

function World({ onScore, onDeath, onMilestone, onPowerupChange, onStageChange, controlState, runningRef, skinId }) {
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
  const stageRef = useRef(1);
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
    stageRef.current = 1;
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

    // Stage progression — emit once per threshold crossing.
    const curStage = Math.min(5, Math.floor(distanceRef.current / 150) + 1);
    if (curStage > stageRef.current) {
      stageRef.current = curStage;
      onStageChange?.(curStage);
    }

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
        // Build the obstacle pool by current stage (distance-gated).
        const stage = Math.min(5, Math.floor(distanceRef.current / 150) + 1);
        const pool = Object.keys(OBSTACLE_DEFS).filter((k) => OBSTACLE_DEFS[k].minStage <= stage);
        let lane = Math.floor(Math.random() * 3);
        if (inGrace && lane === laneIdxRef.current) {
          lane = (lane + 1) % 3;
        }
        const type = pool[Math.floor(Math.random() * pool.length)];
        const def = OBSTACLE_DEFS[type];
        obstaclesRef.current.push({
          id: Math.random(),
          type,
          lane,
          position: new THREE.Vector3(LANES[lane], def.y, spawnZ),
        });
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
      const def = OBSTACLE_DEFS[o.type];
      if (!def) continue;
      // Tight per-type Z hit window so jumps land cleanly between obstacles.
      if (Math.abs(o.position.z) > def.hz) continue;
      if (o.lane !== playerLane) continue;
      // Per-type clear rule (jump vs slide).
      const cleared = def.clear(py, slidingRef.current);
      if (cleared) continue;
      const hit = true;
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
      <PlayerShadow refX={playerXRef} refY={playerYRef} sliding={slidingRef} />
      <Bullpug
        refX={playerXRef}
        refY={playerYRef}
        sliding={slidingRef}
        running={runningRef}
        shieldActive={shieldActiveRef}
        skinId={skinId}
      />
      {obstaclesState.map((o) => (
        <Obstacle key={o.id} type={o.type} refData={o} />
      ))}
      {coinsState.map((c) => (
        <MoonCheese key={c.id} refData={c} />
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
  { playing, onScoreTick, onDeath, onPowerupChange, onMilestone, onStageChange, skinId = "default", className = "" },
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
      // +25 points per moon cheese (matches the 2D legend)
      score: Math.floor(s.distance) + totalCoinsRef.current * 25,
    });
  }, [onScoreTick]);

  const handleDeath = useCallback((d) => {
    runningRef.current.running = false;
    onDeath?.({
      coins: totalCoinsRef.current,
      distance: d.distance,
      score: Math.floor(d.distance) + totalCoinsRef.current * 25,
    });
  }, [onDeath]);

  return (
    <div className={`relative w-full h-full ${className}`} data-testid="runner-3d-scene">
      <Canvas
        camera={{ position: [0, 2.7, 4.5], fov: 70 }}
        dpr={DPR_CAP}
        gl={{
          antialias: true,
          powerPreference: "high-performance",
          toneMapping: THREE.ACESFilmicToneMapping,
          outputColorSpace: THREE.SRGBColorSpace,
        }}
        onCreated={({ gl }) => {
          gl.toneMappingExposure = 1.18;
        }}
        style={{ background: COLORS.bg, width: "100%", height: "100%" }}
      >
        <fog attach="fog" args={[COLORS.bg, 20, 75]} />
        {/* Ambient: a touch of cool sky fill so shadow sides aren't pitch black */}
        <hemisphereLight args={["#5b3a8a", "#0b0820", 0.55]} />
        <ambientLight intensity={0.25} />
        {/* Key light — soft warm directional from above-right */}
        <directionalLight position={[5, 9, 4]} intensity={1.1} color="#fff5d6" />
        {/* Rim light — purple kicker from behind the runner for that "cosmic" silhouette pop */}
        <directionalLight position={[-3, 4, -8]} intensity={0.75} color="#D946EF" />
        <pointLight position={[0, 4, 0]} intensity={0.8} color="#D946EF" />
        <pointLight position={[0, 4, -20]} intensity={0.7} color="#00FFA3" />
        {/* Subtle warm fill from below to lift the pug's belly out of pure shadow */}
        <pointLight position={[0, -2, 2]} intensity={0.3} color="#F5D300" />

        <Stars radius={120} depth={60} count={5000} factor={4.5} fade saturation={0.7} />
        <Sparkles count={180} scale={[40, 25, 40]} size={3.5} speed={0.35} color="#D946EF" />
        <Sparkles count={90} scale={[30, 15, 30]} size={2.2} speed={0.5} color="#00FFA3" />

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
          onStageChange={onStageChange}
          controlState={controlState}
          runningRef={runningRef}
          skinId={skinId}
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
  const [stageFlash, setStageFlash] = useState(null);
  const stageFlashTimer = useRef(null);
  const [submitState, setSubmitState] = useState({ rank: null, submitted: false });
  const milestoneTimer = useRef(null);
  const skinId = useMemo(() => {
    try { return localStorage.getItem("bullpugSkin") || "default"; } catch (e) { return "default"; }
  }, []);

  const playerName = useMemo(() => {
    try { return (localStorage.getItem("bullpugPlayerName") || "Cosmic Pug").trim().slice(0, 20); }
    catch (e) { return "Cosmic Pug"; }
  }, []);

  const handleMilestone = useCallback((dist) => {
    setMilestone(dist);
    if (milestoneTimer.current) clearTimeout(milestoneTimer.current);
    milestoneTimer.current = setTimeout(() => setMilestone(null), 1600);
  }, []);

  const STAGE_TEASE = {
    2: "Space Debris incoming · jump high!",
    3: "Black Holes opening · jump over!",
    4: "Satellites in orbit · slide under!",
    5: "Alien Ships hunting · slide under!",
  };
  const handleStageChange = useCallback((stage) => {
    setStageFlash({ stage, tease: STAGE_TEASE[stage] || "" });
    if (stageFlashTimer.current) clearTimeout(stageFlashTimer.current);
    stageFlashTimer.current = setTimeout(() => setStageFlash(null), 2200);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submitScoreToBackend = useCallback(async (finalDistance, finalCoins) => {
    const finalScore = Math.floor(finalDistance) + finalCoins * 25;
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
        onStageChange={handleStageChange}
        skinId={skinId}
      />

      {/* HUD */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute top-20 left-4 right-4 flex items-start justify-between">
          <div data-testid="runner-3d-hud-score">
            <div className="text-[10px] uppercase tracking-[0.25em] text-[#00FFA3] font-bold mb-1" style={{ fontFamily: "Orbitron" }}>Distance</div>
            <div className="text-3xl font-black text-white tabular-nums" style={{ fontFamily: "Orbitron" }}>{Math.floor(score.distance)}m</div>
            <div className="mt-2 text-[10px] uppercase tracking-[0.25em] text-[#F5D300] font-bold mb-1" style={{ fontFamily: "Orbitron" }}>Moon Cheese</div>
            <div className="text-xl font-bold text-[#F5D300] tabular-nums" style={{ fontFamily: "Orbitron" }}>🥮 {score.coins}</div>
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
        {stageFlash && (
          <div className="absolute top-1/4 left-0 right-0 text-center" data-testid="runner-3d-stage-flash">
            <div className="inline-block px-6 py-3 rounded-2xl backdrop-blur-md animate-[fadeIn_0.4s_ease-out]"
              style={{ background: "rgba(217,70,239,0.18)", border: "1px solid rgba(217,70,239,0.6)", boxShadow: "0 0 40px rgba(217,70,239,0.45)" }}>
              <div className="text-[10px] uppercase tracking-[0.35em] text-[#F5D300] font-bold mb-1" style={{ fontFamily: "Orbitron" }}>Stage Unlocked</div>
              <div className="text-4xl font-black mb-1" style={{ fontFamily: "Orbitron" }}>
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#D946EF] via-[#FF7A2A] to-[#F5D300]">STAGE {stageFlash.stage}</span>
              </div>
              {stageFlash.tease && (
                <div className="text-xs text-slate-200">{stageFlash.tease}</div>
              )}
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
            <p className="text-slate-300 text-sm mb-6 leading-relaxed">Run forever through the deep PugChain. Dodge meteors, slide under alien ion rings, lane-switch around space debris. Grab power-ups & collect Moon Cheese for the Festival of Barks leaderboard.</p>
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
            <p className="text-slate-300 text-sm mb-2">Moon Cheese collected: <span className="text-[#F5D300] font-bold">🥮 {gameOver.coins}</span></p>
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
