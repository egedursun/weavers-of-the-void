import { Microscope } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const DISEASE_AGENTS: RecordFamily = {
  id: 'disease-agents',
  section: 'section-disease-agents',
  title: 'Agents of disease',
  description:
    "What a disease is: a living agent, a poison, a lack, a spirit or a curse, how long it lives outside a body, in water, soil and cold, and which beasts keep it between outbreaks. A cure works only on the kind of thing the disease is: a rite does nothing against a living agent unless the world's laws let faith heal, and a cure used too often breeds resistance. A held value stays where the god set it.",
  icon: Microscope,
  tone: 'gold',
  empty:
    'No agent of disease is kept here. Only a disease has an agent; every other thing shows this section so a god can see that, and may still set what any disease is.',
  tables: {
    disease_agents: {
      create: 'disease_agent:create',
      edit: 'disease_agent:edit',
      remove: 'disease_agent:delete',
    },
  },
}
