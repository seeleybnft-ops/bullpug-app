import { useEffect, useRef, useState } from "react";
import {
  Sparkles,
  Eye,
  Building2,
  Users,
  Moon,
  Radio,
  Rocket,
  ShieldOff,
  Lock,
  Share2,
  Check,
} from "lucide-react";
import { RankBadge } from "../components/RankBadge";

const LOGO =
  "/bullpug-canon.jpg";

// ── Act I placeholder ──────────────────────────────────────────────────
// Sits where the "Watch trailer" button used to. Renders a slowly
// pulsing gold SignalGlyph + a keeper's-log message + an email capture
// so we can tell subscribers when Act I drops. Read-only otherwise.
//
// When Act I episodes are ready, this component is what gets swapped:
//   • Simplest path: replace <ActIPlaceholder /> with a
//     <VideoPlayer src={…} poster={…} /> component.
//   • Or add a `video` prop here: `<ActIPlaceholder video={…} />`. When
//     `video` is truthy, render the player instead of the placeholder
//     body. Layout wrapper stays identical either way.
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function ActIPlaceholder() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState(null); // null | "success" | "invalid" | "error"

  const onSubmit = async (e) => {
    e?.preventDefault?.();
    const trimmed = email.trim();
    if (!EMAIL_RE.test(trimmed)) {
      setStatus("invalid");
      return;
    }
    setSubmitting(true);
    setStatus(null);
    try {
      const res = await fetch(`${API}/newsletter/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Bullpug-CSRF": "1" },
        body: JSON.stringify({ email: trimmed, source: "act1-placeholder" }),
      });
      if (!res.ok) throw new Error("subscribe failed");
      setStatus("success");
    } catch {
      setStatus("error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="flex flex-col items-center gap-3 max-w-xs"
      data-testid="act-i-placeholder"
      role="status"
      aria-live="polite"
    >
      <div
        className="opacity-90"
        style={{ animation: "act-i-glyph-pulse 3.4s ease-in-out infinite" }}
      >
        <RankBadge rank="keepers_circle" size={68} showTitle={false} />
      </div>
      <p
        className="text-[11px] leading-relaxed text-slate-300 text-center whitespace-pre-line"
        style={{ fontFamily: "monospace" }}
        data-testid="act-i-placeholder-message"
      >
        {`keeper's log — the signal is coming.
the record will be updated.
watch this space.`}
      </p>

      {status === "success" ? (
        <p
          className="text-[11px] leading-relaxed text-center whitespace-pre-line px-2 py-2 rounded-lg"
          style={{
            fontFamily: "monospace",
            color: "#F5D300",
            background: "rgba(245,211,0,0.06)",
            border: "1px solid rgba(245,211,0,0.28)",
          }}
          data-testid="act-i-notify-success"
        >
          keeper's note: signal logged.{"\n"}you'll know when it arrives.
        </p>
      ) : (
        <form
          onSubmit={onSubmit}
          className="w-full flex flex-col gap-2 mt-1"
          data-testid="act-i-notify-form"
        >
          <input
            type="text"
            inputMode="email"
            autoComplete="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); if (status === "invalid") setStatus(null); }}
            placeholder="your@email"
            data-testid="act-i-notify-input"
            className="w-full px-3 py-2 rounded-lg bg-black/50 border border-white/15 focus:border-[#F5D300]/60 focus:outline-none text-xs text-white placeholder:text-slate-600"
            style={{ fontFamily: "monospace" }}
            disabled={submitting}
          />
          <button
            type="submit"
            disabled={submitting}
            data-testid="act-i-notify-submit"
            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: "#F5D300",
              color: "#0a0a12",
              fontFamily: "Orbitron, sans-serif",
              boxShadow: "0 0 14px rgba(245,211,0,0.25)",
            }}
          >
            {submitting ? "sending…" : "notify me when the signal arrives"}
          </button>
          {status === "invalid" && (
            <p
              className="text-[10px] text-red-300/90 text-center"
              style={{ fontFamily: "monospace" }}
              data-testid="act-i-notify-invalid"
            >
              keeper's note: that address isn't a valid signal.
            </p>
          )}
          {status === "error" && (
            <p
              className="text-[10px] text-red-300/90 text-center"
              style={{ fontFamily: "monospace" }}
              data-testid="act-i-notify-error"
            >
              keeper's note: the channel dropped. try again.
            </p>
          )}
        </form>
      )}

      <style>{`
        @keyframes act-i-glyph-pulse {
          0%, 100% { transform: scale(1);     filter: drop-shadow(0 0 8px rgba(245,211,0,0.35)); }
          50%      { transform: scale(1.055); filter: drop-shadow(0 0 18px rgba(245,211,0,0.6)); }
        }
      `}</style>
    </div>
  );
}

// Reusable chapter card — keeps visual rhythm consistent
function Chapter({ icon: Icon, title, accent, gradient, image, imageAlt, children, testid }) {
  return (
    <section
      className="glass-card rounded-2xl border border-white/10 transition-colors overflow-hidden"
      data-testid={testid}
    >
      {image && (
        <div className="relative w-full aspect-[16/9] overflow-hidden">
          <img
            src={image}
            alt={imageAlt || title}
            loading="lazy"
            className="w-full h-full object-cover"
            data-testid={`${testid}-image`}
          />
          {/* Gradient fade at the bottom edge so the image blends into the card body */}
          <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[#0D0D15] to-transparent pointer-events-none" />
        </div>
      )}
      <div className="p-8 md:p-10">
        <div className="flex items-center gap-3 mb-6">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: gradient }}
          >
            <Icon className="w-5 h-5 text-black" />
          </div>
          <h2
            className="text-2xl md:text-3xl font-bold tracking-tight"
            style={{ fontFamily: "Orbitron, sans-serif", color: accent }}
          >
            {title}
          </h2>
        </div>
        <div className="space-y-4 text-slate-300 leading-relaxed text-base md:text-lg">
          {children}
        </div>
      </div>
    </section>
  );
}

// Inline word highlight
function H({ color, children }) {
  return (
    <span className="font-semibold" style={{ color }}>
      {children}
    </span>
  );
}

export default function Lore() {
  const starsRef = useRef(null);

  useEffect(() => {
    const canvas = starsRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const stars = Array.from({ length: 200 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 0.5,
      speed: Math.random() * 0.5 + 0.1,
      twinkle: Math.random() * Math.PI * 2,
    }));

    let animationId;
    const animate = () => {
      ctx.fillStyle = "rgba(5, 5, 10, 0.1)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      stars.forEach((star) => {
        star.twinkle += 0.02;
        const alpha = 0.5 + Math.sin(star.twinkle) * 0.3;
        ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fill();
        star.y += star.speed;
        if (star.y > canvas.height) {
          star.y = 0;
          star.x = Math.random() * canvas.width;
        }
      });
      animationId = requestAnimationFrame(animate);
    };
    animate();

    const onResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  // Share / replay handlers used by the bottom CTA block
  const [shared, setShared] = useState(false);

  const handleShare = async () => {
    const shareText =
      "The Origins page is live — read the Bullpug canon: pug-faced skyscrapers, Snout Scanners, and a heartbeat in the noise. 🐾⚡";
    const url = `${window.location.origin}/lore`;
    try {
      if (navigator.share && typeof navigator.share === "function") {
        await navigator.share({ title: "Bullpug Origins", text: shareText, url });
        setShared(true);
        setTimeout(() => setShared(false), 2200);
        return;
      }
    } catch (e) {
      /* user cancelled the native sheet — fall through to clipboard */
    }
    try {
      await navigator.clipboard.writeText(`${shareText}\n${url}`);
      setShared(true);
      setTimeout(() => setShared(false), 2200);
    } catch (e) {
      const intent = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(url)}`;
      window.open(intent, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div className="min-h-screen pt-20 pb-16 relative" data-testid="lore-page">
      <canvas
        ref={starsRef}
        className="fixed inset-0 pointer-events-none opacity-60"
        style={{ zIndex: 0 }}
      />
      <div
        className="fixed inset-0 bg-gradient-to-b from-[#0D0D15] via-transparent to-[#0D0D15] pointer-events-none"
        style={{ zIndex: 1 }}
      />

      <div className="relative z-10 max-w-4xl mx-auto px-4 md:px-8">
        {/* HERO */}
        <div className="text-center mb-16">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#D946EF]/10 border border-[#D946EF]/30 text-[#D946EF] text-xs font-bold uppercase mb-6"
            data-testid="lore-hero-badge"
          >
            <Sparkles className="w-4 h-4" />
            The Legend of Bullpug
          </div>

          <h1
            className="text-4xl md:text-6xl lg:text-7xl font-black mb-6 tracking-tighter"
            style={{ fontFamily: "Orbitron, sans-serif" }}
          >
            <span className="text-white">THE</span>{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00FFA3] via-[#D946EF] to-[#FFD700]">
              ORIGINS
            </span>
          </h1>

          <p className="text-slate-400 max-w-2xl mx-auto text-sm md:text-base">
            A story of collective hope, unmapped places, and a guardian the
            system was never built to detect.
          </p>

          <div className="w-32 h-32 mx-auto mt-8 mb-2 relative">
            <div className="absolute inset-0 bg-gradient-to-br from-[#00FFA3] to-[#D946EF] rounded-full blur-xl opacity-50 animate-pulse" />
            <img
              src={LOGO}
              alt="Bullpug"
              className="relative w-full h-full rounded-full ring-4 ring-[#00FFA3]/50 shadow-2xl shadow-[#00FFA3]/20 object-cover"
            />
          </div>
        </div>

        <div className="space-y-10 md:space-y-12">
          {/* 1. THE COSMIC BIRTH */}
          <Chapter
            icon={Sparkles}
            title="The Cosmic Birth"
            accent="#FFD700"
            gradient="linear-gradient(135deg, #FFD700 0%, #F5D300 100%)"
            image="/lore/cosmic-birth.jpg"
            imageAlt="The Cosmic Birth of Bullpug — the Bull constellation meeting a pug-shaped nebula"
            testid="chapter-cosmic-birth"
          >
            <p>
              Before the <H color="#A78BFA">Between</H> had a name, before
              anyone had learned to read its currents, there was something
              already moving through the space between minds.
            </p>
            <p>
              Not a person. Not a memory. Something older than both.
            </p>
            <p>
              The Between is built from what people carry — fears, obsessions,
              grief, desire. Most of its realms belong to someone. Most of them
              are fragile, shaped by a single consciousness that can crack, or
              be corrupted, or go quiet. But deep in the network, in the
              unmapped regions where no single mind claims territory, something
              different can form.
            </p>
            <p className="italic text-slate-100">
              It forms when enough people want the same thing at the same time.
            </p>
            <p>
              In the early years of the blockchain age, millions of people —
              scattered across continents, speaking different languages,
              holding different dreams — shared one feeling in common: they
              were tired of being taken from. Tired of rug pulls. Tired of bad
              actors in expensive suits who moved markets like chess pieces and
              left ordinary people holding nothing. The want for something{" "}
              <span className="italic">fair</span> — something loyal, something
              that would actually grow with them instead of against them — that
              want was enormous. It was electric.
            </p>
            <p className="italic text-slate-100">
              And in the Between, collective want doesn't just float. <H color="#00FFA3">It coheres.</H>
            </p>
            <p>
              That's when the stars of the{" "}
              <H color="#FFD700">Bull constellation</H> met the swirling energy
              of a <H color="#D946EF">pug-shaped nebula</H> in the shared space
              between a million desperate, hopeful minds.
            </p>
            <p className="italic text-slate-100 text-xl md:text-2xl font-black text-white">
              That's when <H color="#00FFA3">Bullpug</H> was born.
            </p>
          </Chapter>

          {/* 2. A DIFFERENT KIND OF ENTITY */}
          <Chapter
            icon={ShieldOff}
            title="A Different Kind of Entity"
            accent="#00FFA3"
            gradient="linear-gradient(135deg, #00FFA3 0%, #00C2FF 100%)"
            image="/lore/different-kind-of-entity.jpg"
            imageAlt="A Different Kind of Entity — Bullpug shown as a being that no registry ever accounted for"
            testid="chapter-different-entity"
          >
            <p>
              Bullpug was never designed. No one issued him, funded him, or
              wrote him into existence. There is no founder behind him, no
              allocation, no file in any registry. He was never minted by any
              hand — and that, in itself, is significant, because everything
              else in the markets was.
            </p>
            <p className="italic text-slate-100">
              He is something the old systems were never built to account for.
            </p>
            <p>
              Where most beings of the Between are shaped by the memories and
              fears of a single host mind, Bullpug exists in the unmapped space
              — a free-floating realm built from the financial dreams and
              frustrated ambitions of millions of ordinary people. He is the
              embodiment of what they wanted the market to be:{" "}
              <H color="#FFD700">strong as a bull</H>,{" "}
              <H color="#D946EF">loyal as a dog</H>, stubborn enough to hold
              through any storm.
            </p>
            <p>
              He carries the strength and determination of the Bull
              constellation and the tenacious, unshakeable charm of the pug
              nebula from which his form was drawn. He cannot be rugged. He
              cannot be shorted into nothing. He was{" "}
              <span className="italic">made</span> from the refusal to accept
              that.
            </p>
            <p>
              What he did before he became what he is — the path he walked
              through the unmapped Between, what it showed him, what it cost
              him, what he carried back — that record exists. The Archive
              holds it, for those who ask the right questions.
            </p>
            <div className="mt-2 p-4 rounded-xl bg-[#FFD700]/10 border border-[#FFD700]/30">
              <p className="text-[#FFD700] text-center font-medium italic">
                His favourite snack? A bag full of tokens and a side of moon
                cheese. They say if you rub Bullpug's snout, your coins will
                rocket to the moon in no time.
              </p>
            </div>
          </Chapter>

          {/* 3. THE WORLD HE CALLS HOME */}
          <Chapter
            icon={Eye}
            title="The World He Calls Home"
            accent="#A78BFA"
            gradient="linear-gradient(135deg, #A78BFA 0%, #D946EF 100%)"
            image="/lore/world-he-calls-home.jpg"
            imageAlt="The World He Calls Home — Newpug City skyline of pug-faced skyscrapers under a cosmic nebula, holographic barks rippling like aurora"
            testid="chapter-world"
          >
            <p>
              Bullpug's realm exists outside every map ever drawn of the{" "}
              <H color="#A78BFA">Between</H>. No registry lists it. No watcher
              has ever charted a route to it.
            </p>
            <p>
              This is by nature, not accident. The place wasn't built by one
              mind that could be located, tracked, or silenced. It was built by{" "}
              <H color="#00FFA3">millions of minds that never knew they were building anything</H>.
            </p>
            <p className="italic text-slate-100">
              No single person holds the address. No single person can give it up.
            </p>
            <p>
              Over time, this realm grew into something vast. A planet unto
              itself within the Between, known among those who've stumbled into
              it as <H color="#00C2FF">CryptoCanis</H> — a world shaped by the
              collective imagination of everyone who ever believed the market
              could be something worth trusting.
            </p>
          </Chapter>

          {/* 4. NEWPUG CITY */}
          <Chapter
            icon={Building2}
            title="Newpug City"
            accent="#FFD700"
            gradient="linear-gradient(135deg, #FFD700 0%, #FF6B35 100%)"
            image="/lore/newpug-city.jpg"
            imageAlt="Newpug City — the metropolis at the heart of CryptoCanis, pug-faced skyscrapers running on the PugChain"
            testid="chapter-newpug-city"
          >
            <p>
              At the heart of CryptoCanis stands{" "}
              <H color="#00FFA3">Newpug City</H> — a sprawling metropolis
              unlike anything else in the Between.
            </p>
            <p>
              The architecture mirrors Bullpug himself — wide-eyed,
              curly-tailed, built to welcome. Buildings rise in forms that seem
              almost playful until you realise how structurally sound they
              are, how resistant to pressure. During times of prosperity, the
              city emits <H color="#FFD700">holographic barks</H> that ripple
              through the skyline like aurora. During times of threat, that
              same system becomes a warning network, loud and impossible to
              ignore.
            </p>
            <p>
              Newpug City runs on the <H color="#D946EF">PugChain</H> — a
              decentralised network that the Bullpughans built over
              generations. Unlike the ledgers of the old markets — written by
              the powerful and edited by the guilty — the PugChain stores not
              just wealth but{" "}
              <span className="italic">memories, dreams, and emotions</span>.
              It was designed to be owned by everyone on it and controlled by
              none.
            </p>
            <p className="italic text-slate-100">
              Transparency is its core architecture. Corruption, by design,
              cannot hide inside it.
            </p>
            <p>
              There are places beneath the city that most Bullpughans have
              never seen. Records kept in the cold and the dark, older than
              the spires above them. The Guardians know what's down there.
              Some of them have keys.
            </p>
          </Chapter>

          {/* 5. THE BULLPUGHANS */}
          <Chapter
            icon={Users}
            title="The Bullpughans"
            accent="#00FFA3"
            gradient="linear-gradient(135deg, #00FFA3 0%, #00C2FF 100%)"
            image="/lore/bullpughans.jpg"
            imageAlt="The Bullpughans — descendants of Bullpug's earliest companions, a Guardian raising a Snout Scanner over the PugChain"
            testid="chapter-bullpughans"
          >
            <p>
              In the eons that followed Bullpug's emergence, the realm evolved.
              Inhabitants took shape — beings infused with Bullpug's original
              spirit, carrying his values forward as civilisation. These are
              the <H color="#D946EF">Bullpughans</H>.
            </p>
            <p>
              They are not gods. They are not soldiers, subjects, or pieces in
              someone else's game. They are a people who built something from
              scratch using only the principles their origin demanded:{" "}
              <H color="#00FFA3">loyalty, tenacity, and shared prosperity</H>.
            </p>
            <p className="italic text-slate-100">
              They built something that refuses to be built on exploitation.
            </p>
            <p>
              The Bullpughans spread across CryptoCanis and beyond, each
              settlement a testament to what happens when a civilisation
              keeps no watchers and sells no quiet — nothing that smooths the
              edges off people until they stop asking questions.
            </p>
            <p>
              Among them, the most revered are the{" "}
              <H color="#FFD700">Guardians</H> — direct descendants of
              Bullpug's earliest companions, beings with enhanced instincts
              and a near-supernatural ability to navigate the digital realm.
              They are equipped with <H color="#D946EF">Snout Scanners</H>,
              tools that can detect corruption or deceit in any transaction at
              the molecular level of the chain.
            </p>
            <p className="italic text-slate-100">
              The Guardians watch the PugChain, and what they flag is deceit.
            </p>
            <p>
              The Guardians are four. Each arrived here by a different road,
              and none of those roads were easy. The elder carries runes that
              aren't decorative. The seer pays a price for what she sees. The
              charge spent twelve years in the wreckage before he ever threw
              a punch. The keeper has been watching the chain longer than most
              people know the chain exists.
            </p>
            <p className="italic text-slate-100">
              Ask Tinkerpug about them. He keeps the records.
            </p>
          </Chapter>

          {/* 6. FESTIVAL OF BARKS */}
          <Chapter
            icon={Moon}
            title="The Festival of Barks"
            accent="#D946EF"
            gradient="linear-gradient(135deg, #D946EF 0%, #FFD700 100%)"
            image="/lore/festival-of-barks.jpg"
            imageAlt="The Festival of Barks — coin- and bone-shaped fireworks above Newpug City, moon-cheese floats parading through the streets, Bullpughans in hodler costumes"
            testid="chapter-festival"
          >
            <p>
              Once a year, Newpug City stops everything for the{" "}
              <H color="#FFD700">Festival of Barks</H>.
            </p>
            <p>
              The sky fills with fireworks shaped like coins and bones. Giant
              floats built from the rarest materials roll through the streets,
              sculpted in the likeness of Bullpug's legendary moon cheese.
              Bullpughans dress in traditional hodler costumes and chant the
              old memecoin chants — words that started as jokes in the physical
              world and became, somewhere in the crossing into the Between,
              something closer to <span className="italic">scripture</span>.
            </p>
            <p className="italic text-slate-100">
              It's a celebration. But it's also a ritual of remembrance.
            </p>
            <p>
              A deliberate act of <H color="#00FFA3">not forgetting</H> where
              Bullpug came from — from want, from exhaustion, from the
              desperate hope of people who had been burned too many times and
              still refused to stop believing.
            </p>
            <p className="italic text-slate-100">
              In a universe where forgetting is the cheapest thing on sale,
              the Festival of Barks is <H color="#FFD700">a radical act</H>.
            </p>
          </Chapter>

          {/* 7. THE SIGNAL IN THE NOISE */}
          <Chapter
            icon={Radio}
            title="The Signal in the Noise"
            accent="#00C2FF"
            gradient="linear-gradient(135deg, #00C2FF 0%, #00FFA3 100%)"
            image="/lore/signal-in-the-noise.jpg"
            imageAlt="The Signal in the Noise — Bullpug above his followers, cutting a golden path through the FUD clouds and bear-market shadows"
            testid="chapter-signal"
          >
            <p>
              There are those who travel deep in the Between — drifters,
              seekers, the ones who've learned to listen — who have started
              picking up something they can't fully explain.
            </p>
            <p>
              Not a market frequency. Not a transmission with an owner behind
              it. <H color="#FFD700">Something warmer</H>. Something that moves
              at its own rhythm — a signal that feels less like machinery and
              more like a <H color="#00FFA3">heartbeat</H>.
            </p>
            <p>
              Some believe it's CryptoCanis. Some believe Bullpug's realm has
              grown large enough that it has started to bleed at the edges of
              the map.
            </p>
            <p className="italic text-slate-100">
              Wherever the signal is strongest, bad actors have a harder time
              operating.
            </p>
            <p>
              Markets in that radius behave more fairly. People who should
              have been rugged aren't. Wallets that should have been drained
              hold. Nobody can explain it. No record accounts for it.
            </p>
            <p>
              There are those, too, who believe the signal isn't random. That
              it finds specific people. That surviving a loss with your
              belief intact puts out a particular frequency — one that
              something in the unmapped Between has learned to recognise.
            </p>
            <p className="italic text-slate-100">
              Whether that's true is not a question the origins page can
              answer. Tinkerpug might, if you ask the right way.
            </p>
            <p className="text-lg md:text-xl text-white font-bold">
              Bullpug doesn't announce himself. He just shows up where he's
              needed.
            </p>
          </Chapter>

          {/* 8. THE LEGACY */}
          <Chapter
            icon={Rocket}
            title="The Legacy"
            accent="#00FFA3"
            gradient="linear-gradient(135deg, #00FFA3 0%, #D946EF 100%)"
            image="/lore/legacy.jpg"
            imageAlt="The Legacy — Bullpug in his cosmic cape, silhouetted against the nebula, the pack watching from the star field"
            testid="chapter-legacy"
          >
            <p>
              Bullpug's legacy is not a monument. It's not a file or a
              designation or a title handed down. It lives in the PugChain, in
              Newpug City's skyline, in every Bullpughan who woke up one
              morning understanding, without being taught, that{" "}
              <H color="#FFD700">
                prosperity is only worth having if everyone around you has a
                shot at it too
              </H>
              .
            </p>
            <p>
              In a Between increasingly threatened by forces that want to
              flatten human experience into something manageable, something
              uniform, something quiet — Bullpug is the opposite of quiet.
            </p>
            <p className="italic text-slate-100">
              He is <H color="#FFD700">loud</H>. He is{" "}
              <H color="#D946EF">loyal</H>. He charges through bear markets
              and barks away FUD and sniffs out the rot before it spreads.
            </p>
            <p>He was born from the want of millions.</p>
            <p className="italic text-slate-100 text-lg md:text-xl text-white font-bold">
              He will not stop until that want is answered.
            </p>
          </Chapter>

          {/* EPILOGUE */}
          <section className="text-center py-10">
            <div className="inline-block px-8 py-6 rounded-2xl bg-gradient-to-r from-[#00FFA3]/20 via-[#D946EF]/20 to-[#FFD700]/20 border border-white/10 max-w-3xl">
              <p className="text-xl md:text-2xl font-medium text-white italic leading-relaxed">
                "Thus, the universe continues to echo with the{" "}
                <span className="text-[#00FFA3]">barks of prosperity</span> —
                each one a reminder of Bullpug, the cosmic guardian who started
                it all with a mix of{" "}
                <span className="text-[#FFD700]">bull's strength</span> and a{" "}
                <span className="text-[#D946EF]">pug's heart</span>."
              </p>
            </div>
          </section>

          {/* ACT I PLACEHOLDER + SHARE CTA — between epilogue and canon anchor.
              When Act I episodes are ready, swap `<ActIPlaceholder />` for the
              video player component (single-component swap or add a `<VideoPlayer src={…} />`
              alongside — layout wraps both). No redesign needed. */}
          <section
            className="rounded-2xl border border-[#00FFA3]/20 bg-gradient-to-br from-[#0F1018] to-[#0a0a12] p-6 md:p-8"
            data-testid="lore-actions-block"
          >
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div className="flex-1">
                <p
                  className="text-[10px] uppercase tracking-[0.3em] text-[#00FFA3] font-bold mb-2"
                  style={{ fontFamily: "Space Grotesk, sans-serif" }}
                >
                  Carry it forward
                </p>
                <h3
                  className="text-xl md:text-2xl font-black text-white tracking-tight leading-snug"
                  style={{ fontFamily: "Orbitron, sans-serif" }}
                >
                  Spread the signal across the Between.
                </h3>
                <p className="text-sm text-slate-400 mt-2 max-w-lg leading-relaxed">
                  Share the Origins page with someone who's tired of being rugged.
                  The Archive rewards persistence.
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0 flex-wrap">
                {/* Placeholder for the Act I video slot — sits where the
                    "Watch trailer" button used to. Structured so a
                    <VideoPlayer /> can drop in with no layout change. */}
                <ActIPlaceholder />
                <button
                  type="button"
                  onClick={handleShare}
                  data-testid="lore-share-btn"
                  aria-live="polite"
                  className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-transparent border border-white/20 text-white font-bold text-xs uppercase tracking-wider hover:bg-white/5 hover:border-white/30 transition-colors"
                >
                  {shared ? (
                    <>
                      <Check size={14} />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Share2 size={14} />
                      Share the Origins
                    </>
                  )}
                </button>
              </div>
            </div>
          </section>

          {/* CANON ANCHOR */}
          <section
            className="rounded-2xl border border-white/10 bg-black/40 backdrop-blur-md p-6 md:p-8"
            data-testid="lore-canon-anchor"
          >
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-full bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
                <Lock className="w-4 h-4 text-slate-300" />
              </div>
              <p className="text-xs md:text-sm text-slate-400 leading-relaxed">
                The <H color="#D946EF">Bullpughan universe</H> is sovereign.{" "}
                <H color="#00C2FF">CryptoCanis</H> sits in the unmapped regions
                of the <H color="#A78BFA">Between</H> — beyond any map, any
                registry, any watcher. The PugChain and its Guardians answer
                to no one but the pack.{" "}
                <span className="text-slate-300 italic">This is by design.</span>
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
