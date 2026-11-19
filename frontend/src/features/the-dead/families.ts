import { Hourglass } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const THE_DEAD: RecordFamily = {
  id: 'the-dead',
  section: 'section-the-dead',
  title: 'The dead',
  description:
    'The roles a people keeps in the work of the dead: each role, whether it is honoured, plain or avoided, its purity, the fee it asks, how many do the work and the association that holds it. What the people does with its remains is set with its funeral rite among its customs.',
  icon: Hourglass,
  tone: 'muted',
  empty:
    'No role in the work of the dead is kept here yet. Only a people keeps these roles, since the work belongs to a people and its customs; every other thing shows this section so a god can see that, and may still give any people a role.',
  tables: {
    death_work: {
      create: 'death_work:create',
      edit: 'death_work:edit',
      remove: 'death_work:delete',
    },
  },
}
