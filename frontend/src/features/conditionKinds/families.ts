import { Stethoscope } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const CONDITION_KINDS: RecordFamily = {
  id: 'agentless_condition',
  section: 'section-condition-kinds',
  title: 'Conditions the body brings on',
  description:
    'The kinds of lasting condition that arise in this world without any sickness to carry them: what brings each on, the body system it touches, the condition it shows as, whether it stays, worsens or comes and goes, the share of a life span after which it may come, its first severity and how often it comes beside the others.',
  icon: Stethoscope,
  tone: 'warning',
  empty:
    'No kind of condition is named here. Each world keeps its own list of the conditions that age, diet, foul air, water or soil, inheritance, strain and old wounds bring on, and the list is drawn up the first time the world turns.',
  tables: {
    agentless_conditions: {
      create: 'agentless_condition:create',
      edit: 'agentless_condition:edit',
      remove: 'agentless_condition:delete',
    },
  },
}
