import { Layers } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const DEEP_WORLD: RecordFamily = {
  id: 'deep-world',
  section: 'section-deep-world',
  title: 'The world below',
  description:
    'The cells beneath this land, the passages that join them and what each polity knows of them. Make, reshape or take away any cell or passage; a cell taken away moves those in it to the level above. A held value stays where the god set it.',
  icon: Layers,
  tone: 'gold',
  empty:
    'Nothing is kept below this thing yet. A god may still make a cell beneath any land, open a passage or set what a polity knows.',
  tables: {
    region_underground: {
      create: 'deep_cell:create',
      edit: 'deep_cell:edit',
      remove: 'deep_cell:delete',
    },
    deep_passages: {
      create: 'deep_passage:create',
      edit: 'deep_passage:edit',
      remove: 'deep_passage:delete',
    },
    polity_deep_knowledge: {
      create: 'deep_knowledge:set',
      edit: 'record_row:edit',
      remove: 'deep_knowledge:delete',
    },
  },
}
