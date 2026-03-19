// Sound effects utility for Bullpug - using Web Audio API
const audioContext = typeof window !== 'undefined' ? new (window.AudioContext || window.webkitAudioContext)() : null;

// Background music management
let bgMusicAudio = null;
let musicIsPlaying = false;
let musicVolume = 0.4;

// Start background music using the custom MP3 file
export async function startBackgroundMusic() {
  if (musicIsPlaying) return;
  
  try {
    if (!bgMusicAudio) {
      bgMusicAudio = new Audio('/cosmic-runner-music.mp3');
      bgMusicAudio.loop = true;
      bgMusicAudio.volume = musicVolume;
    }
    
    await bgMusicAudio.play();
    musicIsPlaying = true;
  } catch (e) {
    console.log('Background music error:', e);
  }
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
