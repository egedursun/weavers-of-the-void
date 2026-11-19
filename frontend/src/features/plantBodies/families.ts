import { Sprout } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const PLANT_BODIES: RecordFamily = {
  id: 'plant-bodies',
  section: 'section-plant-bodies',
  title: 'Plant bodies',
  description:
    'The body of a plant: its form, the parts it grows and the good each part gives, how it spreads, how long it lives, how many months it grows and how long before its first harvest. Its parts become the goods its people gather; storms lay down tall forms and fires burn low ones; seeds carried by wind or beast take root in neighbouring lands and may crowd out what grows there; a plant sown widely enough is tamed. A held value stays where the god set it.',
  icon: Sprout,
  tone: 'success',
  empty:
    'No plant body is kept here. Only a plant or a plant-like kind of life has a body of roots, leaves and seeds; every other thing shows this section so a god can see that, and may still give any plant its body.',
  tables: {
    plant_anatomy: {
      create: 'plant_anatomy:create',
      edit: 'plant_anatomy:edit',
      remove: 'plant_anatomy:delete',
    },
    plant_parts: {
      create: 'plant_part:create',
      edit: 'plant_part:edit',
      remove: 'plant_part:delete',
    },
  },
}
