import { HeartPulse } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const BODY_SYSTEMS: RecordFamily = {
  id: 'body-systems',
  section: 'section-body-systems',
  title: 'Body systems and sensitivities',
  description:
    "The systems that run a body, from breath and blood to nerves and bone, and what each bears: thin or heavy air, weight, cold, heat, poison, diet and sleep. A world past what a people's body bears weighs on its towns until the people grow used to it or the system gives way, and a colony is not founded where its settlers cannot live. A being sensitive to a food, a plant, a beast or a substance falls ill when it meets it. A held value stays where the god set it.",
  icon: HeartPulse,
  tone: 'gold',
  empty:
    'No body system or sensitivity is kept here. Only a people or a kind of life has body systems and only a being has sensitivities; every other thing shows this section so a god can see that, and may still give any body its systems.',
  tables: {
    body_systems: {
      create: 'body_system:create',
      edit: 'body_system:edit',
      remove: 'body_system:delete',
    },
    sensitivities: {
      create: 'sensitivity:create',
      edit: 'sensitivity:edit',
      remove: 'sensitivity:delete',
    },
  },
}
