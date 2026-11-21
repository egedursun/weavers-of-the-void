import { Gavel } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const RECKONING: RecordFamily = {
  id: 'reckoning',
  section: 'section-reckoning',
  title: 'Reckoning',
  description:
    'What a new order does with the servants of the one it replaced: the reckoning of a realm with a fallen ruler or government, the resistance of the old servants and the pressure of their victims; its measures, from tribunals, inquiries and bars from office to amnesties, restitution, reparation, memorials and the opening of records, each with its scope, strength and stage; and the cases of the accused with the deeds the record names and how each ended.',
  icon: Gavel,
  tone: 'danger',
  empty:
    'No reckoning has been opened here. A realm whose rule changed hands reckons with the old regime, and its rulers, the fallen, the accused and those who opened it see the reckoning here.',
  tables: {
    reckonings: {
      create: 'reckoning:create',
      edit: 'reckoning:edit',
      remove: 'reckoning:delete',
    },
    reckoning_measures: {
      create: 'reckoning_measure:create',
      edit: 'reckoning_measure:edit',
      remove: 'reckoning_measure:delete',
    },
    reckoning_cases: {
      create: 'reckoning_case:create',
      edit: 'reckoning_case:edit',
      remove: 'reckoning_case:delete',
    },
  },
}
