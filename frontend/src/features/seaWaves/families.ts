import { Waves } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const SEA_WAVES: RecordFamily = {
  id: 'sea_wave',
  section: 'section-sea-waves',
  title: 'Sea waves',
  description:
    'Great waves a quake, an eruption, a slide, a storm, a blow from the sky or a god drove across a sea: where each rose and how strong it was; each coast it struck, how high and how soon, whether that coast was warned, how many died and whether the land was salted; and the warnings given on a coast and how long they hold.',
  icon: Waves,
  tone: 'info',
  empty:
    'No wave has risen or struck here and no coast here is warned. A world with seas of any kind sends waves across them when the ground shakes, a flank slides or a storm drives the water; a world without seas has none to send.',
  tables: {
    sea_waves: {
      create: 'sea_wave:create',
      edit: 'sea_wave:edit',
      remove: 'sea_wave:delete',
    },
    sea_wave_coasts: {
      create: 'sea_wave_coast:create',
      edit: 'sea_wave_coast:edit',
      remove: 'sea_wave_coast:delete',
    },
    wave_warnings: {
      create: 'wave_warning:create',
      edit: 'wave_warning:edit',
      remove: 'wave_warning:delete',
    },
  },
}
