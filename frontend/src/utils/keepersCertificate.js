/**
 * generateKeepersCertificate — renders and downloads a KC certificate.
 *
 * Portrait A4, dark background, gold text/borders, Archive aesthetic.
 * Pure client-side via jsPDF — no server round-trip.
 */
import { jsPDF } from "jspdf";

const A4_W = 210;
const A4_H = 297;
const GOLD = [245, 211, 0];
const GOLD_DARK = [201, 162, 0];
const DEEP = [5, 7, 18];
const TEXT_SOFT = [220, 226, 240];
const TEXT_DIM = [148, 163, 184];

function shortenWallet(w) {
  if (!w) return "";
  const s = String(w);
  return s.length <= 10 ? s : `${s.slice(0, 4)}…${s.slice(-4)}`;
}

function drawSignalGlyph(doc, cx, cy, r) {
  // Outer ring
  doc.setDrawColor(...GOLD);
  doc.setLineWidth(0.8);
  doc.circle(cx, cy, r, "S");
  // Inner ring
  doc.setDrawColor(...GOLD_DARK);
  doc.setLineWidth(0.4);
  doc.circle(cx, cy, r - 2, "S");
  // Compass pips (N/E/S/W)
  doc.setFillColor(...GOLD);
  const pipR = 0.9;
  doc.circle(cx, cy - r, pipR, "F");
  doc.circle(cx + r, cy, pipR, "F");
  doc.circle(cx, cy + r, pipR, "F");
  doc.circle(cx - r, cy, pipR, "F");
  // Ember centre
  doc.setFillColor(...GOLD);
  doc.circle(cx, cy, r / 3.2, "F");
}

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      day: "numeric", month: "long", year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function generateKeepersCertificate({ wallet, rankReachedAt }) {
  const doc = new jsPDF({ unit: "mm", format: "a4", orientation: "portrait" });

  // ── Dark background ─────────────────────────────────────────────
  doc.setFillColor(...DEEP);
  doc.rect(0, 0, A4_W, A4_H, "F");

  // Outer gold border (double frame)
  doc.setDrawColor(...GOLD);
  doc.setLineWidth(1.2);
  doc.rect(10, 10, A4_W - 20, A4_H - 20);
  doc.setLineWidth(0.3);
  doc.setDrawColor(...GOLD_DARK);
  doc.rect(13, 13, A4_W - 26, A4_H - 26);

  // Corner pips
  const cornerR = 1.4;
  doc.setFillColor(...GOLD);
  [
    [10, 10], [A4_W - 10, 10], [10, A4_H - 10], [A4_W - 10, A4_H - 10],
  ].forEach(([x, y]) => doc.circle(x, y, cornerR, "F"));

  // ── Kicker ──────────────────────────────────────────────────────
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(...GOLD_DARK);
  doc.text("KEEPER STATION 001 · CERTIFIED SIGNAL", A4_W / 2, 30, {
    align: "center", charSpace: 1.4,
  });

  // ── Title ───────────────────────────────────────────────────────
  doc.setFont("helvetica", "bold");
  doc.setFontSize(30);
  doc.setTextColor(...GOLD);
  doc.text("THE KEEPER'S CIRCLE", A4_W / 2, 48, { align: "center", charSpace: 2 });

  // ── Divider ─────────────────────────────────────────────────────
  doc.setDrawColor(...GOLD_DARK);
  doc.setLineWidth(0.4);
  doc.line(A4_W / 2 - 40, 54, A4_W / 2 + 40, 54);

  // ── SignalGlyph ─────────────────────────────────────────────────
  drawSignalGlyph(doc, A4_W / 2, 90, 16);

  // ── Body copy ───────────────────────────────────────────────────
  doc.setFont("helvetica", "normal");
  doc.setFontSize(12);
  doc.setTextColor(...TEXT_SOFT);
  doc.text("This certifies that", A4_W / 2, 128, { align: "center" });

  // Shortened wallet — big, gold
  const short = shortenWallet(wallet);
  doc.setFont("courier", "bold");
  doc.setFontSize(22);
  doc.setTextColor(...GOLD);
  doc.text(short, A4_W / 2, 142, { align: "center" });

  // Achievement line
  doc.setFont("helvetica", "normal");
  doc.setFontSize(12);
  doc.setTextColor(...TEXT_SOFT);
  const line = "has filed the complete record of the Bullpughan Archive";
  doc.text(line, A4_W / 2, 156, { align: "center" });

  // ── Date achieved ───────────────────────────────────────────────
  doc.setFontSize(9);
  doc.setTextColor(...TEXT_DIM);
  doc.text("RANK ACHIEVED", A4_W / 2, 178, { align: "center", charSpace: 1.4 });

  doc.setFont("courier", "normal");
  doc.setFontSize(12);
  doc.setTextColor(...TEXT_SOFT);
  doc.text(formatDate(rankReachedAt), A4_W / 2, 187, { align: "center" });

  // ── Divider ─────────────────────────────────────────────────────
  doc.setDrawColor(...GOLD_DARK);
  doc.setLineWidth(0.3);
  doc.line(A4_W / 2 - 30, 200, A4_W / 2 + 30, 200);

  // ── Tinkerpug sign-off ──────────────────────────────────────────
  doc.setFont("courier", "italic");
  doc.setFontSize(10);
  doc.setTextColor(...TEXT_SOFT);
  const signoff = "keeper's note: the signal is in The Ledger.\nthat is permanent. that is the point.";
  const lines = signoff.split("\n");
  lines.forEach((l, i) => {
    doc.text(l, A4_W / 2, 216 + i * 6, { align: "center" });
  });

  // ── Signature-y flourish ────────────────────────────────────────
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(...GOLD_DARK);
  doc.text("— TINKERPUG, KEEPER OF THE ARCHIVE", A4_W / 2, 240, {
    align: "center", charSpace: 1.2,
  });

  // ── Footer ──────────────────────────────────────────────────────
  doc.setFont("courier", "normal");
  doc.setFontSize(9);
  doc.setTextColor(...GOLD_DARK);
  doc.text("bullpug.com/archive", A4_W / 2, A4_H - 20, { align: "center" });

  // ── Save ────────────────────────────────────────────────────────
  const fname = `bullpug-keepers-circle-${(wallet || "signal").slice(0, 8)}.pdf`;
  doc.save(fname);
}
