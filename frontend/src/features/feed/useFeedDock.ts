import { useMatches } from '@tanstack/react-router'
import { create } from 'zustand'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import { useFeedPreferences } from './feedStore'

const WIDE_QUERY = '(min-width: 90rem)'

type FeedOverlay = {
  open: boolean
  setOpen: (open: boolean) => void
}

export const useFeedOverlay = create<FeedOverlay>()((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
}))

export function useCanvasRoute(): boolean {
  return useMatches({
    select: (matches) => matches.at(-1)?.staticData.layout === 'canvas',
  })
}

export function useFeedDock() {
  const wide = useMediaQuery(WIDE_QUERY)
  const canvas = useCanvasRoute()
  const preference = useFeedPreferences((state) => state.open)
  const setPreference = useFeedPreferences((state) => state.setOpen)
  const overlay = useFeedOverlay((state) => state.open)
  const setOverlay = useFeedOverlay((state) => state.setOpen)
  const docked = wide && !canvas
  if (wide && canvas)
    return { wide, docked, open: overlay, setOpen: setOverlay }
  return { wide, docked, open: preference ?? wide, setOpen: setPreference }
}
