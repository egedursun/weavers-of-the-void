import { Magnet } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const SPACE_WEATHER: RecordFamily = {
  id: 'space-weather',
  section: 'section-space-weather',
  title: 'Fields and space weather',
  description:
    "The magnetic shield of a world and the activity of a star. A star turns through its cycle and sends flares, storms and surges of its wind; a world's field and upper air turn them away, and what comes through silences its signals, makes its compasses err, spreads its auroras and harms those who live outside shelter. A field may turn over and leave its world weak for a while. A held value stays where the god set it.",
  icon: Magnet,
  tone: 'verdigris',
  empty:
    "No field or space weather is kept here. Only a world has a magnetic shield and only a star has a cycle of activity, so the storms that strike a world are kept on that world; every other thing shows this section so a god can see that, and may still set a world's shield or a star's cycle.",
  tables: {
    world_fields: {
      create: 'world_field:create',
      edit: 'world_field:edit',
      remove: 'world_field:delete',
    },
    star_activity: {
      create: 'star_activity:create',
      edit: 'star_activity:edit',
      remove: 'star_activity:delete',
    },
    space_weather_events: {
      create: 'space_weather_event:create',
      edit: 'space_weather_event:edit',
      remove: 'space_weather_event:delete',
    },
  },
}
