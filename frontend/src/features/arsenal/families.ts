import { Radiation } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const ARSENAL: RecordFamily = {
  id: 'arsenal',
  section: 'section-arsenal',
  title: 'Arsenal and remnants of war',
  description:
    'Weapons whose harm reaches a whole settlement, region or world, the postures that hold rivals back, and what wars leave in the land: each weapon with its harm, reach, stage, count, readiness and the rivals who have seen it; each posture with its holder, toward whom and how credible it is; each remnant with its land or orbit, density, decay, the war or weapon that left it and how much of it is cleared.',
  icon: Radiation,
  tone: 'danger',
  empty:
    'No weapon of mass harm, posture or remnant of war touches this. A realm, an organisation, a faith or a league may hold an arsenal, and regions and worlds carry what wars leave behind; others see the arsenals aimed at them and the remnants in their land.',
  tables: {
    mass_weapons: {
      create: 'mass_weapon:create',
      edit: 'mass_weapon:edit',
      remove: 'mass_weapon:delete',
    },
    deterrence_postures: {
      create: 'deterrence_posture:create',
      edit: 'deterrence_posture:edit',
      remove: 'deterrence_posture:delete',
    },
    war_remnants: {
      create: 'war_remnant:create',
      edit: 'war_remnant:edit',
      remove: 'war_remnant:delete',
    },
  },
}
