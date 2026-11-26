type RuleRow = { namespace: string; key: string; value: number }

export const RULE_LIST_ROUTE = 'GET /api/rules'
export const RULE_VALUES_ROUTE = 'GET /api/rules/values'
export const RULE_VALUES_PATH = '/api/rules/values'

function isRuleRows(value: unknown): value is RuleRow[] {
  return Array.isArray(value)
}

export function ruleMap(rows: readonly RuleRow[]): Record<string, number> {
  return Object.fromEntries(
    rows.map((rule) => [`${rule.namespace}.${rule.key}`, rule.value])
  )
}

export function ruleValuesOf(reply: unknown): unknown {
  if (!isRuleRows(reply)) return reply
  return { values: ruleMap(reply) }
}
