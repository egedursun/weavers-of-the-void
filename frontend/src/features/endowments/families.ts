import { Landmark } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const ENDOWMENTS: RecordFamily = {
  id: 'endowments',
  section: 'section-endowments',
  title: 'Endowments',
  description:
    'Endowments founded by this thing or serving it: their founder, beneficiary and trustee, purpose, capital and what it is held in, the income it yields each epoch, what the trustee has kept back, its terms, whether a law shelters it, and whether it serves, is captured, confiscated or ended.',
  icon: Landmark,
  tone: 'gold',
  empty:
    'No endowment is kept for this thing yet. Beings, peoples, realms and gods found endowments; towns, buildings, peoples and beings are served by them; worlds and stars hold none, though a god may found one for anything.',
  tables: {
    endowments: {
      create: 'endowment:create',
      edit: 'endowment:edit',
      remove: 'endowment:delete',
    },
  },
}
