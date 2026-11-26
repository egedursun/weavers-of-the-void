import { create } from 'zustand'

type ConnectStep = {
  open: boolean
  show: () => void
  finish: () => void
}

export const useConnectStep = create<ConnectStep>((set) => ({
  open: false,
  show: () => set({ open: true }),
  finish: () => set({ open: false }),
}))
