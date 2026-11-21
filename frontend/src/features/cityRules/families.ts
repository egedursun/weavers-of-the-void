import { Building, Scissors } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const CITY_RULES: RecordFamily = {
  id: 'city-rules',
  section: 'section-city-rules',
  title: 'City rules and services',
  description:
    'What a settlement rules for its own land, the services it keeps and the city it has grown into: each rule with its district, kind, values, maker, strength, enforcement and how widely it is evaded; each service with its provider, budget, cost, quality and the districts it reaches; each city grown from several settlements with its core, quarters, governance and the laws its core spread.',
  icon: Building,
  tone: 'info',
  empty:
    'This place keeps no rules for its land and no services, and has grown into no city. Settlements set rules and found services as they grow, and those grown close together with strong ties become one city; settlements without dwellings keep these idle.',
  tables: {
    land_use_rules: {
      create: 'land_use_rule:create',
      edit: 'land_use_rule:edit',
      remove: 'land_use_rule:delete',
    },
    municipal_services: {
      create: 'municipal_service:create',
      edit: 'municipal_service:edit',
      remove: 'municipal_service:delete',
    },
    conurbations: {
      create: 'conurbation:create',
      edit: 'conurbation:edit',
      remove: 'conurbation:delete',
      step: {
        action: 'conurbation:split',
        label: 'Split it into its settlements',
        field: 'record_id',
        icon: Scissors,
        ready: (values) =>
          values.split_epoch === null || values.split_epoch === undefined
            ? null
            : 'This city has already split apart',
      },
    },
  },
}
