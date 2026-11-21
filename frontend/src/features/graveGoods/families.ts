import { Gem } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const GRAVE_GOODS: RecordFamily = {
  id: 'grave_good',
  section: 'section-grave-goods',
  title: 'Grave goods',
  description:
    'What was laid with the dead: the grave they lie in, the custom that kept them, the things and the worth of goods placed, the guard over them, and when the grave was robbed or found and by whom.',
  icon: Gem,
  tone: 'warning',
  empty:
    'No goods lie in a grave here. A people that keeps its dead in a place lays a share of their goods with them by rank; a people whose custom leaves no place, such as those who burn, expose or release their dead, keeps no graves to fill.',
  tables: {
    grave_goods: {
      create: 'grave_good:create',
      edit: 'grave_good:edit',
      remove: 'grave_good:delete',
    },
  },
}
