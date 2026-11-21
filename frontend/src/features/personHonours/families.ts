import { Medal } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const PERSON_HONOURS: RecordFamily = {
  id: 'honour_kind',
  section: 'section-person-honours',
  title: 'Honours',
  description:
    'The honours a realm, faith, order or god confers, with their rank, privileges, limit on holders, whether they pass to an heir and what they are still worth; and the honours held, by whom, conferred by whom, for which deed, whether bought, inherited or taken back.',
  icon: Medal,
  tone: 'warning',
  empty:
    'No honour is founded or held here. Realms, faiths, orders and gods found honours and confer them on those who serve them; worlds, stars and the Creator serve no one, so they hold none.',
  tables: {
    honour_kinds: {
      create: 'honour_kind:create',
      edit: 'honour_kind:edit',
      remove: 'honour_kind:delete',
    },
    honours_held: {
      create: 'honour_held:create',
      edit: 'honour_held:edit',
      remove: 'honour_held:delete',
    },
  },
}
