import { useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'
import { RULES_STALE_TIME_MS } from '@/constants/ui'

export function useRules() {
  return useQuery({
    queryKey: queryKeys.rules.all,
    queryFn: () => unwrap(api.GET('/api/rules')),
    staleTime: RULES_STALE_TIME_MS,
  })
}

export function useRuleLookup() {
  const rules = useRules()
  const table = useMemo(() => {
    const map = new Map<string, number>()
    for (const rule of rules.data ?? [])
      map.set(`${rule.namespace}.${rule.key}`, rule.value)
    return map
  }, [rules.data])
  return useCallback(
    (path: string): number | undefined => table.get(path),
    [table]
  )
}

export const RULE = {
  sanityClouding: 'cosmic_horror.clouding_threshold',
  sanityMadness: 'cosmic_horror.madness_threshold',
  priceScarcity: 'society.price_scarcity_pct',
  pricePlenty: 'society.price_plenty_pct',
} as const
