import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export const WILL_VIEWS = ['chat', 'writings', 'sessions'] as const

export type WillView = (typeof WILL_VIEWS)[number]

export const PANEL_MIN_REM = 22
export const PANEL_MAX_REM = 78
export const PANEL_DEFAULT_REM = 42
export const PANEL_STEP_REM = 2

export const WILL_DOCK_KEY = 'aerona.divine-will'
const WIDER_PANEL_VERSION = 1
const WIDER_PANEL_SCALE = 1.5

type DockState = {
  open: boolean
  width: number
  view: WillView
  setOpen: (open: boolean) => void
  toggle: () => void
  setWidth: (width: number) => void
  setView: (view: WillView) => void
}

export function clampWidth(width: number): number {
  return Math.min(PANEL_MAX_REM, Math.max(PANEL_MIN_REM, width))
}

export function widened(stored: unknown): Partial<DockState> {
  if (typeof stored !== 'object' || stored === null) return {}
  const { width, view } = stored as { width?: unknown; view?: unknown }
  return {
    ...(typeof width === 'number'
      ? { width: clampWidth(width * WIDER_PANEL_SCALE) }
      : {}),
    ...(WILL_VIEWS.some((item) => item === view)
      ? { view: view as WillView }
      : {}),
  }
}

export const useWillDock = create<DockState>()(
  persist(
    (set) => ({
      open: false,
      width: PANEL_DEFAULT_REM,
      view: 'chat',
      setOpen: (open) => set({ open }),
      toggle: () => set((state) => ({ open: !state.open })),
      setWidth: (width) => set({ width: clampWidth(width) }),
      setView: (view) => set({ view }),
    }),
    {
      name: WILL_DOCK_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ width: state.width, view: state.view }),
      version: WIDER_PANEL_VERSION,
      migrate: (stored) => widened(stored),
    }
  )
)
