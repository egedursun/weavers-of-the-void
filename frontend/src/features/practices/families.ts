import { Sprout } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const PRACTICES: RecordFamily = {
  id: 'practices',
  section: 'section-practices',
  title: 'Practices',
  description:
    'The practices a community keeps, from its crafts and trades to its rites, laws and learning. Each one grows from what the community knows, holds and has built, and while it is kept it acts on the community: its order, health, wealth, learning and defence. A held level stays where the god set it.',
  icon: Sprout,
  tone: 'success',
  empty:
    'No practice is kept here yet. Only a people or a town keeps practices, since a practice lives in a community; every other thing shows this section so a god can see that, and may still give any community a practice.',
  tables: {
    facet_practices: {
      create: 'facet_practice:create',
      edit: 'facet_practice:edit',
      remove: 'facet_practice:delete',
    },
  },
}
