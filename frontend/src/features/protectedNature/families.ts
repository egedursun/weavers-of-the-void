import { TreePine } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const PROTECTED_NATURE: RecordFamily = {
  id: 'protected-nature',
  section: 'section-protected-nature',
  title: 'Protection',
  description:
    'Land, waters and living kinds kept for their own sake: each protected land with its site, protector, right, the uses it bars, its wardens, strength and poaching; each protected kind with its holder, right and measures, and whether it has recovered; each movement for the wild with its aims and the support of each class.',
  icon: TreePine,
  tone: 'verdigris',
  empty:
    'Nothing here is protected. Realms, faiths, communities and movements protect lands and living kinds where loss, faith or knowledge moves them; the protected lands, the kinds and those who protect them see it here, and worlds without life keep this idle.',
  tables: {
    protected_areas: {
      create: 'protected_area:create',
      edit: 'protected_area:edit',
      remove: 'protected_area:delete',
    },
    species_protections: {
      create: 'species_protection:create',
      edit: 'species_protection:edit',
      remove: 'species_protection:delete',
    },
    conservation_movements: {
      create: 'conservation_movement:create',
      edit: 'conservation_movement:edit',
      remove: 'conservation_movement:delete',
    },
  },
}
