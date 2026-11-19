import { Flag } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const YOUTH: RecordFamily = {
  id: 'youth',
  section: 'section-youth',
  title: 'Youth',
  description:
    'The years of youth among a people, where its youths spend them and their freedoms and duties; the youth groups of a town with their purpose, leader and standing; and their members.',
  icon: Flag,
  tone: 'gold',
  empty:
    'Nothing of youth is kept for this thing yet. Peoples hold the standing of youth, towns hold youth groups and beings belong to them; gods, worlds and stars have no youth among mortals.',
  tables: {
    youth_standing: {
      create: 'youth_standing:create',
      edit: 'youth_standing:edit',
      remove: 'youth_standing:delete',
    },
    youth_groups: {
      create: 'youth_group:create',
      edit: 'youth_group:edit',
      remove: 'youth_group:delete',
    },
    youth_group_members: {
      create: 'youth_group_member:create',
      edit: 'youth_group_member:edit',
      remove: 'youth_group_member:delete',
    },
  },
}
