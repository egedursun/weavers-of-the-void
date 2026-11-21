import { Crown } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const LEADER_CULTS: RecordFamily = {
  id: 'leader-cults',
  section: 'section-leader-cults',
  title: 'Cult of a leader',
  description:
    'The organised veneration of a living leader by those under them: whose cult it is and in which realm, who promotes it, the instruments it uses, its intensity and the sincerity of the public, and its fate once the leader dies, passed to an heir, faded, turned into a faith or torn down.',
  icon: Crown,
  tone: 'gold',
  empty:
    'No cult is raised here. Mortals and made minds who lead may be venerated in their lifetime, and their realm and promoters see the cult too; gods are worshipped through faith, not through a cult of this kind, and so show none.',
  tables: {
    leader_cults: {
      create: 'leader_cult:create',
      edit: 'leader_cult:edit',
      remove: 'leader_cult:delete',
    },
  },
}
