import { BookOpenCheck } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const FOLK_KNOWLEDGE: RecordFamily = {
  id: 'folk_knowledge',
  section: 'section-folk_knowledge',
  title: 'What they know',
  description:
    'What a people knows of weather, sky, matter, land, waters, plants, animals, the body, illness, the mind, society, number and time: how deep and how accurate it is, who holds it and how it is passed on; and the classes it names in each domain, the world kind each class groups and what the people take it for.',
  icon: BookOpenCheck,
  tone: 'verdigris',
  empty:
    'No knowledge is kept for this thing yet. Peoples hold what they know and the classes they name; species, illnesses, materials, regions, worlds and stars appear here when a people names them, and gods hold no folk knowledge of their own.',
  tables: {
    folk_knowledge: {
      create: 'folk_knowledge:create',
      edit: 'folk_knowledge:edit',
      remove: 'folk_knowledge:delete',
    },
    folk_classes: {
      create: 'folk_class:create',
      edit: 'folk_class:edit',
      remove: 'folk_class:delete',
    },
  },
}
