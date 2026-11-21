import { Crown, Feather, Landmark, ScrollText, Sparkles } from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { type Named } from '@/features/collective/labels'

type Schema = components['schemas']

export const PROTECTION_BASIS: Record<Schema['ProtectionBasis'], Named> = {
  law: { label: 'Protected by law', icon: Landmark, tone: 'info' },
  faith: { label: 'Protected by faith', icon: Sparkles, tone: 'gold' },
  custom: { label: 'Protected by custom', icon: Feather, tone: 'verdigris' },
  charter: { label: 'Protected by charter', icon: ScrollText, tone: 'info' },
  divine_decree: {
    label: 'Protected by divine decree',
    icon: Crown,
    tone: 'gold',
  },
}
