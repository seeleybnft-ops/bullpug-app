/**
 * PugPitFaceOff — fighting-game style two-pug face-off card for the Pug Pit.
 *
 * Renders the player's equipped Cosmic Runner skin (left side) against an
 * opponent's deterministic skin (right side) with a centered VS badge.
 * Both pugs use the live `SkinPreview3D` component, which routes through
 * `Bullpug` → `SculptedPugBody` so the meshes match exactly what the user
 * sees in the game and the Skin Store (no separate low-poly preview path).
 *
 * Modes:
 *   • "idle" — both pugs slowly spin (the default rotate inside SkinPreview3D).
 *   • "clashing" — both pugs lunge inward via CSS keyframe (lasts ~2s); used
 *     during the coin-flip resolve animation.
 *   • "win" — player rears with a horns-up gold glow.
 *   • "loss" — player tail-tucks (rotate + dim).
 *
 * Opponent skin: deterministic from a simple wallet-string hash so the
 * same opponent always shows the same skin without requiring a backend
 * field. Falls back to "default" if no opponent string is passed.
 */

import { useMemo } from "react";
import SkinPreview3D from "@/components/SkinPreview3D";

const SKIN_POOL = [
  "default", "ethereal", "diamond", "gold", "silver",
  "heatmap", "radioactive", "zombie", "water", "fire", "robot",
];

/** djb2-ish hash → deterministic skin pick from a wallet string. */
function skinForOpponent(walletStr) {
  if (!walletStr) return "default";
  let h = 5381;
  for (let i = 0; i < walletStr.length; i++) {
    h = ((h << 5) + h + walletStr.charCodeAt(i)) | 0;
  }
  return SKIN_POOL[Math.abs(h) % SKIN_POOL.length];
}

export default function PugPitFaceOff({
  playerSkin,
  opponentWallet,
  opponentName = "???",
  playerName = "You",
  mode = "idle",
  size = 110,
}) {
  const opponentSkin = useMemo(() => skinForOpponent(opponentWallet), [opponentWallet]);

  // Per-mode keyframe class for each side. Win/loss only apply to the
  // player (left) so the loser's pug stays neutral; the rest happen
  // symmetrically (or mirrored) on both sides.
  const playerAnim =
    mode === "clashing" ? "pugpit-lunge-left" :
    mode === "win" ? "pugpit-rear" :
    mode === "loss" ? "pugpit-tuck" :
    "";
  const opponentAnim =
    mode === "clashing" ? "pugpit-lunge-right" :
    mode === "win" ? "pugpit-tuck" :     // opponent loses when player wins
    mode === "loss" ? "pugpit-rear" :    // opponent rears when player loses
    "";

  return (
    <div className="flex items-center justify-between gap-2 sm:gap-4" data-testid="pug-pit-face-off">
      {/* Player side */}
      <div className={`flex flex-col items-center ${playerAnim}`}>
        <SkinPreview3D skinId={playerSkin || "default"} size={size} glowColor="#00FFA3" />
        <p className="mt-1 text-[10px] font-bold text-[#00FFA3] uppercase tracking-wider truncate max-w-[120px]">
          {playerName}
        </p>
      </div>

      {/* VS badge */}
      <div className="flex flex-col items-center">
        <div
          className="px-3 py-1 rounded-md bg-gradient-to-br from-[#D946EF] to-[#00FFA3] text-black text-xs font-black"
          style={{ fontFamily: "Orbitron, sans-serif", letterSpacing: "0.15em" }}
          data-testid="pug-pit-vs-badge"
        >
          VS
        </div>
        {mode === "clashing" && (
          <p className="text-[9px] text-amber-400 uppercase mt-1 animate-pulse">Snarl-off</p>
        )}
        {mode === "win" && (
          <p className="text-[9px] text-[#00FFA3] uppercase mt-1 font-bold">Top dog</p>
        )}
        {mode === "loss" && (
          <p className="text-[9px] text-red-400 uppercase mt-1 font-bold">Tail tucked</p>
        )}
      </div>

      {/* Opponent side — name above the preview for visual balance */}
      <div className={`flex flex-col items-center ${opponentAnim}`}>
        <SkinPreview3D skinId={opponentSkin} size={size} glowColor="#D946EF" />
        <p className="mt-1 text-[10px] font-bold text-[#D946EF] uppercase tracking-wider truncate max-w-[120px]">
          {opponentName}
        </p>
      </div>
    </div>
  );
}
