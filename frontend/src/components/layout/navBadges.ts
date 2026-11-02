import { createContext, useContext } from 'react'

export type NavBadge = { count: number; tone: 'primary' | 'warning' | 'info' }

export const NavBadgeContext = createContext<Record<string, NavBadge>>({})

export function useNavBadge(id: string): NavBadge | null {
  const badge = useContext(NavBadgeContext)[id]
  return badge && badge.count > 0 ? badge : null
}
