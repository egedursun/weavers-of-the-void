import { type FeedCategory } from './feedModel'

const TONE_SECONDS = 0.35
const TONE_GAIN = 0.05
const TONE_THROTTLE_MS = 400
const DRONE_GAIN = 0.03
const DRONE_FADE_SECONDS = 2
const DRONE_FILTER_HZ = 420
const LFO_HZ = 0.07
const LFO_DEPTH_HZ = 160
const SILENCE = 0.0001

const CATEGORY_TONE_HZ: Record<FeedCategory, number> = {
  voyage: 523.25,
  gate: 587.33,
  leak: 207.65,
  war: 164.81,
  disaster: 146.83,
  sky: 783.99,
  life: 659.25,
  civilization: 440,
  world: 392,
}

const DRONE_HZ = [55, 82.41, 110, 164.81]

type Drone = {
  gain: GainNode
  sources: OscillatorNode[]
}

let context: AudioContext | null = null
let drone: Drone | null = null
let lastTone = 0

function audio(): AudioContext | null {
  if (typeof window === 'undefined' || !('AudioContext' in window)) return null
  context ??= new AudioContext()
  if (context.state === 'suspended') void context.resume()
  return context
}

export function categoryTone(category: FeedCategory): number {
  return CATEGORY_TONE_HZ[category]
}

export function playTone(category: FeedCategory, force = false): void {
  const now = Date.now()
  if (!force && now - lastTone < TONE_THROTTLE_MS) return
  const ctx = audio()
  if (!ctx) return
  lastTone = now
  const oscillator = ctx.createOscillator()
  const gain = ctx.createGain()
  oscillator.type = 'sine'
  oscillator.frequency.value = CATEGORY_TONE_HZ[category]
  gain.gain.setValueAtTime(TONE_GAIN, ctx.currentTime)
  gain.gain.exponentialRampToValueAtTime(
    SILENCE,
    ctx.currentTime + TONE_SECONDS
  )
  oscillator.connect(gain).connect(ctx.destination)
  oscillator.start()
  oscillator.stop(ctx.currentTime + TONE_SECONDS)
}

export function startDrone(): void {
  if (drone) return
  const ctx = audio()
  if (!ctx) return
  const gain = ctx.createGain()
  const filter = ctx.createBiquadFilter()
  filter.type = 'lowpass'
  filter.frequency.value = DRONE_FILTER_HZ
  const lfo = ctx.createOscillator()
  const lfoGain = ctx.createGain()
  lfo.frequency.value = LFO_HZ
  lfoGain.gain.value = LFO_DEPTH_HZ
  lfo.connect(lfoGain).connect(filter.frequency)
  gain.gain.setValueAtTime(SILENCE, ctx.currentTime)
  gain.gain.linearRampToValueAtTime(
    DRONE_GAIN,
    ctx.currentTime + DRONE_FADE_SECONDS
  )
  filter.connect(gain).connect(ctx.destination)
  const sources = DRONE_HZ.map((frequency) => {
    const oscillator = ctx.createOscillator()
    oscillator.type = 'triangle'
    oscillator.frequency.value = frequency
    oscillator.connect(filter)
    oscillator.start()
    return oscillator
  })
  lfo.start()
  drone = { gain, sources: [...sources, lfo] }
}

export function stopDrone(): void {
  const ctx = context
  const current = drone
  if (!ctx || !current) return
  drone = null
  current.gain.gain.cancelScheduledValues(ctx.currentTime)
  current.gain.gain.setValueAtTime(current.gain.gain.value, ctx.currentTime)
  current.gain.gain.linearRampToValueAtTime(
    SILENCE,
    ctx.currentTime + DRONE_FADE_SECONDS
  )
  for (const source of current.sources)
    source.stop(ctx.currentTime + DRONE_FADE_SECONDS)
}
