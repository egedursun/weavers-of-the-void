import {
  CloudLightning,
  Flame,
  Mountain,
  Orbit,
  Sparkles,
  Waves,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const WAVE_ORIGIN: Record<Schema['WaveOrigin'], Named> = {
  quake: { label: 'A quake', icon: Waves, tone: 'danger' },
  eruption: { label: 'An eruption', icon: Flame, tone: 'danger' },
  slide: { label: 'A slide into the sea', icon: Mountain, tone: 'warning' },
  storm: { label: 'A storm surge', icon: CloudLightning, tone: 'warning' },
  impact: { label: 'A blow from the sky', icon: Orbit, tone: 'danger' },
  divine: { label: 'A god', icon: Sparkles, tone: 'verdigris' },
}
