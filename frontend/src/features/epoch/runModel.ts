import { type ServerEvent } from '@/realtime'

const MILLISECONDS = 1000

export type RunPhase = {
  no: number
  total: number
  name: string
}

export type PhaseTiming = {
  name: string
  seconds: number
  failed: boolean
}

export type FinishedRun = {
  epoch: number
  newEpoch: number
  durationSeconds: number
  phases: PhaseTiming[]
  summary: Record<string, unknown>
  stoppedAtPhase: number | null
}

export type RunState = {
  active: boolean
  epoch: number | null
  startedAt: number | null
  resuming: boolean
  phase: RunPhase | null
  subtitle: string | null
  sonQueue: { no: number; total: number } | null
  stopRequested: boolean
  phases: PhaseTiming[]
  last: FinishedRun | null
}

export const IDLE_RUN: RunState = {
  active: false,
  epoch: null,
  startedAt: null,
  resuming: false,
  phase: null,
  subtitle: null,
  sonQueue: null,
  stopRequested: false,
  phases: [],
  last: null,
}

function stampOf(event: ServerEvent): number {
  const parsed = Date.parse(event.at)
  return Number.isNaN(parsed) ? Date.now() : parsed
}

function started(
  state: RunState,
  event: ServerEvent<'epoch.started'>
): RunState {
  return {
    ...IDLE_RUN,
    last: state.last,
    active: true,
    epoch: event.payload.epoch ?? null,
    startedAt: stampOf(event),
    resuming: event.payload.resuming,
    subtitle: event.payload.resuming ? 'Resuming where it stopped' : null,
  }
}

function ensureActive(state: RunState, event: ServerEvent): RunState {
  if (state.active) return state
  return {
    ...state,
    active: true,
    epoch: event.payload.epoch ?? state.epoch,
    startedAt: stampOf(event),
  }
}

function finished(
  state: RunState,
  event: ServerEvent<'epoch.finished'>
): RunState {
  return {
    ...IDLE_RUN,
    last: {
      epoch: event.payload.epoch ?? event.payload.new_epoch - 1,
      newEpoch: event.payload.new_epoch,
      durationSeconds: event.payload.duration_s,
      phases: state.phases,
      summary: event.payload.summary ?? {},
      stoppedAtPhase: null,
    },
  }
}

function stopped(
  state: RunState,
  event: ServerEvent<'epoch.stopped'>
): RunState {
  const elapsed =
    state.startedAt === null
      ? 0
      : Math.max(0, (stampOf(event) - state.startedAt) / MILLISECONDS)
  return {
    ...IDLE_RUN,
    last: {
      epoch: event.payload.epoch ?? state.epoch ?? 0,
      newEpoch: event.payload.epoch ?? state.epoch ?? 0,
      durationSeconds: elapsed,
      phases: state.phases,
      summary: {},
      stoppedAtPhase: event.payload.phase,
    },
  }
}

export function applyRunEvent(state: RunState, event: ServerEvent): RunState {
  switch (event.kind) {
    case 'epoch.started':
      return started(state, event)
    case 'epoch.resumed':
      return {
        ...ensureActive(state, event),
        resuming: true,
        subtitle: `Resuming from phase ${event.payload.phase}`,
      }
    case 'epoch.progress':
      return {
        ...ensureActive(state, event),
        phase: {
          no: event.payload.no,
          total: event.payload.total,
          name: event.payload.name,
        },
        subtitle: null,
      }
    case 'son.turn_queued':
      return {
        ...state,
        sonQueue: { no: event.payload.no, total: event.payload.total },
      }
    case 'son.turn_started':
      return state.active
        ? { ...state, subtitle: `${event.payload.son_name} is acting` }
        : state
    case 'mortal.turn_started':
      return state.active
        ? { ...state, subtitle: `${event.payload.name} takes a mortal turn` }
        : state
    case 'engine.phase':
      return state.active
        ? {
            ...state,
            subtitle: `World engine: ${event.payload.phase}`,
            phases:
              event.payload.seconds === null ||
              event.payload.seconds === undefined
                ? state.phases
                : [
                    ...state.phases,
                    {
                      name: event.payload.phase,
                      seconds: event.payload.seconds,
                      failed: Boolean(event.payload.error),
                    },
                  ],
          }
        : state
    case 'fate.step':
      return state.active ? { ...state, subtitle: event.payload.text } : state
    case 'epoch.stop_requested':
      return { ...state, stopRequested: true }
    case 'epoch.stopped':
      return stopped(state, event)
    case 'epoch.finished':
      return finished(state, event)
    default:
      return state
  }
}

export function phaseRatio(phase: RunPhase | null): number | null {
  if (!phase || phase.total <= 0) return null
  return Math.min(1, Math.max(0, phase.no / phase.total))
}

export const STALE_RUN_MS = 15_000

export function isStaleRun(
  state: RunState,
  serverRunning: boolean | undefined,
  checkedAt: number
): boolean {
  return (
    serverRunning === false &&
    state.active &&
    state.startedAt !== null &&
    checkedAt - state.startedAt > STALE_RUN_MS
  )
}
