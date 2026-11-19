import { Snowflake } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const WATER_AND_ICE: RecordFamily = {
  id: 'water-and-ice',
  section: 'section-water-and-ice',
  title: 'Water, ice and sediment',
  description:
    "The ice on a land's seas, rivers and ground, its snow and glaciers, the sediment its rivers and winds carry, the form of its coast and the warmth a town makes for itself. Ice closes waters to ships and opens roads across them; thawing ground brings works down and gives up what it held; little snow means a dry summer downstream; sediment builds deltas and silts harbours; coasts build out or wear away; crowded towns warm their own air and feed disease. A held value stays where the god set it.",
  icon: Snowflake,
  tone: 'verdigris',
  empty:
    'No ice, sediment or coast is kept here. Only a land has ice, a coast and flows of sediment, and only a land or a town has a local climate; every other thing shows this section so a god can see that, and may still set the water and ice of any land.',
  tables: {
    region_cryosphere: {
      create: 'region_cryosphere:create',
      edit: 'region_cryosphere:edit',
      remove: 'region_cryosphere:delete',
    },
    sediment_flows: {
      create: 'sediment_flow:create',
      edit: 'sediment_flow:edit',
      remove: 'sediment_flow:delete',
    },
    coasts: {
      create: 'coast:create',
      edit: 'coast:edit',
      remove: 'coast:delete',
    },
    local_climates: {
      create: 'local_climate:create',
      edit: 'local_climate:edit',
      remove: 'local_climate:delete',
    },
  },
}
