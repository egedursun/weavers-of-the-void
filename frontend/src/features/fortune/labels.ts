import {
  CircleDashed,
  Clover,
  CloudRain,
  Gem,
  Globe,
  Hand,
  HandHeart,
  Handshake,
  MapPin,
  CalendarDays,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Sun,
  Unlink,
  Skull,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/entity/environment/labels'

type Schema = components['schemas']

export const FORTUNE_ICON = Clover

export const LAWS: Record<Schema['FortuneLaw'], Named> = {
  causes_only: { label: 'Causes only', icon: CircleDashed, tone: 'muted' },
  personal: { label: 'Each carries a streak', icon: Sparkles, tone: 'info' },
  divine: { label: 'Only the gods give it', icon: Sun, tone: 'gold' },
  belief_shaped: { label: 'Shaped by belief', icon: Globe, tone: 'verdigris' },
}

export const SOURCES: Record<Schema['FortuneSourceKind'], Named> = {
  blessing: { label: 'A blessing', icon: HandHeart, tone: 'success' },
  curse: { label: 'A curse', icon: Skull, tone: 'danger' },
  charm: { label: 'A charm', icon: Gem, tone: 'info' },
  divine_favour: { label: 'Divine favour', icon: Sun, tone: 'gold' },
  divine_disfavour: {
    label: 'Divine disfavour',
    icon: CloudRain,
    tone: 'danger',
  },
  fate_power: { label: 'A power over fate', icon: Sparkles, tone: 'gold' },
  natural_law: { label: 'A natural law', icon: ScrollText, tone: 'info' },
  oath_kept: { label: 'An oath kept', icon: Handshake, tone: 'success' },
  oath_broken: { label: 'An oath broken', icon: Unlink, tone: 'danger' },
  place: { label: 'A place', icon: MapPin, tone: 'info' },
  day: { label: 'A day', icon: CalendarDays, tone: 'info' },
  price_paid: { label: 'A price paid', icon: Hand, tone: 'warning' },
  care: { label: 'Care taken', icon: ShieldCheck, tone: 'success' },
}
