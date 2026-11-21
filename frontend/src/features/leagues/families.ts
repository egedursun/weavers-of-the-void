import { Handshake } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const LEAGUES: RecordFamily = {
  id: 'leagues',
  section: 'section-leagues',
  title: 'Leagues',
  description:
    'Standing bodies of realms: the charter of a league with its aims, seat, dues, vote basis, organs, treasury, depth, common tariff, the authority of its shared money and the treaty it grew from; the realms that stand in it as founders, members, observers, suspended or expelled, with the dues they paid, their veto and their defiance; and every decision laid before its organs, with the votes for and against and how it ended.',
  icon: Handshake,
  tone: 'gold',
  empty:
    'Nothing here stands in a league. Realms at peace bound by treaties found leagues; a league, its member realms, the subjects of its decisions and anyone who lays a motion before it show those rows here.',
  tables: {
    polity_leagues: {
      create: 'polity_league:create',
      edit: 'polity_league:edit',
      remove: 'polity_league:delete',
    },
    league_members: {
      create: 'league_member:create',
      edit: 'league_member:edit',
      remove: 'league_member:delete',
    },
    league_decisions: {
      create: 'league_decision:create',
      edit: 'league_decision:edit',
      remove: 'league_decision:delete',
    },
  },
}
