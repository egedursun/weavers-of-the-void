import { createContext, useContext } from 'react'

export type Collapsible = 'offcanvas' | 'icon' | 'none'
export type Variant = 'inset' | 'sidebar' | 'floating'

export const COLLAPSIBLES: readonly Collapsible[] = [
  'icon',
  'offcanvas',
  'none',
]
export const VARIANTS: readonly Variant[] = ['inset', 'sidebar', 'floating']

export type LayoutContextValue = {
  resetLayout: () => void
  defaultCollapsible: Collapsible
  collapsible: Collapsible
  setCollapsible: (collapsible: Collapsible) => void
  defaultVariant: Variant
  variant: Variant
  setVariant: (variant: Variant) => void
}

export const LayoutContext = createContext<LayoutContextValue | null>(null)

export function useLayout(): LayoutContextValue {
  const context = useContext(LayoutContext)
  if (!context)
    throw new Error('useLayout must be used within a LayoutProvider')
  return context
}
