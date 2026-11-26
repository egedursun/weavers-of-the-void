import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { RULES_STALE_TIME_MS } from '@/constants/ui'
import { useAgeRefusal } from '@/features/team/writeGate'

export type Rule = components['schemas']['RuleResponse']

export const ruleKeys = {
  list: queryKeys.rules.all,
}

export function rulePath(rule: Pick<Rule, 'namespace' | 'key'>): string {
  return `${rule.namespace}.${rule.key}`
}

export function useRules() {
  return useQuery({
    queryKey: ruleKeys.list,
    queryFn: () => unwrap(api.GET('/api/rules')),
    staleTime: RULES_STALE_TIME_MS,
  })
}

export function useRuleValue(path: string): number | null {
  const rules = useRules()
  const found = rules.data?.find((rule) => rulePath(rule) === path)
  return found ? found.value : null
}

const RULE_WRITES = [{ method: 'PATCH', path: '/api/rules' }] as const

export function useRulesWait(): string | null {
  return useAgeRefusal(RULE_WRITES)
}

function useRefreshRules() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.rules.all })
    void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
  }
}

export function useResetRule() {
  const refresh = useRefreshRules()
  return useMutation({
    writes: [{ method: 'DELETE', path: '/api/rules/{namespace}/{key}' }],
    mutationFn: (rule: Rule) =>
      unwrap(
        api.DELETE('/api/rules/{namespace}/{key}', {
          params: { path: { namespace: rule.namespace, key: rule.key } },
        })
      ),
    onSettled: refresh,
  })
}

export function useResetGroup() {
  const refresh = useRefreshRules()
  return useMutation({
    writes: [{ method: 'PATCH', path: '/api/rules' }],
    mutationFn: (rules: Rule[]) =>
      unwrap(
        api.PATCH('/api/rules', {
          body: {
            reset_all: false,
            changes: Object.fromEntries(
              rules.map((rule) => [rulePath(rule), null])
            ),
          },
        })
      ),
    onSettled: refresh,
  })
}

export function useResetAllRules() {
  const refresh = useRefreshRules()
  return useMutation({
    writes: [{ method: 'DELETE', path: '/api/rules' }],
    mutationFn: () => unwrap(api.DELETE('/api/rules')),
    onSettled: refresh,
  })
}

export function useSaveRules() {
  const refresh = useRefreshRules()
  return useMutation({
    writes: [
      { method: 'PATCH', path: '/api/rules' },
      { method: 'PUT', path: '/api/rules/{namespace}/{key}' },
    ],
    mutationFn: async (changes: Map<Rule, number>) => {
      const entries = [...changes]
      if (entries.length === 1) {
        const [[rule, value]] = entries
        return unwrap(
          api.PUT('/api/rules/{namespace}/{key}', {
            params: { path: { namespace: rule.namespace, key: rule.key } },
            body: { value },
          })
        )
      }
      return unwrap(
        api.PATCH('/api/rules', {
          body: {
            reset_all: false,
            changes: Object.fromEntries(
              entries.map(([rule, value]) => [rulePath(rule), value])
            ),
          },
        })
      )
    },
    onSettled: refresh,
  })
}
