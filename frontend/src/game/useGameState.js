/**
 * useGameState - React hook for managing game state
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { createInitialGameState } from './GameEngine';

/**
 * Custom hook for managing Cosmic Runner game state
 */
export function useGameState(skinBonus = 0, skinColor = '#00FFA3') {
  const [gameState, setGameState] = useState('idle'); // idle, playing, gameover
  const [score, setScore] = useState(0);
  const [moonCheese, setMoonCheese] = useState(0);
  const [currentStage, setCurrentStage] = useState(1);
  const [highScore, setHighScore] = useState(() => 
    parseInt(localStorage.getItem('bullpugHighScore') || '0')
  );
  const [totalMoonCheese, setTotalMoonCheese] = useState(() => 
    parseInt(localStorage.getItem('bullpugMoonCheese') || '0')
  );
  
  const gameRef = useRef(null);
  const animRef = useRef(null);
  const keysRef = useRef({ left: false, right: false, jump: false });

  /**
   * Initialize a new game
   */
  const initGame = useCallback(() => {
    return createInitialGameState(skinBonus, skinColor);
  }, [skinBonus, skinColor]);

  /**
   * Start the game
   */
  const startGame = useCallback(() => {
    gameRef.current = initGame();
    setGameState('playing');
    setScore(0);
    setMoonCheese(0);
    setCurrentStage(1);
  }, [initGame]);

  /**
   * End the game
   */
  const endGame = useCallback((finalScore, finalMoonCheese) => {
    if (gameRef.current) {
      gameRef.current.running = false;
    }
    
    // Update high score
    if (finalScore > highScore) {
      setHighScore(finalScore);
      localStorage.setItem('bullpugHighScore', finalScore.toString());
    }
    
    // Update total moon cheese
    const newTotal = totalMoonCheese + finalMoonCheese;
    setTotalMoonCheese(newTotal);
    localStorage.setItem('bullpugMoonCheese', newTotal.toString());
    
    setGameState('gameover');
  }, [highScore, totalMoonCheese]);

  /**
   * Handle keyboard input
   */
  const handleKeyDown = useCallback((e) => {
    if (gameState !== 'playing') return;
    
    switch (e.key) {
      case 'ArrowLeft':
      case 'a':
      case 'A':
        keysRef.current.left = true;
        e.preventDefault();
        break;
      case 'ArrowRight':
      case 'd':
      case 'D':
        keysRef.current.right = true;
        e.preventDefault();
        break;
      case 'ArrowUp':
      case ' ':
      case 'w':
      case 'W':
        keysRef.current.jump = true;
        e.preventDefault();
        break;
      default:
        break;
    }
  }, [gameState]);

  /**
   * Handle touch input for mobile
   */
  const handleTouch = useCallback((direction) => {
    if (gameState !== 'playing') return;
    
    switch (direction) {
      case 'left':
        keysRef.current.left = true;
        break;
      case 'right':
        keysRef.current.right = true;
        break;
      case 'jump':
        keysRef.current.jump = true;
        break;
      default:
        break;
    }
  }, [gameState]);

  // Setup keyboard listeners
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return {
    // State
    gameState,
    score,
    moonCheese,
    currentStage,
    highScore,
    totalMoonCheese,
    
    // Refs
    gameRef,
    animRef,
    keysRef,
    
    // State setters
    setScore,
    setMoonCheese,
    setCurrentStage,
    setGameState,
    
    // Actions
    initGame,
    startGame,
    endGame,
    handleTouch,
  };
}

export default useGameState;
