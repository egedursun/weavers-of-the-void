import { Users } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const NUMBERS: RecordFamily = {
  id: 'numbers',
  section: 'section-numbers',
  title: 'Numbers',
  description:
    'The policy a realm, people, faith, company or town holds on its numbers: its aim, what it aims at, its strength and enforcement and the count it began from; and the instruments that serve it, each with its strength.',
  icon: Users,
  tone: 'gold',
  empty:
    'No policy on numbers is held by this thing yet. Realms, peoples, faiths, companies and towns hold policies; beings, worlds and stars hold none of their own, though a policy may aim at the people of a world.',
  tables: {
    population_policies: {
      create: 'population_policy:create',
      edit: 'population_policy:edit',
      remove: 'population_policy:delete',
    },
    population_instruments: {
      create: 'population_instrument:create',
      edit: 'population_instrument:edit',
      remove: 'population_instrument:delete',
    },
  },
}
