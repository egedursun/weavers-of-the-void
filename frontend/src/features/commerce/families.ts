import { Store } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const COMMERCE: RecordFamily = {
  id: 'commerce',
  section: 'section-commerce',
  title: 'Commerce',
  description:
    'The shops of a town or a keeper with their form, margin, stock and credit, and the goods each carries; the tiers through which goods pass at a market with their holders, shares and margins; the promotions a holder runs with their medium, reach, cost and how true their claims are; and the leases of things between owners and lessees with their rent, term, upkeep and what follows a default.',
  icon: Store,
  tone: 'gold',
  empty:
    'Nothing of commerce is kept for this thing yet. Towns hold shops and tiers of supply, keepers hold shops, holders run promotions and owners and lessees hold leases; gods, worlds and stars trade through those who hold such things.',
  tables: {
    shops: { create: 'shop:create', edit: 'shop:edit', remove: 'shop:delete' },
    shop_goods: {
      create: 'shop_good:create',
      edit: 'shop_good:edit',
      remove: 'shop_good:delete',
    },
    supply_tiers: {
      create: 'supply_tier:create',
      edit: 'supply_tier:edit',
      remove: 'supply_tier:delete',
    },
    promotions: {
      create: 'promotion:create',
      edit: 'promotion:edit',
      remove: 'promotion:delete',
    },
    leases: {
      create: 'lease:create',
      edit: 'lease:edit',
      remove: 'lease:delete',
    },
  },
}
