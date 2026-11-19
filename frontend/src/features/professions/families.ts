import { Scale } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const PROFESSIONS: RecordFamily = {
  id: 'professions',
  section: 'section-professions',
  title: 'Professed values',
  description:
    'The values a being professes, from honour and piety to freedom or tradition, and how far its deeds fall short of them. Each act against what it professes widens the gap, and the gap closes with time; a wide gap that others know of comes out, costing trust, standing and the followers who held that value, and is forgiven once it closes. A held value stays where the god set it.',
  icon: Scale,
  tone: 'gold',
  empty:
    'No professed value is kept here. Any being that holds values may profess them, from a mortal to a people, a faith, a god or the Creator; every thing shows this section so a god can set what it professes.',
  tables: {
    professions_of_value: {
      create: 'profession_of_value:create',
      edit: 'profession_of_value:edit',
      remove: 'profession_of_value:delete',
    },
  },
}
