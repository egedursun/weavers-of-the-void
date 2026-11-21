import { HeartHandshake } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const FAMILY: RecordFamily = {
  id: 'family',
  section: 'section-family',
  title: 'Family',
  description:
    'What happens between members of one family: the favour a parent shows a child, the rivalries between kin and their heat, those cast out and whether they were taken back, step kin joined by a later marriage and their standing, and the sway of a surviving elder, all kept for each house or household.',
  icon: HeartHandshake,
  tone: 'gold',
  empty:
    'No favour, rivalry, casting out, step kin or elder sway touches this. Houses and households form these as their members live together; kinds that keep no kin show none, and each member and house sees its own.',
  tables: {
    kin_dynamics: {
      create: 'kin_dynamic:create',
      edit: 'kin_dynamic:edit',
      remove: 'kin_dynamic:delete',
    },
    kin_favours: {
      create: 'kin_favour:create',
      edit: 'kin_favour:edit',
      remove: 'kin_favour:delete',
    },
    kin_rivalries: {
      create: 'kin_rivalry:create',
      edit: 'kin_rivalry:edit',
      remove: 'kin_rivalry:delete',
    },
    kin_disownings: {
      create: 'kin_disowning:create',
      edit: 'kin_disowning:edit',
      remove: 'kin_disowning:delete',
    },
    kin_blends: {
      create: 'kin_blend:create',
      edit: 'kin_blend:edit',
      remove: 'kin_blend:delete',
    },
    elder_sway: {
      create: 'elder_sway:create',
      edit: 'elder_sway:edit',
      remove: 'elder_sway:delete',
    },
  },
}
