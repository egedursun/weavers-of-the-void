import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { followUniverse, universePersisted } from '@/lib/universeStorage'
import { isMode } from './modes'
import { type DivineWillMode } from './types'

export type LiveToolPhase = 'preparing' | 'writing' | 'called' | 'result'

export type LiveTool = {
  callId: string
  tool: string
  phase: LiveToolPhase
  chars: number
  input: Record<string, unknown> | null
  error: boolean
}

export type LiveCycle = {
  text: string
  tools: LiveTool[]
}

export type ComposerSeed = {
  mode: DivineWillMode
  text: string
}

type WillState = {
  mode: DivineWillMode
  draft: string
  unread: number
  live: Record<number, LiveCycle>
  seed: ComposerSeed | null
  foresight: Record<number, number>
  setForesight: (forecastId: number, progress: number) => void
  setMode: (mode: DivineWillMode) => void
  setDraft: (draft: string) => void
  addUnread: () => void
  clearUnread: () => void
  appendText: (cycleId: number, text: string) => void
  settleText: (cycleId: number) => void
  trackTool: (
    cycleId: number,
    tool: Partial<LiveTool> & { callId: string }
  ) => void
  endLive: (cycleId: number) => void
  plant: (seed: ComposerSeed) => void
  takeSeed: () => ComposerSeed | null
}

const EMPTY_LIVE: LiveCycle = { text: '', tools: [] }

function liveOf(state: WillState, cycleId: number): LiveCycle {
  return state.live[cycleId] ?? EMPTY_LIVE
}

export const useWill = create<WillState>()(
  persist(
    (set, get) => ({
      mode: 'command',
      draft: '',
      unread: 0,
      live: {},
      seed: null,
      foresight: {},
      setForesight: (forecastId, progress) =>
        set((state) => ({
          foresight: { ...state.foresight, [forecastId]: progress },
        })),
      setMode: (mode) => set({ mode }),
      setDraft: (draft) => set({ draft }),
      addUnread: () => set((state) => ({ unread: state.unread + 1 })),
      clearUnread: () => set({ unread: 0 }),
      appendText: (cycleId, text) =>
        set((state) => {
          const current = liveOf(state, cycleId)
          return {
            live: {
              ...state.live,
              [cycleId]: { ...current, text: current.text + text },
            },
          }
        }),
      settleText: (cycleId) =>
        set((state) => ({
          live: {
            ...state.live,
            [cycleId]: { ...liveOf(state, cycleId), text: '' },
          },
        })),
      trackTool: (cycleId, tool) =>
        set((state) => {
          const current = liveOf(state, cycleId)
          const known = current.tools.find(
            (item) => item.callId === tool.callId
          )
          const merged: LiveTool = {
            tool: '',
            phase: 'preparing',
            chars: 0,
            input: null,
            error: false,
            ...known,
            ...tool,
          }
          const tools = known
            ? current.tools.map((item) =>
                item.callId === tool.callId ? merged : item
              )
            : [...current.tools, merged]
          return { live: { ...state.live, [cycleId]: { ...current, tools } } }
        }),
      endLive: (cycleId) =>
        set((state) => {
          const rest = { ...state.live }
          delete rest[cycleId]
          return { live: rest }
        }),
      plant: (seed) => set({ seed, mode: seed.mode }),
      takeSeed: () => {
        const seed = get().seed
        if (seed) set({ seed: null })
        return seed
      },
    }),
    {
      ...universePersisted<Pick<WillState, 'mode' | 'draft'>>(
        'aerona.divine-will.composer'
      ),
      partialize: (state) => ({ mode: state.mode, draft: state.draft }),
      merge: (persisted, current) => {
        const saved = (persisted ?? {}) as Partial<WillState>
        return {
          ...current,
          mode: isMode(saved.mode) ? saved.mode : current.mode,
          draft: typeof saved.draft === 'string' ? saved.draft : current.draft,
        }
      },
    }
  )
)

followUniverse(useWill)
