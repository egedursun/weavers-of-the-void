import { useMemo, useState } from 'react'
import { getCookie, setCookie } from '@/lib/cookies'
import {
  COLLAPSIBLES,
  type Collapsible,
  LayoutContext,
  VARIANTS,
  type Variant,
} from './layoutContext'

const COLLAPSIBLE_COOKIE_NAME = 'aerona-sidebar-collapse'
const VARIANT_COOKIE_NAME = 'aerona-sidebar-variant'
const LAYOUT_COOKIE_MAX_AGE = 60 * 60 * 24 * 365

const DEFAULT_VARIANT: Variant = 'inset'
const DEFAULT_COLLAPSIBLE: Collapsible = 'icon'

export function LayoutProvider({ children }: { children: React.ReactNode }) {
  const [collapsible, setCollapsibleState] = useState<Collapsible>(
    () =>
      COLLAPSIBLES.find(
        (item) => item === getCookie(COLLAPSIBLE_COOKIE_NAME)
      ) ?? DEFAULT_COLLAPSIBLE
  )
  const [variant, setVariantState] = useState<Variant>(
    () =>
      VARIANTS.find((item) => item === getCookie(VARIANT_COOKIE_NAME)) ??
      DEFAULT_VARIANT
  )

  const value = useMemo(() => {
    const setCollapsible = (next: Collapsible) => {
      setCollapsibleState(next)
      setCookie(COLLAPSIBLE_COOKIE_NAME, next, LAYOUT_COOKIE_MAX_AGE)
    }
    const setVariant = (next: Variant) => {
      setVariantState(next)
      setCookie(VARIANT_COOKIE_NAME, next, LAYOUT_COOKIE_MAX_AGE)
    }
    return {
      resetLayout: () => {
        setCollapsible(DEFAULT_COLLAPSIBLE)
        setVariant(DEFAULT_VARIANT)
      },
      defaultCollapsible: DEFAULT_COLLAPSIBLE,
      collapsible,
      setCollapsible,
      defaultVariant: DEFAULT_VARIANT,
      variant,
      setVariant,
    }
  }, [collapsible, variant])

  return <LayoutContext value={value}>{children}</LayoutContext>
}
