import { Sparkles } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const DIVINE_CONCEPTIONS: RecordFamily = {
  id: 'divine_conception',
  section: 'section-divine-conceptions',
  title: 'Conception of the divine',
  description:
    'How a faith holds the divine: how many gods it holds there are, how near they are, whether they are persons, forces or a principle, where the Creator stands, the strain its belief bears and since when it has held so; and how it reads each god, as true, as a servant, as a demon or as unknown.',
  icon: Sparkles,
  tone: 'verdigris',
  empty:
    'No conception of the divine is held here. Every faith conceives the divine from its tenets and the gods it worships, and reads each god of the world by it; a node that is no faith and no god holds none.',
  tables: {
    divine_conceptions: {
      create: 'divine_conception:create',
      edit: 'divine_conception:edit',
      remove: 'divine_conception:delete',
    },
    god_readings: {
      create: 'god_reading:create',
      edit: 'god_reading:edit',
      remove: 'god_reading:delete',
    },
  },
}
