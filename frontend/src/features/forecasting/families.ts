import { CloudSun } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const FORECASTING: RecordFamily = {
  id: 'forecasting',
  section: 'section-forecasting',
  title: 'Forecasts and weather works',
  description:
    'How a people reads the coming weather, by sight, lore, almanac, instruments, observers, models, machines, powers or divination, and how truly; and the works that turn the weather of a land by rite, power, seeding, diversion, a made structure or living craft. A people that reads truly foresees a hard season and makes ready, unless it does not believe the reading; a weather work turns the land downwind the other way, and those harmed there may make the worker stop. A held value stays where the god set it.',
  icon: CloudSun,
  tone: 'verdigris',
  empty:
    'No forecast or weather work is kept here. Only a people reads the weather by its ways and only a land is worked; every other thing shows this section so a god can see that, and may still give any people its ways or set a work over any land.',
  tables: {
    observation_methods: {
      create: 'observation_method:create',
      edit: 'observation_method:edit',
      remove: 'observation_method:delete',
    },
    weather_works: {
      create: 'weather_work:create',
      edit: 'weather_work:edit',
      remove: 'weather_work:delete',
    },
  },
}
