import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

export const supportedLanguages = {
  en: { nativeName: 'English', flag: '🇺🇸' },
  es: { nativeName: 'Español', flag: '🇪🇸' }
};

// English translations
const enTranslations = {
  // Common
  common: {
    loading: 'Loading...',
    error: 'An error occurred',
    success: 'Success',
    cancel: 'Cancel',
    submit: 'Submit',
    save: 'Save',
    delete: 'Delete',
    back: 'Back',
    refresh: 'Refresh',
    connectWallet: 'Connect Wallet',
    walletRequired: 'Wallet Required',
    language: 'Language'
  },
  // Navbar
  nav: {
    home: 'Home',
    lore: 'Origins',
    arena: 'Arena',
    game: 'Game',
    exitSim: 'Exit Sim',
    reflections: 'Reflections',
    journal: 'Journal',
    forum: 'Forum',
    wallet: 'Wallet',
    admin: 'Admin',
    messages: 'Messages'
  },
  // Betting Arena
  betting: {
    title: 'P2P Arena',
    subtitle: 'Player vs Player • Real SOL • {{rake}}% Rake',
    solOnly: 'SOL Only',
    disclaimer: 'For entertainment - check local laws',
    connectWalletToPlay: 'Connect your Solana wallet to play',
    p2pRequiresWallet: 'P2P betting requires a connected wallet with SOL',
    // Coin Flip
    coinFlip: {
      title: 'P2P Coin Flip',
      createChallenge: 'Create Challenge',
      yourName: 'Your Name',
      betAmount: 'Bet Amount (SOL)',
      yourPick: 'Your Pick',
      heads: 'Heads',
      tails: 'Tails',
      opponentBet: 'Opponent Bet',
      totalPot: 'Total Pot',
      rake: 'Rake',
      winnerGets: 'Winner Gets',
      creating: 'Creating...',
      createBtn: 'Create Challenge',
      yourOpenChallenges: 'Your Open Challenges',
      waitingForOpponent: 'Waiting for opponent...',
      cancel: 'Cancel',
      openChallenges: 'Open Challenges',
      noChallenges: 'No open challenges',
      createOrWait: 'Create one or wait for others!',
      picked: 'Picked',
      youPick: 'You pick',
      accept: 'Accept',
      flipping: 'Flipping...',
      recentFlips: 'Recent P2P Flips',
      youWon: 'YOU WON {{amount}} SOL!',
      youLost: 'YOU LOST',
      coinLandedOn: 'Coin landed on',
      provablyFair: 'Provably Fair Verification',
      serverSeed: 'Server Seed',
      clientSeed: 'Client Seed',
      resultHash: 'Result Hash'
    },
    // Pot
    pot: {
      title: 'Winner Pot',
      joinPot: 'Join Pot',
      yourName: 'Your Name',
      betAmount: 'Bet Amount (SOL)',
      higherBetHigherChance: 'Higher bet = higher win probability. Winner takes all minus {{rake}}% rake.',
      joining: 'Joining...',
      joinBtn: 'Join Pot',
      rakeGoesTo: 'Rake goes to',
      currentPot: 'Current Pot',
      entries: 'Entries',
      won: '{{name}} won {{amount}} SOL!',
      participants: 'Participants',
      chance: 'chance',
      noEntries: 'No entries yet. Be the first!',
      howItWorks: 'How P2P Pot Works',
      rule1: 'Multiple players contribute SOL to the pot',
      rule2: 'Your win probability = your bet / total pot',
      rule3: 'When drawn, one winner takes all',
      rule4: 'Provably fair random selection'
    }
  },
  // Speed Run Game
  game: {
    title: 'Speed Run',
    subtitle: 'Dodge obstacles, collect Mooncake, activate power-ups',
    resetsIn: 'Resets in {{days}}d',
    startGame: 'Start Game',
    spaceToJump: 'SPACE / Tap to jump (double jump!)',
    gameOver: 'GAME OVER',
    score: 'Score',
    mooncake: 'Mooncake',
    newHighScore: 'New High Score!',
    playAgain: 'Play Again',
    shareOnX: 'Share on',
    shareText: 'I just scored {{score}} points in the Bullpug Speed Run game! Can you beat my score?',
    highScore: 'High Score',
    totalMooncake: 'Total Mooncake',
    controls: 'Controls',
    weeklyLeaderboard: 'Weekly Leaderboard',
    noScoresYet: 'No scores this week yet. Be the first!',
    resetMonday: 'Resets every Monday 00:00 UTC',
    mooncakes: 'mooncakes',
    // Power-ups
    shield: 'Shield',
    magnet: 'Magnet',
    doubleScore: '2x Score'
  }
};

// Spanish translations
const esTranslations = {
  // Common
  common: {
    loading: 'Cargando...',
    error: 'Ocurrió un error',
    success: 'Éxito',
    cancel: 'Cancelar',
    submit: 'Enviar',
    save: 'Guardar',
    delete: 'Eliminar',
    back: 'Atrás',
    refresh: 'Actualizar',
    connectWallet: 'Conectar Billetera',
    walletRequired: 'Billetera Requerida',
    language: 'Idioma'
  },
  // Navbar
  nav: {
    home: 'Inicio',
    lore: 'Historia',
    arena: 'Arena',
    game: 'Juego',
    exitSim: 'Simulador',
    reflections: 'Reflexiones',
    journal: 'Diario',
    forum: 'Foro',
    wallet: 'Billetera',
    admin: 'Admin',
    messages: 'Mensajes'
  },
  // Betting Arena
  betting: {
    title: 'Arena P2P',
    subtitle: 'Jugador vs Jugador • SOL Real • {{rake}}% Comisión',
    solOnly: 'Solo SOL',
    disclaimer: 'Para entretenimiento - verifica las leyes locales',
    connectWalletToPlay: 'Conecta tu billetera Solana para jugar',
    p2pRequiresWallet: 'Las apuestas P2P requieren una billetera conectada con SOL',
    // Coin Flip
    coinFlip: {
      title: 'Volado P2P',
      createChallenge: 'Crear Desafío',
      yourName: 'Tu Nombre',
      betAmount: 'Cantidad (SOL)',
      yourPick: 'Tu Elección',
      heads: 'Cara',
      tails: 'Cruz',
      opponentBet: 'Apuesta Oponente',
      totalPot: 'Pozo Total',
      rake: 'Comisión',
      winnerGets: 'Ganador Recibe',
      creating: 'Creando...',
      createBtn: 'Crear Desafío',
      yourOpenChallenges: 'Tus Desafíos Abiertos',
      waitingForOpponent: 'Esperando oponente...',
      cancel: 'Cancelar',
      openChallenges: 'Desafíos Abiertos',
      noChallenges: 'No hay desafíos abiertos',
      createOrWait: '¡Crea uno o espera a otros!',
      picked: 'Eligió',
      youPick: 'Tú eliges',
      accept: 'Aceptar',
      flipping: 'Lanzando...',
      recentFlips: 'Volados P2P Recientes',
      youWon: '¡GANASTE {{amount}} SOL!',
      youLost: 'PERDISTE',
      coinLandedOn: 'La moneda cayó en',
      provablyFair: 'Verificación Justa',
      serverSeed: 'Semilla Servidor',
      clientSeed: 'Semilla Cliente',
      resultHash: 'Hash Resultado'
    },
    // Pot
    pot: {
      title: 'Pozo de Premios',
      joinPot: 'Unirse al Pozo',
      yourName: 'Tu Nombre',
      betAmount: 'Cantidad (SOL)',
      higherBetHigherChance: 'Mayor apuesta = mayor probabilidad de ganar. El ganador se lleva todo menos {{rake}}% de comisión.',
      joining: 'Uniéndose...',
      joinBtn: 'Unirse al Pozo',
      rakeGoesTo: 'Comisión va a',
      currentPot: 'Pozo Actual',
      entries: 'Entradas',
      won: '¡{{name}} ganó {{amount}} SOL!',
      participants: 'Participantes',
      chance: 'probabilidad',
      noEntries: 'Sin entradas aún. ¡Sé el primero!',
      howItWorks: 'Cómo Funciona el Pozo P2P',
      rule1: 'Múltiples jugadores contribuyen SOL al pozo',
      rule2: 'Tu probabilidad de ganar = tu apuesta / pozo total',
      rule3: 'Al sortear, un ganador se lleva todo',
      rule4: 'Selección aleatoria verificable'
    }
  },
  // Speed Run Game
  game: {
    title: 'Carrera',
    subtitle: 'Esquiva obstáculos, colecta Mooncake, activa power-ups',
    resetsIn: 'Reinicia en {{days}}d',
    startGame: 'Iniciar Juego',
    spaceToJump: 'ESPACIO / Toca para saltar (¡doble salto!)',
    gameOver: 'FIN DEL JUEGO',
    score: 'Puntaje',
    mooncake: 'Mooncake',
    newHighScore: '¡Nuevo Récord!',
    playAgain: 'Jugar de Nuevo',
    shareOnX: 'Compartir en',
    shareText: '¡Acabo de obtener {{score}} puntos en el juego Speed Run de Bullpug! ¿Puedes superar mi puntaje?',
    highScore: 'Récord',
    totalMooncake: 'Mooncake Total',
    controls: 'Controles',
    weeklyLeaderboard: 'Tabla Semanal',
    noScoresYet: 'Sin puntajes esta semana. ¡Sé el primero!',
    resetMonday: 'Reinicia cada Lunes 00:00 UTC',
    mooncakes: 'mooncakes',
    // Power-ups
    shield: 'Escudo',
    magnet: 'Imán',
    doubleScore: '2x Puntos'
  }
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: enTranslations },
      es: { translation: esTranslations }
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'es'],
    
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'bullpugLang'
    },

    interpolation: {
      escapeValue: false
    },

    react: {
      useSuspense: false
    },

    debug: false
  });

export default i18n;
