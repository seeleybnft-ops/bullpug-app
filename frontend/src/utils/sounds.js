// Sound effects utility for Bullpug - using Web Audio API
const audioContext = typeof window !== 'undefined' ? new (window.AudioContext || window.webkitAudioContext)() : null;

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

export default {
  playTone,
  playCoinFlipSequence,
  isSoundEnabled,
  setSoundEnabled,
  playSoundIfEnabled,
};
