import { create } from 'zustand'

export type FontSize = 'small' | 'medium' | 'large'

interface FontSizeState {
  fontSize: FontSize
  setFontSize: (size: FontSize) => void
}

const FONT_SIZE_KEY = 'app-font-size'

function getStoredFontSize(): FontSize {
  const stored = localStorage.getItem(FONT_SIZE_KEY)
  if (stored === 'small' || stored === 'medium' || stored === 'large') {
    return stored
  }
  return 'medium'
}

function applyFontSize(size: FontSize) {
  const root = document.documentElement
  const sizeMap: Record<FontSize, string> = {
    small: '14px',
    medium: '16px',
    large: '18px',
  }
  root.style.setProperty('--font-size-base', sizeMap[size])
  root.setAttribute('data-font-size', size)
}

export const useFontSizeStore = create<FontSizeState>((set) => {
  const initial = getStoredFontSize()
  if (typeof document !== 'undefined') {
    applyFontSize(initial)
  }

  return {
    fontSize: initial,
    setFontSize: (size) => {
      localStorage.setItem(FONT_SIZE_KEY, size)
      applyFontSize(size)
      set({ fontSize: size })
    },
  }
})
