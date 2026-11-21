import { PawPrint } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const CREATURE_GROUPS: RecordFamily = {
  id: 'creature_group',
  section: 'section-creature-groups',
  title: 'Creature groups',
  description:
    'The packs, herds, colonies, hives, troops and flocks of a land: their kind, the land and lair they hold, their form, numbers, leader and how long it has led, their ranks, the lands they range over, their rivals, their hunger, and what a god has turned them to and until when.',
  icon: PawPrint,
  tone: 'success',
  empty:
    'No group of creatures lives here. A kind that grows plentiful in a land gathers by its nature, in a pack, herd, colony, hive, troop or flock, or keeps a lone range; a world without fauna has none.',
  tables: {
    creature_groups: {
      create: 'creature_group:create',
      edit: 'creature_group:edit',
      remove: 'creature_group:delete',
    },
  },
}
