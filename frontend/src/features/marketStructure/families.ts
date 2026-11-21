import { ChartPie } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const MARKET_STRUCTURE: RecordFamily = {
  id: 'market-structure',
  section: 'section-market-structure',
  title: 'Market structure',
  description:
    'Who sells each good in a market and with what share, the share of small sellers too many to name, how concentrated it is, whether it has many sellers, few, one, one buyer or few buyers, and the barriers that keep newcomers out with their strength; the compacts that bind sellers with their aim, terms, secrecy and discipline; and the price wars fought in it with their cut, losses and outcome.',
  icon: ChartPie,
  tone: 'gold',
  empty:
    'No market structure is kept for this thing. Towns hold the structure of each good their market trades; organisations and beings that sell there, join a compact or wage a price war see those rows here; worlds, stars and gods hold none, though a god may set one down for any market.',
  tables: {
    market_structures: {
      create: 'market_structure:create',
      edit: 'market_structure:edit',
      remove: 'market_structure:delete',
    },
    cartels: {
      create: 'cartel:create',
      edit: 'cartel:edit',
      remove: 'cartel:delete',
    },
    price_wars: {
      create: 'price_war:create',
      edit: 'price_war:edit',
      remove: 'price_war:delete',
    },
  },
}
