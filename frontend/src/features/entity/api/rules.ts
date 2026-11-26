export { useRuleLookup } from '@/api/ruleValues'

export const RULE = {
  sanityClouding: 'cosmic_horror.clouding_threshold',
  sanityMadness: 'cosmic_horror.madness_threshold',
  priceScarcity: 'market.flow_price_gap_pct',
  pricePlenty: 'markets.price_floor_pct',
} as const
