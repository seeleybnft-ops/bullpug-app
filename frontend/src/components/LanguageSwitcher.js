import { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { supportedLanguages } from "@/i18n/config";
import { Globe, ChevronDown, Check } from "lucide-react";

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const currentLang = i18n.language?.substring(0, 2) || 'en';
  const currentLanguage = supportedLanguages[currentLang] || supportedLanguages.en;

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLanguageChange = async (langCode) => {
    try {
      await i18n.changeLanguage(langCode);
      localStorage.setItem('bullpugLang', langCode);
      setIsOpen(false);
    } catch (error) {
      console.error('Error changing language:', error);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        data-testid="language-switcher"
        className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-[#00FFA3]/50 transition-all"
        aria-label="Change language"
        aria-expanded={isOpen}
      >
        <Globe size={14} />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-36 bg-[#0A0A12] border border-white/10 rounded-lg shadow-xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="py-1">
            {Object.entries(supportedLanguages).map(([code, { nativeName, flag }]) => (
              <button
                key={code}
                onClick={() => handleLanguageChange(code)}
                data-testid={`lang-${code}`}
                className={`w-full px-3 py-2 text-left text-xs flex items-center gap-2 transition-colors ${
                  currentLang === code
                    ? 'bg-[#00FFA3]/10 text-[#00FFA3]'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <span className="text-base">{flag}</span>
                <span className="flex-1" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                  {nativeName}
                </span>
                {currentLang === code && <Check size={12} className="text-[#00FFA3]" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
