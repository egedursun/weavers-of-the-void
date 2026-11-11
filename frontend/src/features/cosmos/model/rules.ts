import { useMemo } from 'react'
import { type RuleValue, type TravelMethod, useCosmosRules } from '../api'

export const RULE = {
  createWorld: 'balance.create_world',
  igniteStar: 'cosmic_costs.ignite_star',
  createGalaxy: 'cosmic_costs.create_galaxy',
  createCluster: 'cosmic_costs.create_cluster',
  createDimension: 'cosmic_costs.create_dimension',
  sealGate: 'cosmic_costs.seal_gate',
  cleanseLeak: 'cosmic_costs.cleanse_leak',
  forgetWorld: 'cosmic_costs.forget_world',
  skyEvent: 'cosmic_costs.sky_event',
  rekindleStar: 'cosmic_costs.rekindle_dead_star',
  extinguishStar: 'cosmic_costs.extinguish_star',
  extinguishLeak: 'pantheon.extinguish_leak',
  extinguishFertility: 'pantheon.extinguish_fertility_loss',
  extinguishDoom: 'pantheon.extinguish_star_apocalypse',
  legendaryQuest: 'cosmic_costs.legendary_expedition',
  severCost: 'beyond.sever_route_cost',
  stitchCost: 'beyond.reopen_route_cost',
  severEpochs: 'beyond.sever_route_epochs',
  revealCost: 'travel.reveal_route_cost',
  alignmentPeriod: 'travel.alignment_period',
  expeditionBase: 'travel.expedition_base_pct',
  expeditionMinPopulation: 'travel.expedition_min_population',
  worldWrathCost: 'god_power.world_wrath_cost',
  worldWrathSeverity: 'god_power.world_wrath_severity',
  cleanseAmount: 'pantheon.cleanse_leak_amount',
  rekindleBrightness: 'god_hand.rekindle_brightness',
  rekindleLeak: 'god_hand.rekindle_leak_drain',
  voyagePercent: 'god_hand.decree_expedition_pct',
  voyageMaxPercent: 'god_hand.decree_expedition_max_pct',
  climateEpochs: 'god_hand.decree_climate_epochs',
  climateMaxEpochs: 'god_hand.decree_climate_max_epochs',
  mortalAgentsCap: 'god_hand.mortal_agents_per_world_cap',
  leakWarning: 'cosmic_horror.repair_threshold',
  leakDanger: 'cosmic_horror.outer_being_threshold',
  explorationCap: 'exploration.per_epoch_cap',
  explorationBase: 'exploration.base_chance',
  crowdedPerRegion: 'exploration.crowded_communities_per_region',
  routeSearchCap: 'exploration.route_search_cap',
  stormEpochs: 'sky.god_storm_epochs',
  inspirationMax: 'god_actions.inspiration_max_chars',
} as const

export type RuleName = keyof typeof RULE

export type RuleBook = {
  ready: boolean
  get: (name: RuleName) => number | undefined
  path: (path: string) => number | undefined
  methodDuration: (method: TravelMethod) => number | undefined
  methodDanger: (method: TravelMethod) => number | undefined
}

export function buildRuleBook(rules: RuleValue[] | undefined): RuleBook {
  const values = new Map<string, number>()
  for (const item of rules ?? [])
    values.set(`${item.namespace}.${item.key}`, item.value)
  const path = (key: string) => values.get(key)
  return {
    ready: rules !== undefined,
    get: (name) => path(RULE[name]),
    path,
    methodDuration: (method) => path(`travel_methods.${method}_duration`),
    methodDanger: (method) => path(`travel_methods.${method}_danger`),
  }
}

export function useRuleBook(): RuleBook {
  const { data } = useCosmosRules()
  return useMemo(() => buildRuleBook(data), [data])
}

export function ruleText(value: number | undefined): string {
  return value === undefined ? '…' : String(value)
}
