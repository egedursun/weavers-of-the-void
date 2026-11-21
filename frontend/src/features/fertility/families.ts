import { Baby } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const FERTILITY: RecordFamily = {
  id: 'fertility_means',
  section: 'section-fertility',
  title: 'Means of conception',
  description:
    'The ways a people prevents, seeks or ends conception: each means, whether it comes from folk knowledge, medicine, a rite or a power, how reliable and how risky it is, how the people hold it, and the share who use it; and each being who uses one, whether in the open or in secret, and whether that use has come to light.',
  icon: Baby,
  tone: 'info',
  empty:
    'No means of conception is known or used here. A people that conceives finds such means through folk knowledge and medicine and passes them along its trade; a people that does not conceive has none to find.',
  tables: {
    fertility_means: {
      create: 'fertility_means:create',
      edit: 'fertility_means:edit',
      remove: 'fertility_means:delete',
    },
    fertility_uses: {
      create: 'fertility_use:create',
      edit: 'fertility_use:edit',
      remove: 'fertility_use:delete',
    },
  },
}
