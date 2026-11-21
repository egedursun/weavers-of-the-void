import { Landmark } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const MONEY_POLICY: RecordFamily = {
  id: 'money-policy',
  section: 'section-money-policy',
  title: 'Money',
  description:
    'The authorities that issue a currency on purpose: who holds each one and how far it stands apart from rulers, its aim, the policy rate it sets and the rate lenders feel now, the reserves it keeps and what it asks of banks, the currency or good it is pegged to and whether it saves failing banks; with the history of its rate, supply and trust each epoch.',
  icon: Landmark,
  tone: 'gold',
  empty:
    'No authority issues money here. A world without money shows this as idle; a currency, its issuer and whoever holds its authority, a ruler, an office, a temple, a bank, a company or a council, show their authority here once money is minted.',
  tables: {
    monetary_authorities: {
      create: 'monetary_authority:create',
      edit: 'monetary_authority:edit',
      remove: 'monetary_authority:delete',
    },
  },
}
