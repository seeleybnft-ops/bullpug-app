// Sound effects utility for Bullpug - using Web Audio API
const audioContext = typeof window !== 'undefined' ? new (window.AudioContext || window.webkitAudioContext)() : null;

// Background music management
let bgMusicSource = null;
let bgMusicGain = null;
let bgMusicBuffer = null;
let musicIsPlaying = false;
let musicVolume = 0.3;

// Generate procedural cosmic background music
async function generateCosmicMusicBuffer() {
  if (!audioContext || bgMusicBuffer) return bgMusicBuffer;
  
  const duration = 30; // 30 second loop
  const sampleRate = audioContext.sampleRate;
  const numSamples = duration * sampleRate;
  const buffer = audioContext.createBuffer(2, numSamples, sampleRate);
  
  const leftChannel = buffer.getChannelData(0);
  const rightChannel = buffer.getChannelData(1);
  
  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate;
    
    // Deep space ambient pad (very low frequency drone)
    const pad1 = Math.sin(2 * Math.PI * 55 * t) * 0.08; // Deep bass
    const pad2 = Math.sin(2 * Math.PI * 82.5 * t) * 0.05; // Fifth
    const pad3 = Math.sin(2 * Math.PI * 110 * t + Math.sin(t * 0.5) * 0.5) * 0.04; // Modulated octave
    
    // Ethereal shimmer (high frequency sparkle)
    const shimmer1 = Math.sin(2 * Math.PI * 880 * t) * Math.sin(t * 2) * 0.02;
    const shimmer2 = Math.sin(2 * Math.PI * 1320 * t) * Math.sin(t * 1.5 + 1) * 0.015;
    
    // Cosmic wind (filtered noise)
    const noise = (Math.random() * 2 - 1) * 0.02 * Math.sin(t * 0.3);
    
    // Pulsing rhythm (subtle)
    const pulse = Math.sin(2 * Math.PI * 0.5 * t) * Math.sin(2 * Math.PI * 220 * t) * 0.03;
    
    // Celestial bells (occasional high notes)
    const bell1 = Math.sin(2 * Math.PI * 1760 * t) * Math.exp(-((t % 4) * 3)) * 0.02;
    const bell2 = Math.sin(2 * Math.PI * 2200 * t) * Math.exp(-(((t + 2) % 4) * 3)) * 0.015;
    
    // Mix with stereo spread
    const left = pad1 + pad2 * 0.8 + pad3 + shimmer1 * 1.2 + shimmer2 + noise + pulse + bell1;
    const right = pad1 + pad2 * 1.2 + pad3 + shimmer1 + shimmer2 * 1.2 + noise + pulse + bell2;
    
    // Soft limiting
    leftChannel[i] = Math.tanh(left * 2) * 0.5;
    rightChannel[i] = Math.tanh(right * 2) * 0.5;
  }
  
  bgMusicBuffer = buffer;
  return buffer;
}

// Start background music
export async function startBackgroundMusic() {
  if (!audioContext || musicIsPlaying) return;
  
  try {
    if (audioContext.state === 'suspended') {
      await audioContext.resume();
    }
    
    const buffer = await generateCosmicMusicBuffer();
    if (!buffer) return;
    
    bgMusicGain = audioContext.createGain();
    bgMusicGain.gain.value = musicVolume;
    bgMusicGain.connect(audioContext.destination);
    
    bgMusicSource = audioContext.createBufferSource();
    bgMusicSource.buffer = buffer;
    bgMusicSource.loop = true;
    bgMusicSource.connect(bgMusicGain);
    bgMusicSource.start();
    
    musicIsPlaying = true;
  } catch (e) {
    console.log('Background music error:', e);
  }
}

// Stop background music
export function stopBackgroundMusic() {
  if (bgMusicSource) {
    try {
      bgMusicSource.stop();
      bgMusicSource.disconnect();
    } catch (e) {}
    bgMusicSource = null;
  }
  musicIsPlaying = false;
}

// Set music volume (0-1)
export function setMusicVolume(volume) {
  musicVolume = Math.max(0, Math.min(1, volume));
  if (bgMusicGain) {
    bgMusicGain.gain.value = musicVolume;
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
  startBackgroundMusic,
  stopBackgroundMusic,
  setMusicVolume,
  getMusicVolume,
  isMusicPlaying,
};
