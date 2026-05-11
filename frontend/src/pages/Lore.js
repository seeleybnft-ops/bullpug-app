import { useEffect, useRef } from "react";
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
} from "lucide-react";

const LOGO =
  "https://customer-assets.emergentagent.com/job_5d6a5e00-50cf-4b65-9a94-df993e3bd9bc/artifacts/o46e15vc_BULLPUG.jfif";

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
            testid="chapter-cosmic-birth"
          >
            <p>
              Before the <H color="#A78BFA">Mindverse</H> had a name, before{" "}
              <H color="#A78BFA">G*BOY</H> tore through its fabric and operatives
              learned to read its signals, there was something already moving
              through the space between minds. Not a person. Not a memory.{" "}
              <span className="italic text-slate-100">
                Something older than both.
              </span>
            </p>
            <p>
              The Mindverse is built from what people carry — fears, obsessions,
              grief, desire. Most mind places belong to someone. Most are
              fragile, shaped by a single consciousness that can crack or be
              corrupted or go quiet. But deep in the network, in the unmapped
              regions where no single mind claims territory, something different
              can form.
            </p>
            <p className="text-slate-200 italic">
              It forms when enough people want the same thing at the same time.
            </p>
            <p>
              In the early years of the blockchain age, millions of people —
              scattered across continents, speaking different languages, holding
              different dreams — shared one feeling in common: they were tired
              of being taken from. Tired of rug pulls. Tired of bad actors in
              expensive suits who moved markets like chess pieces and left
              ordinary people holding nothing. The want for something fair —
              something loyal, something that would actually grow{" "}
              <span className="italic">with</span> them instead of{" "}
              <span className="italic">against</span> them — that want was
              enormous. It was electric. And in the Mindverse, collective want
              doesn't just float.{" "}
              <H color="#00FFA3">It coheres.</H>
            </p>
            <p>
              That's when the stars of the{" "}
              <H color="#FFD700">Bull constellation</H> met the swirling energy
              of a <H color="#D946EF">pug-shaped nebula</H> in the shared space
              between a million desperate, hopeful minds.
            </p>
            <p className="text-xl md:text-2xl font-black text-white">
              That's when <H color="#00FFA3">Bullpug</H> was born.
            </p>
          </Chapter>

          {/* 2. A DIFFERENT KIND OF ENTITY */}
          <Chapter
            icon={ShieldOff}
            title="A Different Kind of Entity"
            accent="#00FFA3"
            gradient="linear-gradient(135deg, #00FFA3 0%, #00C2FF 100%)"
            testid="chapter-different-entity"
          >
            <p>
              Bullpug is not a test subject. He was never experimented on, never
              assigned a designation, never held in a chamber. He has no file at{" "}
              <H color="#FF6B6B">Saint Juniper Research Campus</H>.{" "}
              <H color="#FF6B6B">MITER-Corp</H>'s logs don't mention him — and
              that, in itself, is significant, because MITER-Corp monitors{" "}
              <span className="italic">everything</span>.
            </p>
            <p>
              He is something the system was never built to account for: a being
              that emerged not from trauma or control, but from{" "}
              <H color="#00FFA3">collective hope</H>.
            </p>
            <p>
              Where most Mindverse entities are shaped by the memories and fears
              of their host minds, Bullpug exists in the unmapped space — a
              free-floating mind place built from the financial dreams and
              frustrated ambitions of millions of ordinary people. He is the
              embodiment of what they wanted the market to be:{" "}
              <H color="#FFD700">strong as a bull</H>,{" "}
              <H color="#D946EF">loyal as a dog</H>, stubborn enough to hold
              through any storm.
            </p>
            <p>
              He carries the strength and determination of the Bull constellation
              and the tenacious, unshakeable charm of the pug nebula from which
              his form was drawn. He cannot be rugged. He cannot be shorted into
              nothing. He was made from the refusal to accept that.
            </p>
            <div className="mt-2 p-4 rounded-xl bg-[#FFD700]/10 border border-[#FFD700]/30">
              <p className="text-[#FFD700] text-center font-medium italic">
                His favorite snack? A bag full of tokens and a side of moon
                cheese. They say if you rub Bullpug's snout, your coins will
                rocket to the moon in no time.
              </p>
            </div>
          </Chapter>

          {/* 3. THE MINDVERSE HE CALLS HOME */}
          <Chapter
            icon={Eye}
            title="The Mindverse He Calls Home"
            accent="#A78BFA"
            gradient="linear-gradient(135deg, #A78BFA 0%, #D946EF 100%)"
            testid="chapter-mindverse"
          >
            <p>
              Bullpug's mind place exists outside the coordinates that{" "}
              <H color="#FF6B6B">MITER-Corp</H> and{" "}
              <H color="#FF6B6B">Aurelian Systems</H> have mapped. Their
              surveillance infrastructure — the same one that monitors{" "}
              <H color="#FF6B6B">Harmony</H> patients, tracks non-responsive
              individuals, and feeds data back through the{" "}
              <H color="#FF6B6B">IRIS</H> system — has never detected it.
            </p>
            <p>
              This is by nature, not accident. The place wasn't built by one
              mind that could be located, tracked, or dosed into silence. It was
              built by{" "}
              <H color="#00FFA3">millions of minds that never knew they were building anything</H>
              . No single person holds the address. No single person can give it
              up.
            </p>
            <p>
              Over time, this mind place grew into something vast. A planet unto
              itself within the Mindverse, known among those who've stumbled
              into it as <H color="#00C2FF">CryptoCanis</H> — a world shaped by
              the collective imagination of everyone who ever believed the
              market could be something worth trusting.
            </p>
          </Chapter>

          {/* 4. NEWPUG CITY */}
          <Chapter
            icon={Building2}
            title="Newpug City"
            accent="#FFD700"
            gradient="linear-gradient(135deg, #FFD700 0%, #FF6B35 100%)"
            image="/lore/newpug-city.png"
            imageAlt="The skyline of Newpug City — pug-faced skyscrapers under a cosmic nebula, emitting holographic green soundwaves"
            testid="chapter-newpug-city"
          >
            <p>
              At the heart of CryptoCanis stands{" "}
              <H color="#00FFA3">Newpug City</H>, a sprawling metropolis unlike
              anything else in the Mindverse.
            </p>
            <p>
              The architecture mirrors Bullpug himself — wide-eyed, curly-tailed,
              built to welcome. Buildings rise in forms that seem almost playful
              until you realize how structurally sound they are, how resistant
              to pressure. During times of prosperity, the city emits{" "}
              <H color="#FFD700">holographic barks</H> that ripple through the
              skyline like aurora. During times of threat, that same system
              becomes a warning network, loud and impossible to ignore.
            </p>
            <p>
              Newpug City runs on the <H color="#D946EF">PugChain</H> — a
              decentralized network that the Bullpughans built over generations.
              Unlike the surveillance systems MITER-Corp developed, or the
              patient monitoring infrastructure Aurelian routes through IRIS,
              the PugChain stores not just wealth but{" "}
              <span className="italic">memories, dreams, and emotions</span>. It
              was designed to be owned by everyone on it and controlled by
              none. Transparency is its core architecture. Corruption, by
              design, cannot hide inside it.
            </p>
            <p className="italic text-slate-100">
              It is, in almost every way, the opposite of what the people behind
              Harmony were building in the physical world.
            </p>
          </Chapter>

          {/* 5. THE BULLPUGHANS */}
          <Chapter
            icon={Users}
            title="The Bullpughans"
            accent="#00FFA3"
            gradient="linear-gradient(135deg, #00FFA3 0%, #00C2FF 100%)"
            image="/lore/snout-scanner.png"
            imageAlt="Close-up of a Snout Scanner — a sleek titanium handheld device shaped like a stylised dog snout, projecting a holographic blockchain lattice"
            testid="chapter-bullpughans"
          >
            <p>
              In the eons that followed Bullpug's emergence, the mind place
              evolved. Inhabitants took shape — beings infused with Bullpug's
              original spirit, carrying his values forward as civilization.
              These are the <H color="#D946EF">Bullpughans</H>.
            </p>
            <p>
              They are not gods. They are not soldiers or test subjects or
              operatives in someone else's war. They are a people who built
              something from scratch using only the principles their origin
              demanded:{" "}
              <H color="#00FFA3">loyalty, tenacity, and shared prosperity</H>.
            </p>
            <p>
              The Bullpughans spread across CryptoCanis and beyond, each
              settlement a testament to what happens when a civilization refuses
              to be built on exploitation. Their society has no MITER-Corp
              equivalent. No Aurelian Systems. No drug that smooths out the
              edges of people until they stop asking questions.
            </p>
            <p>
              Among them, the most revered are the{" "}
              <H color="#FFD700">Guardians</H> — direct descendants of Bullpug's
              earliest companions, beings with enhanced instincts and a
              near-supernatural ability to navigate the digital realm. They are
              equipped with <H color="#D946EF">Snout Scanners</H>, tools that
              can detect corruption or deceit in any transaction at the
              molecular level of the chain. Where IRIS watches patients and
              flags the ones who resist, the Guardians watch the PugChain and
              flag the ones who deceive.
            </p>
          </Chapter>

          {/* 6. FESTIVAL OF BARKS */}
          <Chapter
            icon={Moon}
            title="The Festival of Barks"
            accent="#D946EF"
            gradient="linear-gradient(135deg, #D946EF 0%, #FFD700 100%)"
            image="/lore/festival-of-barks.png"
            imageAlt="The Festival of Barks — coin- and bone-shaped fireworks light up the sky above Newpug City as moon-cheese floats parade through the streets"
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
              Bullpughans dress in traditional hodler costumes and chant the old
              memecoin chants — words that started as jokes in the physical
              world and became, somewhere in the crossing into the Mindverse,
              something closer to <span className="italic">scripture</span>.
            </p>
            <p>
              It's a celebration, yes. But it's also a ritual of remembrance. A
              deliberate act of <H color="#00FFA3">not forgetting</H> where
              Bullpug came from — from want, from exhaustion, from the desperate
              hope of people who had been burned too many times and still
              refused to stop believing.
            </p>
            <p>
              In a universe where Harmony is designed to make people forget,
              where emotional flattening is marketed as balance and behavioral
              uniformity is called peace, the Festival of Barks is{" "}
              <H color="#FFD700">a radical act</H>.
            </p>
          </Chapter>

          {/* 7. THE SIGNAL IN THE NOISE */}
          <Chapter
            icon={Radio}
            title="The Signal in the Noise"
            accent="#00C2FF"
            gradient="linear-gradient(135deg, #00C2FF 0%, #00FFA3 100%)"
            testid="chapter-signal"
          >
            <p>
              There are those in the <H color="#A78BFA">Neuko network</H> —
              operatives who've gone deep enough into the Mindverse,
              puzzle-solvers who've cracked enough ciphers — who have started
              picking up something they can't fully explain.
            </p>
            <p>
              Not a frequency from MITER-Corp. Not a transmission from Saint
              Juniper. <H color="#FFD700">Something warmer</H>. Something that
              moves at its own rhythm, not the 152 BPM pattern Aurelian flagged
              in the G-304 modulation trials, but something adjacent to it — a
              signal that feels less like surveillance and more like a{" "}
              <H color="#00FFA3">heartbeat</H>.
            </p>
            <p>
              Some believe it's CryptoCanis. Some believe Bullpug's mind place
              has grown large enough that it's started to bleed at the edges of
              the Mindverse map.
            </p>
            <p>
              What everyone agrees on is this: wherever the signal is strongest,
              bad actors have a harder time operating. Markets in that radius
              behave more fairly. People who should have been rugged aren't.
              Wallets that should have been drained hold.
            </p>
            <p className="italic text-slate-100">
              Nobody at Aurelian Systems can explain it. There's no entry in
              MITER-Corp's files.
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
            testid="chapter-legacy"
          >
            <p>
              Bullpug's legacy is not a monument. It's not a file or a
              designation or a badge distributed through a chain of operatives.
              It lives in the PugChain, in Newpug City's skyline, in every
              Bullpughan who woke up one morning understanding, without being
              taught, that{" "}
              <H color="#FFD700">
                prosperity is only worth having if everyone around you has a
                shot at it too
              </H>
              .
            </p>
            <p>
              In a Mindverse increasingly threatened by forces that want to
              flatten human experience into something manageable, something
              uniform, something quiet — Bullpug is the opposite of quiet.
            </p>
            <p>
              He is <H color="#FFD700">loud</H>. He is{" "}
              <H color="#D946EF">loyal</H>. He charges through bear markets and
              barks away FUD and sniffs out the rot before it spreads.
            </p>
            <p>He was born from the want of millions.</p>
            <p className="text-lg md:text-xl text-white font-bold">
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
                it all with a mix of <span className="text-[#FFD700]">bull's strength</span>{" "}
                and a <span className="text-[#D946EF]">pug's heart</span>."
              </p>
            </div>
          </section>

          {/* CANON ANCHOR — Neuko universe */}
          <section
            className="rounded-2xl border border-white/10 bg-black/40 backdrop-blur-md p-6 md:p-8"
            data-testid="lore-canon-anchor"
          >
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-full bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
                <Lock className="w-4 h-4 text-slate-300" />
              </div>
              <p className="text-xs md:text-sm text-slate-400 leading-relaxed">
                Bullpug exists within the{" "}
                <H color="#A78BFA">Neuko universe</H>. His mind place,{" "}
                <H color="#00C2FF">CryptoCanis</H>, sits in the unmapped regions
                of the Mindverse — beyond the reach of MITER-Corp's surveillance
                and Aurelian Systems' monitoring infrastructure. The PugChain
                and its Guardians operate independently of any known corporate
                research program.{" "}
                <span className="text-slate-300 italic">This is by design.</span>
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
