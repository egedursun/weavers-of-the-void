import { create } from 'zustand'

export type LivePhase = 'preparing' | 'writing' | 'called' | 'result'

export type LiveCall = {
  callId: string
  tool: string
  phase: LivePhase
  error: boolean
}

export type LiveExchange = {
  text: string
  calls: LiveCall[]
}

type PresenceState = {
  live: Record<number, LiveExchange>
  drafts: Record<number, string>
  appendText: (exchangeId: number, text: string) => void
  settleText: (exchangeId: number) => void
  trackCall: (
    exchangeId: number,
    call: Partial<LiveCall> & { callId: string }
  ) => void
  endLive: (exchangeId: number) => void
  setDraft: (nodeId: number, text: string) => void
}

const EMPTY_LIVE: LiveExchange = { text: '', calls: [] }

function liveOf(state: PresenceState, exchangeId: number): LiveExchange {
  return state.live[exchangeId] ?? EMPTY_LIVE
}

export const usePresence = create<PresenceState>()((set) => ({
  live: {},
  drafts: {},
  appendText: (exchangeId, text) =>
    set((state) => {
      const current = liveOf(state, exchangeId)
      return {
        live: {
          ...state.live,
          [exchangeId]: { ...current, text: current.text + text },
        },
      }
    }),
  settleText: (exchangeId) =>
    set((state) => ({
      live: {
        ...state.live,
        [exchangeId]: { ...liveOf(state, exchangeId), text: '' },
      },
    })),
  trackCall: (exchangeId, call) =>
    set((state) => {
      const current = liveOf(state, exchangeId)
      const known = current.calls.find((item) => item.callId === call.callId)
      const merged: LiveCall = {
        tool: '',
        phase: 'preparing',
        error: false,
        ...known,
        ...call,
      }
      const calls = known
        ? current.calls.map((item) =>
            item.callId === call.callId ? merged : item
          )
        : [...current.calls, merged]
      return {
        live: { ...state.live, [exchangeId]: { ...current, calls } },
      }
    }),
  endLive: (exchangeId) =>
    set((state) => {
      const rest = { ...state.live }
      delete rest[exchangeId]
      return { live: rest }
    }),
  setDraft: (nodeId, text) =>
    set((state) => ({ drafts: { ...state.drafts, [nodeId]: text } })),
}))
