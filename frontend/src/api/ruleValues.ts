import { useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { queryKeys } from '@/api/queryKeys'
import { RULES_STALE_TIME_MS } from '@/constants/ui'

export type RuleValues = Readonly<Record<string, number>>

export function useRuleValues() {
  return useQuery({
    queryKey: queryKeys.rules.values,
    queryFn: async (): Promise<RuleValues> =>
      (await unwrap(api.GET('/api/rules/values'))).values,
    staleTime: RULES_STALE_TIME_MS,
  })
}

export function useRuleLookup() {
  const values = useRuleValues()
  return useCallback(
    (path: string): number | undefined => values.data?.[path],
    [values.data]
  )
}

export function useRuleValue(path: string): number | null {
  return useRuleValues().data?.[path] ?? null
}

export function ruleValue(
  values: RuleValues | undefined,
  namespace: string,
  key: string,
  fallback: number
): number {
  return values?.[`${namespace}.${key}`] ?? fallback
}
