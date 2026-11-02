import { create } from 'zustand'
import { type Rarity } from '@/constants/rarity'
import { type SonPublic } from './api'

export type RevealKind = 'new' | 'ascended' | 'genesis' | 'preview'

export type RevealItem = {
  key: string
  sonId: number
  kind: RevealKind
  rarity: Rarity | null
  preview?: SonPublic
}

type RevealQueue = {
  items: RevealItem[]
  genesisPending: boolean
  push: (items: RevealItem[]) => void
  next: () => void
  clear: () => void
  expectGenesis: () => void
  genesisDone: () => void
}

export const useRevealQueue = create<RevealQueue>((set) => ({
  items: [],
  genesisPending: false,
  push: (items) =>
    set((state) => ({
      items: [
        ...state.items,
        ...items.filter(
          (item) => !state.items.some((queued) => queued.key === item.key)
        ),
      ],
    })),
  next: () => set((state) => ({ items: state.items.slice(1) })),
  clear: () => set({ items: [] }),
  expectGenesis: () => set({ genesisPending: true }),
  genesisDone: () => set({ genesisPending: false }),
}))
