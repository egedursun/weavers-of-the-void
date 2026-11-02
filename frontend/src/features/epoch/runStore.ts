import { type ServerEvent } from '@/realtime'
import { create } from 'zustand'
import { IDLE_RUN, type RunState, applyRunEvent } from './runModel'

type RunStore = RunState & {
  apply: (event: ServerEvent) => void
  reset: () => void
}

export const useEpochRun = create<RunStore>((set) => ({
  ...IDLE_RUN,
  apply: (event) => set((state) => applyRunEvent(state, event)),
  reset: () => set(IDLE_RUN),
}))
