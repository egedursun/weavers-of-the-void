import { FastForward, Landmark } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

const OPEN_STAGES = new Set(['memory', 'movement', 'rising'])

export const RESTORATIONS: RecordFamily = {
  id: 'restorations',
  section: 'section-restorations',
  title: 'Restorations',
  description:
    'Movements that raise a fallen realm again under its old name, laws and rights: the fallen realm and who leads the movement, the old lands it seeks, its grounds, how strong its memory is, the stage it has reached and the realm it raised again.',
  icon: Landmark,
  tone: 'gold',
  empty:
    'No movement seeks to raise a fallen realm here. A realm that has fallen is remembered in accounts, titles and claims, and its old lands, its claimants and the realm raised in its place see such a movement too.',
  tables: {
    restorations: {
      create: 'restoration:create',
      edit: 'restoration:edit',
      remove: 'restoration:delete',
      step: {
        action: 'restoration:advance',
        label: 'Carry it to its next stage',
        field: 'record_id',
        icon: FastForward,
        ready: (values) =>
          OPEN_STAGES.has(String(values.stage))
            ? null
            : 'Only a restoration still under way can move on',
      },
    },
  },
}
