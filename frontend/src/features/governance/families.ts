import { ChevronsRight, Landmark } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

const OPEN_BID_STAGES = new Set(['bid', 'resisted', 'agreed'])

export const GOVERNANCE: RecordFamily = {
  id: 'governance',
  section: 'section-governance',
  title: 'Governance',
  description:
    'How an organisation is ruled within: its decision body and how it votes, its quorum, its head and the rule that chooses the head, the term, the trust the body holds in its head and the course it follows; the seats on its body with the weight of each vote; the cliques that gather votes for a course, a head, a split or a merger; the bids it makes or meets; the research it pays for; and the insolvency cases it goes through.',
  icon: Landmark,
  tone: 'gold',
  empty:
    'This thing has no governing body. Factions, companies, holy orders, guilds, unions, parties and cults hold one; a being, a people, a realm, a world, a star or a god can sit on a body, own shares, bid for an organisation or be its creditor, and those rows show here.',
  tables: {
    org_governance: {
      create: 'org_governance:create',
      edit: 'org_governance:edit',
      remove: 'org_governance:delete',
    },
    org_seats: {
      create: 'org_seat:create',
      edit: 'org_seat:edit',
      remove: 'org_seat:delete',
    },
    org_cliques: {
      create: 'org_clique:create',
      edit: 'org_clique:edit',
      remove: 'org_clique:delete',
    },
    org_mergers: {
      create: 'org_merger:create',
      edit: 'org_merger:edit',
      remove: 'org_merger:delete',
      step: {
        action: 'org_merger:advance',
        label: 'Carry this bid a stage further',
        field: 'record_id',
        icon: ChevronsRight,
        ready: (values) =>
          OPEN_BID_STAGES.has(String(values.stage))
            ? null
            : 'Only a bid still open can be carried a stage further',
      },
    },
    org_research: {
      create: 'org_research:create',
      edit: 'org_research:edit',
      remove: 'org_research:delete',
    },
    insolvency_cases: {
      create: 'insolvency_case:create',
      edit: 'insolvency_case:edit',
      remove: 'insolvency_case:delete',
    },
  },
}
