// Sound effects utility for Bullpug - using Web Audio API
const audioContext = typeof window !== 'undefined' ? new (window.AudioContext || window.webkitAudioContext)() : null;

// Background music management
let bgMusicAudio = null;
let musicIsPlaying = false;
let musicVolume = 0.4;
let musicLoadAttempted = false;

// Preload the music file
function preloadMusic() {
  if (bgMusicAudio || musicLoadAttempted) return;
  musicLoadAttempted = true;
  
  try {
    bgMusicAudio = new Audio('/cosmic-runner-music.mp3');
    bgMusicAudio.loop = true;
    bgMusicAudio.volume = musicVolume;
    bgMusicAudio.preload = 'auto';
    
    // Add event listeners for debugging
    bgMusicAudio.addEventListener('canplaythrough', () => {
      console.log('Music loaded and ready to play');
    });
    
    bgMusicAudio.addEventListener('error', (e) => {
      console.error('Music load error:', e);
      bgMusicAudio = null;
      musicLoadAttempted = false;
    });
  } catch (e) {
    console.error('Failed to create audio element:', e);
  }
}

// Preload on module init if in browser
if (typeof window !== 'undefined') {
  // Delay preload slightly to not block initial render
  setTimeout(preloadMusic, 1000);
}

// Start background music using the custom MP3 file
export async function startBackgroundMusic() {
  if (musicIsPlaying) return true;
  
  try {
    // Ensure audio is loaded
    if (!bgMusicAudio) {
      preloadMusic();
      // Wait a bit for load
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    if (!bgMusicAudio) {
      console.warn('Music audio element not available');
      return false;
    }
    
    // Reset to start if needed
    bgMusicAudio.currentTime = 0;
    bgMusicAudio.volume = musicVolume;
    
    // Try to play
    const playPromise = bgMusicAudio.play();
    
    if (playPromise !== undefined) {
      await playPromise;
      musicIsPlaying = true;
      console.log('Background music started successfully');
      return true;
    }
  } catch (e) {
    // NotAllowedError is common due to autoplay policy
    if (e.name === 'NotAllowedError') {
      console.log('Music blocked by autoplay policy - will play on next user interaction');
    } else {
      console.error('Background music error:', e);
    }
    return false;
  }
  
  return musicIsPlaying;
}

// Stop background music
export function stopBackgroundMusic() {
  if (bgMusicAudio) {
    bgMusicAudio.pause();
    bgMusicAudio.currentTime = 0;
  }
  musicIsPlaying = false;
}

// Set music volume (0-1)
export function setMusicVolume(volume) {
  musicVolume = Math.max(0, Math.min(1, volume));
  if (bgMusicAudio) {
    bgMusicAudio.volume = musicVolume;
  }
}

// Get music volume
export function getMusicVolume() {
  return musicVolume;
}

// Check if music is playing
export function isMusicPlaying() {
  return musicIsPlaying;
}

// Sound presets
const sounds = {
  win: { frequency: 880, duration: 0.3, type: 'sine', gain: 0.3 },
  lose: { frequency: 220, duration: 0.4, type: 'sawtooth', gain: 0.2 },
  flip: { frequency: 440, duration: 0.1, type: 'square', gain: 0.15 },
  click: { frequency: 600, duration: 0.05, type: 'sine', gain: 0.1 },
  collect: { frequency: 1200, duration: 0.1, type: 'sine', gain: 0.2 },
  powerup: { frequency: 660, duration: 0.2, type: 'triangle', gain: 0.25 },
  gameover: { frequency: 150, duration: 0.5, type: 'sawtooth', gain: 0.2 },
  jump: { frequency: 300, duration: 0.1, type: 'square', gain: 0.1 },
  newHighScore: { frequency: 1000, duration: 0.4, type: 'sine', gain: 0.3 },
  // New sounds
  betPlaced: { frequency: 520, duration: 0.15, type: 'triangle', gain: 0.2 },
  challengeCreated: { frequency: 700, duration: 0.2, type: 'sine', gain: 0.25 },
  potJoin: { frequency: 400, duration: 0.2, type: 'triangle', gain: 0.2 },
  notification: { frequency: 800, duration: 0.15, type: 'sine', gain: 0.15 },
  coinLand: { frequency: 350, duration: 0.25, type: 'square', gain: 0.2 },
  countdown: { frequency: 500, duration: 0.1, type: 'sine', gain: 0.15 },
  success: { frequency: 750, duration: 0.2, type: 'sine', gain: 0.2 },
  error: { frequency: 200, duration: 0.3, type: 'sawtooth', gain: 0.15 },
  hover: { frequency: 450, duration: 0.03, type: 'sine', gain: 0.05 },
  swoosh: { frequency: 300, duration: 0.15, type: 'sawtooth', gain: 0.1 },
  // Big-win celebration — arpeggio fanfare (handled specially below)
  bigWin: { frequency: 660, duration: 1.4, type: 'sine', gain: 0.3 },
  // Pug Pit sounds — sub-bass howl for Pack Pile tension build (≤10s),
  // sharp bark for the bone-drop winner reveal. Both routed through the
  // existing oscillator pipeline so they respect the user's mute toggle.
  howl: { frequency: 220, duration: 0.9, type: 'sawtooth', gain: 0.18 },
  bark: { frequency: 320, duration: 0.18, type: 'square', gain: 0.25 },
};

// Play a tone
export function playTone(soundName) {
  if (!audioContext) return;
  
  const sound = sounds[soundName];
  if (!sound) return;
  
  try {
    // Resume audio context if suspended (browser autoplay policy)
    if (audioContext.state === 'suspended') {
      audioContext.resume();
    }
    
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.type = sound.type;
    oscillator.frequency.setValueAtTime(sound.frequency, audioContext.currentTime);
    
    // Add frequency sweep for more interesting sounds
    if (soundName === 'win') {
      oscillator.frequency.exponentialRampToValueAtTime(1760, audioContext.currentTime + sound.duration);
    } else if (soundName === 'lose') {
      oscillator.frequency.exponentialRampToValueAtTime(110, audioContext.currentTime + sound.duration);
    } else if (soundName === 'collect') {
      oscillator.frequency.exponentialRampToValueAtTime(1800, audioContext.currentTime + sound.duration);
    } else if (soundName === 'newHighScore') {
      // Arpeggio effect
      oscillator.frequency.setValueAtTime(880, audioContext.currentTime + 0.1);
      oscillator.frequency.setValueAtTime(1100, audioContext.currentTime + 0.2);
      oscillator.frequency.setValueAtTime(1320, audioContext.currentTime + 0.3);
    } else if (soundName === 'howl') {
      // Dog howl tail-off — pitch rises then drops, like a real howl
      oscillator.frequency.setValueAtTime(220, audioContext.currentTime);
      oscillator.frequency.linearRampToValueAtTime(380, audioContext.currentTime + 0.25);
      oscillator.frequency.exponentialRampToValueAtTime(110, audioContext.currentTime + sound.duration);
    } else if (soundName === 'bark') {
      // Sharp bark — quick downward chirp
      oscillator.frequency.setValueAtTime(420, audioContext.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(180, audioContext.currentTime + sound.duration);
    }
    
    gainNode.gain.setValueAtTime(sound.gain, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + sound.duration);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + sound.duration);
  } catch (e) {
    console.log('Sound playback error:', e);
  }
}

// Play coin flip animation sound sequence
export function playCoinFlipSequence(isWin, onComplete) {
  if (!audioContext) {
    onComplete?.();
    return;
  }
  
  // Play flip sounds
  let flipCount = 0;
  const flipInterval = setInterval(() => {
    playTone('flip');
    flipCount++;
    if (flipCount >= 6) {
      clearInterval(flipInterval);
      // Small delay then result sound
      setTimeout(() => {
        playTone(isWin ? 'win' : 'lose');
        onComplete?.();
      }, 200);
    }
  }, 100);
}

// Check if sound is enabled (stored in localStorage)
export function isSoundEnabled() {
  return localStorage.getItem('bullpugSoundEnabled') !== 'false';
}

export function setSoundEnabled(enabled) {
  localStorage.setItem('bullpugSoundEnabled', enabled ? 'true' : 'false');
}

// Wrapper that respects user preference
export function playSoundIfEnabled(soundName) {
  if (isSoundEnabled()) {
    playTone(soundName);
  }
}

/**
 * Pack-howl chorus — 4 overlapping `howl` tones at staggered offsets so
 * the result reads as a pack of pugs howling together, not a single
 * lone tone. Used in the Pack Pile when the countdown drops below 10s.
 * Respects the user's sound-enabled preference.
 */
export function playPackHowl() {
  if (!isSoundEnabled() || !audioContext) return;
  const offsets = [0, 120, 260, 410]; // ms between each "pup joining in"
  offsets.forEach((delay) => setTimeout(() => playTone('howl'), delay));
}

/**
 * Single sharp bark — used the moment the bone drops + the alpha is
 * declared. Quick, satisfying punctuation on the win reveal.
 */
export function playBark() {
  playSoundIfEnabled('bark');
}

// Haptic feedback for mobile devices
export function vibrate(pattern = [50]) {
  if (typeof window !== 'undefined' && 'vibrate' in navigator) {
    try {
      navigator.vibrate(pattern);
    } catch (e) {
      // Vibration not supported or permission denied
    }
  }
}

// Combined sound + haptic feedback
export function feedback(soundName, vibratePattern = [30]) {
  playSoundIfEnabled(soundName);
  vibrate(vibratePattern);
}

// Haptic patterns
export const hapticPatterns = {
  light: [20],
  medium: [50],
  heavy: [100],
  success: [50, 30, 50],
  error: [100, 50, 100],
  win: [50, 30, 100, 30, 150],
  lose: [200],
  click: [10],
  collect: [30, 20, 30],
};

// Feedback presets combining sound + haptic
export function winFeedback() {
  feedback('win', hapticPatterns.win);
}

export function loseFeedback() {
  feedback('lose', hapticPatterns.lose);
}

export function collectFeedback() {
  feedback('collect', hapticPatterns.collect);
}

export function clickFeedback() {
  feedback('click', hapticPatterns.click);
}

export function betPlacedFeedback() {
  feedback('betPlaced', hapticPatterns.medium);
}

export function challengeCreatedFeedback() {
  feedback('challengeCreated', hapticPatterns.success);
}

/**
 * Multi-note triumphant fanfare for big wins (>= 1 SOL). Plays a major
 * arpeggio (C5 → E5 → G5 → C6) with a sustained high overtone and a soft
 * sparkle "ting" on top, accompanied by a celebratory haptic pattern.
 * Falls back silently if audio context is unavailable or the user has
 * disabled sound.
 */
export function playBigWinFanfare() {
  if (!isSoundEnabled() || !audioContext) return;
  try {
    if (audioContext.state === 'suspended') audioContext.resume();
    const t0 = audioContext.currentTime;
    // C major triad arpeggio rising into octave (C5→E5→G5→C6→E6)
    const notes = [
      { f: 523.25, t: 0.00, d: 0.18, gain: 0.30, type: 'triangle' }, // C5
      { f: 659.25, t: 0.12, d: 0.18, gain: 0.30, type: 'triangle' }, // E5
      { f: 783.99, t: 0.24, d: 0.22, gain: 0.32, type: 'triangle' }, // G5
      { f: 1046.5, t: 0.40, d: 0.30, gain: 0.34, type: 'sine' },     // C6
      { f: 1318.5, t: 0.60, d: 0.55, gain: 0.30, type: 'sine' },     // E6 sustain
    ];
    // Add a soft sparkle layer — square wave 1 octave up dropped low
    const sparkle = [
      { f: 2093, t: 0.65, d: 0.08, gain: 0.10, type: 'square' },
      { f: 2349, t: 0.78, d: 0.08, gain: 0.10, type: 'square' },
      { f: 2637, t: 0.90, d: 0.10, gain: 0.10, type: 'square' },
    ];
    for (const n of [...notes, ...sparkle]) {
      const osc = audioContext.createOscillator();
      const g = audioContext.createGain();
      osc.type = n.type;
      osc.frequency.setValueAtTime(n.f, t0 + n.t);
      g.gain.setValueAtTime(0, t0 + n.t);
      g.gain.linearRampToValueAtTime(n.gain, t0 + n.t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.001, t0 + n.t + n.d);
      osc.connect(g);
      g.connect(audioContext.destination);
      osc.start(t0 + n.t);
      osc.stop(t0 + n.t + n.d + 0.01);
    }
    // Celebration haptic — long-medium-long
    vibrate([80, 50, 80, 50, 200]);
  } catch (e) {
    // Silent fail — never let audio errors break the toast
  }
}

export default {
  playTone,
  playCoinFlipSequence,
  isSoundEnabled,
  setSoundEnabled,
  playSoundIfEnabled,
  vibrate,
  feedback,
  hapticPatterns,
  winFeedback,
  loseFeedback,
  collectFeedback,
  clickFeedback,
  betPlacedFeedback,
  challengeCreatedFeedback,
  playBigWinFanfare,
  startBackgroundMusic,
  stopBackgroundMusic,
  setMusicVolume,
  getMusicVolume,
  isMusicPlaying,
};
