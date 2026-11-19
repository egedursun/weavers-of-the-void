import { Sun } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const DAILY_LIFE: RecordFamily = {
  id: 'daily-life',
  section: 'section-daily-life',
  title: 'Daily life',
  description:
    'How a people washes, grooms and keeps clean, who keeps which duty of a house, who serves in a household and on what terms, what free time goes to, and the distance, touch and posture a people keeps. Peoples hold care customs, norms of space and pursuits; beings hold the duties they keep, their service and pursuits of their own.',
  icon: Sun,
  tone: 'gold',
  empty:
    'Nothing of daily life is kept for this thing yet. Peoples and the members of households keep it; gods, worlds and stars keep no house, though any of them may be given a pursuit.',
  tables: {
    care_customs: {
      create: 'care_custom:create',
      edit: 'care_custom:edit',
      remove: 'care_custom:delete',
    },
    housework: {
      create: 'housework:create',
      edit: 'housework:edit',
      remove: 'housework:delete',
    },
    domestic_service: {
      create: 'domestic_service:create',
      edit: 'domestic_service:edit',
      remove: 'domestic_service:delete',
    },
    leisure_pursuits: {
      create: 'leisure_pursuit:create',
      edit: 'leisure_pursuit:edit',
      remove: 'leisure_pursuit:delete',
    },
    space_norms: {
      create: 'space_norm:create',
      edit: 'space_norm:edit',
      remove: 'space_norm:delete',
    },
  },
}
