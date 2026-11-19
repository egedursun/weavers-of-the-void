import { Baby } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const CHILDHOOD: RecordFamily = {
  id: 'childhood',
  section: 'section-childhood',
  title: 'Childhood',
  description:
    'How a people feeds, carries and tends its infants and when it weans them; the ages at which a child is named, counts as a person, works, answers to the law and may wed, with the share of child labour; the ways it raises children and what it raises them to be; and the way each school or tradition teaches.',
  icon: Baby,
  tone: 'gold',
  empty:
    'Nothing of childhood is kept for this thing yet. Peoples hold their infant care, the standing of their children and their upbringing, and schools and traditions hold a way of teaching; gods, worlds and stars are not raised as mortals are, though any of them may still be given a way of teaching.',
  tables: {
    infant_care: {
      create: 'infant_care:create',
      edit: 'infant_care:edit',
      remove: 'infant_care:delete',
    },
    child_standing: {
      create: 'child_standing:create',
      edit: 'child_standing:edit',
      remove: 'child_standing:delete',
    },
    socialization: {
      create: 'socialization:create',
      edit: 'socialization:edit',
      remove: 'socialization:delete',
    },
    pedagogy: {
      create: 'pedagogy:create',
      edit: 'pedagogy:edit',
      remove: 'pedagogy:delete',
    },
  },
}
