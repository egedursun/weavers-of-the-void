import { type ReactNode } from 'react'
import { AccessibilityProvider } from '@/context/AccessibilityProvider'
import { FontProvider } from '@/context/FontProvider'

export function Providers({ children }: { children: ReactNode }) {
  return (
    <FontProvider>
      <AccessibilityProvider>{children}</AccessibilityProvider>
    </FontProvider>
  )
}
