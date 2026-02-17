import { useCallback, useRef, useEffect } from 'react';

/**
 * Custom hook for handling game player controls
 * Supports keyboard (A/D, Arrow keys, Space) and touch (swipe, tap)
 */
export function usePlayerControls(gameState, onStart) {
  const keysRef = useRef({ left: false, right: false, jump: false });
  const touchStartRef = useRef({ x: 0, y: 0, time: 0 });

  // Reset keys when game state changes
  useEffect(() => {
    if (gameState !== 'playing') {
      keysRef.current = { left: false, right: false, jump: false };
    }
  }, [gameState]);

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (gameState !== 'playing') {
        if (e.code === 'Space' || e.code === 'Enter') {
          e.preventDefault();
          onStart?.();
        }
        return;
      }

      switch (e.code) {
        case 'ArrowLeft':
        case 'KeyA':
          e.preventDefault();
          keysRef.current.left = true;
          break;
        case 'ArrowRight':
        case 'KeyD':
          e.preventDefault();
          keysRef.current.right = true;
          break;
        case 'Space':
        case 'ArrowUp':
        case 'KeyW':
          e.preventDefault();
          keysRef.current.jump = true;
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameState, onStart]);

  // Touch control handlers
  const handleTouchStart = useCallback(
    (e, canvasRect) => {
      if (gameState !== 'playing') {
        onStart?.();
        return;
      }

      const touch = e.touches[0];
      touchStartRef.current = {
        x: touch.clientX - canvasRect.left,
        y: touch.clientY - canvasRect.top,
        time: Date.now(),
      };
    },
    [gameState, onStart]
  );

  const handleTouchMove = useCallback(
    (e) => {
      if (gameState !== 'playing') return;
      e.preventDefault();
    },
    [gameState]
  );

  const handleTouchEnd = useCallback(
    (e, canvasRect) => {
      if (gameState !== 'playing') return;

      const touch = e.changedTouches[0];
      const endX = touch.clientX - canvasRect.left;
      const endY = touch.clientY - canvasRect.top;

      const deltaX = endX - touchStartRef.current.x;
      const deltaY = endY - touchStartRef.current.y;
      const deltaTime = Date.now() - touchStartRef.current.time;

      const minSwipeDistance = 30;
      const maxSwipeTime = 500;

      if (deltaTime < maxSwipeTime) {
        // Swipe detection
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
          // Horizontal swipe - change lane
          if (deltaX > 0) {
            keysRef.current.right = true;
            setTimeout(() => (keysRef.current.right = false), 100);
          } else {
            keysRef.current.left = true;
            setTimeout(() => (keysRef.current.left = false), 100);
          }
        } else if (deltaY < -minSwipeDistance) {
          // Swipe up - jump
          keysRef.current.jump = true;
          setTimeout(() => (keysRef.current.jump = false), 100);
        } else if (Math.abs(deltaX) < 15 && Math.abs(deltaY) < 15) {
          // Tap - use position for lane change or jump
          const third = canvasRect.width / 3;
          if (touchStartRef.current.x < third) {
            keysRef.current.left = true;
            setTimeout(() => (keysRef.current.left = false), 100);
          } else if (touchStartRef.current.x > third * 2) {
            keysRef.current.right = true;
            setTimeout(() => (keysRef.current.right = false), 100);
          } else {
            keysRef.current.jump = true;
            setTimeout(() => (keysRef.current.jump = false), 100);
          }
        }
      }
    },
    [gameState]
  );

  return {
    keysRef,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
  };
}
