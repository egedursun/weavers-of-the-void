import { IDLE_QUIET_MS } from '@/constants/ui'

const ACTIVITY_EVENTS = ['keydown', 'pointerdown', 'input', 'wheel'] as const

const waiting = new Map<string, () => void>()
let lastActivity = Number.NEGATIVE_INFINITY
let timer: ReturnType<typeof setTimeout> | null = null
let listening = false

export function noteActivity(at: number = Date.now()): void {
  lastActivity = at
}

export function isIdle(at: number = Date.now()): boolean {
  return at - lastActivity >= IDLE_QUIET_MS
}

export function pendingCount(): number {
  return waiting.size
}

function flush(): void {
  timer = null
  if (!isIdle()) {
    schedule()
    return
  }
  const runs = [...waiting.values()]
  waiting.clear()
  for (const run of runs) run()
}

function schedule(): void {
  if (timer !== null) clearTimeout(timer)
  const remaining = IDLE_QUIET_MS - (Date.now() - lastActivity)
  timer = setTimeout(flush, Math.max(remaining, 0) + 1)
}

export function listenForActivity(): void {
  if (listening || typeof window === 'undefined') return
  listening = true
  for (const name of ACTIVITY_EVENTS)
    window.addEventListener(name, () => noteActivity(), {
      capture: true,
      passive: true,
    })
}

export function whenIdle(key: string, run: () => void): void {
  listenForActivity()
  if (isIdle() && waiting.size === 0) {
    run()
    return
  }
  waiting.set(key, run)
  schedule()
}

export function resetIdleGate(): void {
  waiting.clear()
  if (timer !== null) clearTimeout(timer)
  timer = null
  lastActivity = Number.NEGATIVE_INFINITY
}
