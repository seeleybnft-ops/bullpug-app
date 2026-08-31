import { Link } from "react-router-dom";
import { ExternalLink } from "lucide-react";

const LOGO = "/bullpug-canon.jpg";

export default function Footer() {
  return (
    <footer className="border-t border-white/5 bg-black/60 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-6 md:px-12 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <img src={LOGO} alt="Bullpug" className="w-8 h-8 rounded-full" />
              <span className="font-black text-lg" style={{ fontFamily: 'Orbitron, sans-serif' }}>BULLPUG</span>
            </div>
            <p className="text-sm text-slate-500 leading-relaxed" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Guardian of the Memecoin Universe. Born from stellar chaos, protecting holders since 2024.
            </p>
          </div>

          <div>
            <h4 className="font-bold text-xs uppercase tracking-widest mb-4 text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>Ecosystem</h4>
            <div className="flex flex-col gap-2">
              {/* Cosmic Runner / Skin Store parked during private testing
                  — will return when those features launch. */}
              {[
                {t:"Origins", p:"/origins"},
                {t:"PugBurn", p:"/pugburn"},
                {t:"Forum", p:"/forum"}
              ].map(l=>(
                <Link key={l.p} to={l.p} className="text-sm text-slate-500 hover:text-white transition-colors">{l.t}</Link>
              ))}
            </div>
          </div>

          <div>
            <h4 className="font-bold text-xs uppercase tracking-widest mb-4 text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>Community</h4>
            <div className="flex flex-col gap-2">
              <a href="https://x.com/Bullpugcoin" target="_blank" rel="noopener noreferrer" data-testid="footer-x-link"
                className="text-sm text-slate-500 hover:text-white transition-colors flex items-center gap-1">
                X (Twitter) <ExternalLink size={11} />
              </a>
              <a href="https://t.me/bullpugcoinchat" target="_blank" rel="noopener noreferrer" data-testid="footer-telegram-link"
                className="text-sm text-slate-500 hover:text-white transition-colors flex items-center gap-1">
                Telegram <ExternalLink size={11} />
              </a>
              {/* Skin Showcase parked — reinstate when the skin store launches. */}
            </div>
          </div>

          <div>
            <h4 className="font-bold text-xs uppercase tracking-widest mb-4 text-[#00FFA3]" style={{ fontFamily: 'Orbitron, sans-serif' }}>Legal</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              Disclaimer: $BULLPUG is a memecoin. Crypto investments carry risk. Check your local laws before participating.
            </p>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-white/5 text-center text-xs text-slate-700">
          &copy; 2024-2026 Bullpug. All rights reserved. Built on Solana.
        </div>
      </div>
    </footer>
  );
}
