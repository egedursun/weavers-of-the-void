import { Network } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const KIN: RecordFamily = {
  id: 'kin',
  section: 'section-kin-groups',
  title: 'Kin',
  description:
    'The duties a people binds between kin of each role, with their strength, and the kin groups beyond the household: their form, how members join, their head, council, exogamy and shared land and shrine. Peoples hold duties and kin groups; beings hold their memberships.',
  icon: Network,
  tone: 'gold',
  empty:
    'Nothing of kin is kept for this thing yet. Peoples hold duties and kin groups and beings belong to them; gods, worlds and stars stand outside mortal kinship, though a kin group may still be named after one.',
  tables: {
    kin_role_duties: {
      create: 'kin_role_duty:create',
      edit: 'kin_role_duty:edit',
      remove: 'kin_role_duty:delete',
    },
    kin_groups: {
      create: 'kin_group:create',
      edit: 'kin_group:edit',
      remove: 'kin_group:delete',
    },
    kin_group_members: {
      create: 'kin_group_member:create',
      edit: 'kin_group_member:edit',
      remove: 'kin_group_member:delete',
    },
  },
}
