import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export type SealLedger = {
  openedThrough: number
  turned: number[]
}

type CardSeals = SealLedger & {
  open: (id: number) => void
  seal: (id: number) => void
  openAll: (latest: number) => void
  sealAll: () => void
}

export const CARD_SEALS_KEY = 'aerona.cards.seals'

export function sealedIn(ledger: SealLedger, id: number): boolean {
  const opened = id <= ledger.openedThrough
  return ledger.turned.includes(id) ? opened : !opened
}

function turnedTo(ledger: SealLedger, id: number, sealed: boolean): number[] {
  const rest = ledger.turned.filter((item) => item !== id)
  const byDefault = id > ledger.openedThrough
  return byDefault === sealed ? rest : [...rest, id]
}

export function everyOpen(ledger: SealLedger, latest: number | null): boolean {
  if (latest === null) return true
  return (
    ledger.openedThrough >= latest &&
    !ledger.turned.some((id) => id <= ledger.openedThrough)
  )
}

export function everySealed(ledger: SealLedger): boolean {
  return ledger.openedThrough === 0 && ledger.turned.length === 0
}

export const useCardSeals = create<CardSeals>()(
  persist(
    (set) => ({
      openedThrough: 0,
      turned: [],
      open: (id) => set((state) => ({ turned: turnedTo(state, id, false) })),
      seal: (id) => set((state) => ({ turned: turnedTo(state, id, true) })),
      openAll: (latest) => set({ openedThrough: latest, turned: [] }),
      sealAll: () => set({ openedThrough: 0, turned: [] }),
    }),
    {
      name: CARD_SEALS_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: ({ openedThrough, turned }) => ({ openedThrough, turned }),
    }
  )
)

export function useSealed(id: number): boolean {
  return useCardSeals((state) => sealedIn(state, id))
}
