import { createContext, useContext } from 'react'
import type { fonts } from '@/config/fonts'

export type Font = (typeof fonts)[number]

export type FontContextValue = {
  font: Font
  setFont: (font: Font) => void
  resetFont: () => void
}

export const FontContext = createContext<FontContextValue | null>(null)

export function useFont(): FontContextValue {
  const context = useContext(FontContext)
  if (!context) throw new Error('useFont must be used within a FontProvider')
  return context
}
