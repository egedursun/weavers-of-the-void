import { createContext, useContext } from 'react'

export const TEXT_SIZES = ['default', 'large', 'larger'] as const
export const CONTRASTS = ['default', 'high'] as const
export const MOTIONS = ['system', 'reduce'] as const

export type TextSize = (typeof TEXT_SIZES)[number]
export type Contrast = (typeof CONTRASTS)[number]
export type Motion = (typeof MOTIONS)[number]

export type AccessibilityContextValue = {
  textSize: TextSize
  contrast: Contrast
  motion: Motion
  setTextSize: (value: TextSize) => void
  setContrast: (value: Contrast) => void
  setMotion: (value: Motion) => void
  resetAccessibility: () => void
}

export const AccessibilityContext =
  createContext<AccessibilityContextValue | null>(null)

export function useAccessibility(): AccessibilityContextValue {
  const context = useContext(AccessibilityContext)
  if (!context)
    throw new Error(
      'useAccessibility must be used within an AccessibilityProvider'
    )
  return context
}
