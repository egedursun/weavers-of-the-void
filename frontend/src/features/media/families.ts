import { Newspaper } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const MEDIA: RecordFamily = {
  id: 'media',
  section: 'section-media',
  title: 'Media',
  description:
    'The recorded media a holder keeps with their form, fidelity, durability, copy cost, reach, technique and material; the outlets of a town or owner with their medium, reach, stance and lean, trust, funding, revenue, staff and whether they are censored; and the items each puts out with their kind, subject, slant, accuracy, reach and condition.',
  icon: Newspaper,
  tone: 'gold',
  empty:
    'Nothing of the media is kept for this thing yet. Peoples and realms hold recorded media, towns seat outlets, owners run them and items speak of any thing; gods, worlds and stars can be the subject of an item though they run no outlet themselves.',
  tables: {
    record_media: {
      create: 'record_medium:create',
      edit: 'record_medium:edit',
      remove: 'record_medium:delete',
    },
    media_outlets: {
      create: 'media_outlet:create',
      edit: 'media_outlet:edit',
      remove: 'media_outlet:delete',
    },
    media_items: {
      create: 'media_item:create',
      edit: 'media_item:edit',
      remove: 'media_item:delete',
    },
  },
}
