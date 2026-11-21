import { Orbit } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const INTERWORLD: RecordFamily = {
  id: 'interworld',
  section: 'section-interworld',
  title: 'Between worlds',
  description:
    'Campaigns that carry hosts to other worlds, the hold on the space around a world, and peoples moving between worlds: each campaign with its attacker and defender, the worlds and way it crosses, its stage, carriers, forces and supply; each hold on an orbit with its holder, strength and challenger; each movement with its people, worlds, way, cause, reception and how many have gone and arrived.',
  icon: Orbit,
  tone: 'info',
  empty:
    'Nothing crosses between worlds here. Realms send campaigns along the ways between worlds, a world drawer shows who holds the space around it, and a settlement shows its people when they move to another world; worlds joined by no way keep this idle.',
  tables: {
    interworld_campaigns: {
      create: 'interworld_campaign:create',
      edit: 'interworld_campaign:edit',
      remove: 'interworld_campaign:delete',
    },
    orbital_control: {
      create: 'orbital_control:create',
      edit: 'orbital_control:edit',
      remove: 'orbital_control:delete',
    },
    interworld_migrations: {
      create: 'interworld_migration:create',
      edit: 'interworld_migration:edit',
      remove: 'interworld_migration:delete',
    },
  },
}
