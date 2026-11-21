import { Siren } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const OCCUPATION: RecordFamily = {
  id: 'occupation',
  section: 'section-occupation',
  title: 'Occupation',
  description:
    'How an occupier rules a land it holds: the rule it is under and the realm it was taken from, its administrators and the laws imposed on it, what the occupier takes in taxes, levies and labour, the settlers it brings, those who serve it and how exposed they are, and the measures pressed on the people, until liberation or annexation ends it.',
  icon: Siren,
  tone: 'danger',
  empty:
    'No occupation touches this. Lands an army holds are ruled under a regime, and the occupier, the realm the land was taken from, those who serve the occupier and the places it presses see it too.',
  tables: {
    occupation_regimes: {
      create: 'occupation_regime:create',
      edit: 'occupation_regime:edit',
      remove: 'occupation_regime:delete',
    },
    collaborations: {
      create: 'collaboration:create',
      edit: 'collaboration:edit',
      remove: 'collaboration:delete',
    },
    occupation_measures: {
      create: 'occupation_measure:create',
      edit: 'occupation_measure:edit',
      remove: 'occupation_measure:delete',
    },
  },
}
