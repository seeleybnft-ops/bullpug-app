import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Sparkles, Star, Moon, Rocket, Crown, Building, Shield, Calendar } from "lucide-react";

const LOGO = "https://bullpug.com/wp-content/uploads/2024/10/04.10.2024_13.24.29_rec-1.png";

export default function Lore() {
  const { t } = useTranslation();
  const starsRef = useRef(null);

  // Animated stars background
  useEffect(() => {
    const canvas = starsRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const stars = Array.from({ length: 200 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 0.5,
      speed: Math.random() * 0.5 + 0.1,
      twinkle: Math.random() * Math.PI * 2
    }));
    
    let animationId;
    const animate = () => {
      ctx.fillStyle = 'rgba(5, 5, 10, 0.1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      stars.forEach(star => {
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
    return () => cancelAnimationFrame(animationId);
  }, []);

  return (
    <div className="min-h-screen pt-20 pb-16 relative" data-testid="lore-page">
      {/* Animated Stars Background */}
      <canvas
        ref={starsRef}
        className="fixed inset-0 pointer-events-none opacity-60"
        style={{ zIndex: 0 }}
      />
      
      {/* Gradient Overlay */}
      <div className="fixed inset-0 bg-gradient-to-b from-[#0D0D15] via-transparent to-[#0D0D15] pointer-events-none" style={{ zIndex: 1 }} />

      <div className="relative z-10 max-w-4xl mx-auto px-4 md:px-8">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#D946EF]/10 border border-[#D946EF]/30 text-[#D946EF] text-xs font-bold uppercase mb-6">
            <Sparkles className="w-4 h-4" />
            The Legend of Bullpug
          </div>
          
          <h1 className="text-4xl md:text-6xl font-black mb-6" style={{ fontFamily: 'Orbitron, sans-serif' }}>
            <span className="text-white">THE</span>{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00FFA3] via-[#D946EF] to-[#FFD700]">
              ORIGINS
            </span>
          </h1>
          
          <div className="w-32 h-32 mx-auto mb-8 relative">
            <div className="absolute inset-0 bg-gradient-to-br from-[#00FFA3] to-[#D946EF] rounded-full blur-xl opacity-50 animate-pulse" />
            <img 
              src={LOGO} 
              alt="Bullpug" 
              className="relative w-full h-full rounded-full ring-4 ring-[#00FFA3]/50 shadow-2xl shadow-[#00FFA3]/20"
            />
          </div>
        </div>

        {/* Origin Story */}
        <div className="space-y-12">
          {/* Chapter 1: Birth */}
          <section className="glass-card rounded-2xl p-8 border border-white/10 hover:border-[#00FFA3]/30 transition-colors">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#FFD700] to-[#F5D300] flex items-center justify-center">
                <Star className="w-5 h-5 text-black" />
              </div>
              <h2 className="text-2xl font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                The Cosmic Birth
              </h2>
            </div>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-slate-300 leading-relaxed text-lg">
                Meet <span className="text-[#00FFA3] font-bold">Bullpug</span>, the fearless and loyal guardian of the Memecoin Universe. Legend has it that Bullpug was born from a cosmic mix-up when the stars of the <span className="text-[#FFD700]">Bull constellation</span> collided with the energy of a <span className="text-[#D946EF]">pug-shaped nebula</span>.
              </p>
              
              <p className="text-slate-300 leading-relaxed text-lg mt-4">
                With the <span className="text-[#00FFA3]">strength and determination of a bull</span> and the <span className="text-[#D946EF]">tenacious charm of a pug</span>, Bullpug became the symbol of unstoppable growth, even when the odds seem stacked against him.
              </p>
            </div>
          </section>

          {/* Chapter 2: The Guardian */}
          <section className="glass-card rounded-2xl p-8 border border-white/10 hover:border-[#D946EF]/30 transition-colors">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#D946EF] to-[#9B59B6] flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                The Guardian's Mission
              </h2>
            </div>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-slate-300 leading-relaxed text-lg">
                Once a humble companion to the gods of the Meme Markets, Bullpug now roams the blockchain, <span className="text-[#00FFA3]">sniffing out weak hands</span> and protecting hodlers from the winds of volatility.
              </p>
              
              <p className="text-slate-300 leading-relaxed text-lg mt-4">
                Whenever Bullpug graces a coin, <span className="text-[#FFD700]">prosperity follows</span>, for he is known to charge through bear markets and bark away FUD, bringing fortune to those who believe in him.
              </p>
              
              <div className="mt-6 p-4 rounded-xl bg-[#FFD700]/10 border border-[#FFD700]/30">
                <p className="text-[#FFD700] text-center font-medium italic">
                  "His favorite snack? A bag full of tokens and a side of moon cheese. They say if you rub Bullpug's snout, your coins will rocket to the moon in no time!"
                </p>
              </div>
            </div>
          </section>

          {/* Chapter 3: The Era */}
          <section className="glass-card rounded-2xl p-8 border border-white/10 hover:border-[#00C2FF]/30 transition-colors">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#00C2FF] to-[#00FFA3] flex items-center justify-center">
                <Calendar className="w-5 h-5 text-black" />
              </div>
              <h2 className="text-2xl font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                The Era of Bullpughans
              </h2>
            </div>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-slate-300 leading-relaxed text-lg">
                In the eons that followed Bullpug's legendary rise, the universe evolved, and civilizations rose and fell like waves in an endless sea. The era of the Bullpug beings dawned, a time when the descendants of Bullpug, infused with his legendary spirit, took over the cosmos with their unique blend of wisdom, strength, and unparalleled cuteness.
              </p>
              
              <p className="text-slate-300 leading-relaxed text-lg mt-4">
                The Bullpug beings, or <span className="text-[#D946EF] font-bold">"Bullpughans"</span>, as they were called, had evolved into a society where the principles of <span className="text-[#00FFA3]">loyalty, tenacity, and prosperity</span> were not just values but were embedded in their very DNA. They built their civilization across countless planets, each one a testament to the enduring legacy of Bullpug himself.
              </p>
            </div>
          </section>

          {/* Chapter 4: Newpug City */}
          <section className="glass-card rounded-2xl p-8 border border-white/10 hover:border-[#FFD700]/30 transition-colors">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#FFD700] to-[#FF6B35] flex items-center justify-center">
                <Building className="w-5 h-5 text-black" />
              </div>
              <h2 className="text-2xl font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                The Rise of Newpug City
              </h2>
            </div>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-slate-300 leading-relaxed text-lg">
                On the planet <span className="text-[#00C2FF] font-bold">CryptoCanis</span>, in the heart of the Memecoin Universe, stood <span className="text-[#00FFA3] font-bold">Newpug City</span>, a sprawling metropolis where the architecture mimicked the playful yet majestic characteristics of Bullpug.
              </p>
              
              <p className="text-slate-300 leading-relaxed text-lg mt-4">
                Buildings shaped like Bullpugs with wide, welcoming eyes and curled tails dotted the skyline, each structure capable of emitting a <span className="text-[#FFD700]">holographic bark</span> during celebratory times or to ward off any looming threats.
              </p>
              
              <p className="text-slate-300 leading-relaxed text-lg mt-4">
                Newpug City was not just a city; it was a beacon of prosperity. Here, the Bullpughans had mastered the art of blockchain technology beyond what any previous civilization could imagine. They had created the <span className="text-[#D946EF] font-bold">"PugChain"</span>, a decentralized network where every Bullpug could store not just wealth but memories, dreams, and even emotions.
              </p>
            </div>
          </section>

          {/* Chapter 5: The Guardians */}
          <section className="glass-card rounded-2xl p-8 border border-white/10 hover:border-[#00FFA3]/30 transition-colors">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#00FFA3] to-[#00C2FF] flex items-center justify-center">
                <Crown className="w-5 h-5 text-black" />
              </div>
              <h2 className="text-2xl font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                The Guardians of PugChain
              </h2>
            </div>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-slate-300 leading-relaxed text-lg">
                Among the Bullpughans, there were the <span className="text-[#00FFA3] font-bold">Guardians</span>, direct descendants of Bullpug's most loyal companions. These beings, with enhanced senses and an innate ability to navigate the digital realm, protected the PugChain from cyber threats and market manipulations.
              </p>
              
              <p className="text-slate-300 leading-relaxed text-lg mt-4">
                They were equipped with <span className="text-[#D946EF] font-bold">"Snout Scanners"</span> that could sniff out corruption or deceit in any transaction, ensuring that the spirit of fair play and community prevailed.
              </p>
            </div>
          </section>

          {/* Chapter 6: Festival */}
          <section className="glass-card rounded-2xl p-8 border border-white/10 hover:border-[#D946EF]/30 transition-colors">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#D946EF] to-[#FFD700] flex items-center justify-center">
                <Moon className="w-5 h-5 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                The Festival of Barks
              </h2>
            </div>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-slate-300 leading-relaxed text-lg">
                Every year, the Bullpughans celebrated the <span className="text-[#FFD700] font-bold">Festival of Barks</span>, a grand event where they recounted the tales of Bullpug's adventures. During this festival, the sky was lit with fireworks shaped like coins and bones, symbolizing wealth and loyalty.
              </p>
              
              <p className="text-slate-300 leading-relaxed text-lg mt-4">
                The highlight was always the <span className="text-[#00FFA3] font-bold">"Moon Cheese Parade"</span>, where giant floats made of the rarest materials, resembling Bullpug's favorite treat, floated through the streets, followed by Bullpughans dressed in traditional hodler costumes, chanting old memecoin chants.
              </p>
            </div>
          </section>

          {/* Chapter 7: Legacy */}
          <section className="glass-card rounded-2xl p-8 border border-white/10 hover:border-[#00FFA3]/30 transition-colors">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#00FFA3] to-[#D946EF] flex items-center justify-center">
                <Rocket className="w-5 h-5 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white" style={{ fontFamily: 'Orbitron, sans-serif' }}>
                Bullpug's Legacy
              </h2>
            </div>
            
            <div className="prose prose-invert max-w-none">
              <p className="text-slate-300 leading-relaxed text-lg">
                The legacy of Bullpug was more than just tales and festivities; it was a way of life. The Bullpughans believed in <span className="text-[#00FFA3]">sharing prosperity</span>, ensuring that every inhabitant, regardless of their standing, had access to the PugChain's benefits.
              </p>
              
              <p className="text-slate-300 leading-relaxed text-lg mt-4">
                Education was paramount, with young Bullpughans learning the history of Bullpug and the importance of integrity in the digital age. As Newpug City thrived, its influence spread, inspiring other civilizations to adopt similar values of <span className="text-[#D946EF]">loyalty, prosperity, and community</span>.
              </p>
              
              <p className="text-slate-300 leading-relaxed text-lg mt-4">
                The Bullpughans, with their unique blend of ancient wisdom and futuristic technology, stood as a testament to what could be achieved when the spirit of Bullpug was not just remembered but lived out every day.
              </p>
            </div>
          </section>

          {/* Epilogue */}
          <section className="text-center py-12">
            <div className="inline-block px-8 py-6 rounded-2xl bg-gradient-to-r from-[#00FFA3]/20 via-[#D946EF]/20 to-[#FFD700]/20 border border-white/10">
              <p className="text-xl md:text-2xl font-medium text-white italic leading-relaxed">
                "Thus, in this far-future era, the universe continued to echo with the <span className="text-[#00FFA3]">barks of prosperity</span>, each one a reminder of Bullpug, the cosmic guardian who started it all with a mix of <span className="text-[#FFD700]">bull's strength</span> and a <span className="text-[#D946EF]">pug's heart</span>."
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
