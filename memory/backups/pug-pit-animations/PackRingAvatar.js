/**
 * PackRingAvatar — circular mini-pug avatar used around the Pack Pile
 * "Howl Ring". Lightweight wrapper around `SkinPreview3D` so each pug
 * in the pack reuses the live sculpted geometry.
 *
 * Props:
 *   • walletStr  — used to deterministically pick a skin via the same
 *                  djb2 hash used by `PugPitFaceOff`.
 *   • initial    — single-character label drawn over the disc when no
 *                  3D preview can render (fallback).
 *   • size       — disc diameter in px (default 48).
 *   • pose       — "idle" | "howl" | "rear" | "tuck". The pose maps onto
 *                  the existing Pug Pit keyframes in animations.css.
 *   • isPlayer   — when true, ring color flips to the player's accent
 *                  (#00FFA3) instead of the pack accent (#D946EF).
 */

import { useMemo } from "react";
import SkinPreview3D from "@/components/SkinPreview3D";

const SKIN_POOL = [
  "default", "ethereal", "diamond", "gold", "silver",
  "heatmap", "radioactive", "zombie", "water", "fire", "robot",
];

function skinForWallet(walletStr) {
  if (!walletStr) return "default";
  let h = 5381;
  for (let i = 0; i < walletStr.length; i++) {
    h = ((h << 5) + h + walletStr.charCodeAt(i)) | 0;
  }
  return SKIN_POOL[Math.abs(h) % SKIN_POOL.length];
}

const POSE_CLASS = {
  idle: "",
  howl: "packring-howl",
  rear: "pugpit-rear",
  tuck: "pugpit-tuck",
};

export default function PackRingAvatar({
  walletStr,
  initial = "?",
  size = 48,
  pose = "idle",
  isPlayer = false,
  forceSkin = null,
}) {
  const skinId = useMemo(
    () => forceSkin || skinForWallet(walletStr),
    [forceSkin, walletStr]
  );
  const ringColor = isPlayer ? "#00FFA3" : "#D946EF";

  return (
    <div
      className={`relative inline-block ${POSE_CLASS[pose] || ""}`}
      style={{ width: size, height: size }}
      data-testid={`pack-ring-avatar-${initial.toLowerCase()}`}
    >
      {/* Glow ring backdrop — colored to mark player vs opponent */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `radial-gradient(circle, ${ringColor}33 0%, transparent 70%)`,
        }}
      />
      <div
        className="absolute inset-[8%] rounded-full overflow-hidden border-2"
        style={{ borderColor: ringColor }}
      >
        <SkinPreview3D skinId={skinId} size={size - 8} glowColor={ringColor} />
      </div>
      {/* Initial badge at the bottom — kept tiny so it doesn't fight the
          3D preview but still gives pack roll-call clarity */}
      <div
        className="absolute -bottom-1 left-1/2 -translate-x-1/2 px-1 rounded text-[8px] font-black"
        style={{
          backgroundColor: ringColor,
          color: "#0a0a15",
          fontFamily: "Orbitron, sans-serif",
        }}
      >
        {initial.toUpperCase()}
      </div>
    </div>
  );
}
