import { type Rule, rulePath } from './api'

export const ALL_GROUPS = 'all'

export type RuleRow =
  | {
      type: 'group'
      group: string
      total: number
      changed: number
      open: boolean
    }
  | { type: 'rule'; rule: Rule; path: string }

export type RuleFilter = {
  query: string
  group: string
  onlyChanged: boolean
  open: ReadonlySet<string>
}

export function isChanged(rule: Rule): boolean {
  return rule.value !== rule.default
}

export function isSwitch(rule: Rule): boolean {
  return rule.integer && rule.minimum === 0 && rule.maximum === 1
}

export function groupsOf(rules: Rule[]): string[] {
  const seen: string[] = []
  for (const rule of rules)
    if (!seen.includes(rule.group)) seen.push(rule.group)
  return seen
}

function haystack(rule: Rule): string {
  return `${rule.label} ${rulePath(rule)} ${rule.key.replaceAll('_', ' ')}`.toLowerCase()
}

export function buildRows(rules: Rule[], filter: RuleFilter): RuleRow[] {
  const needle = filter.query.trim().toLowerCase()
  const rows: RuleRow[] = []
  for (const group of groupsOf(rules)) {
    if (filter.group !== ALL_GROUPS && group !== filter.group) continue
    const members = rules.filter((rule) => rule.group === group)
    const groupMatches = needle !== '' && group.toLowerCase().includes(needle)
    const visible = members.filter(
      (rule) =>
        (!filter.onlyChanged || isChanged(rule)) &&
        (needle === '' || groupMatches || haystack(rule).includes(needle))
    )
    if (visible.length === 0) continue
    const changed = members.filter(isChanged).length
    const open =
      filter.open.has(group) ||
      needle !== '' ||
      filter.onlyChanged ||
      filter.group !== ALL_GROUPS
    rows.push({ type: 'group', group, total: visible.length, changed, open })
    if (open)
      for (const rule of visible)
        rows.push({ type: 'rule', rule, path: rulePath(rule) })
  }
  return rows
}

export function exceedsMaximum(rule: Rule, text: string): boolean {
  const value = Number(text)
  return text.trim() !== '' && Number.isFinite(value) && value > rule.maximum
}

export function parseDraft(rule: Rule, text: string): number | string {
  if (text.trim() === '')
    return 'Enter a number, or reset the rule to its default.'
  const value = Number(text)
  if (!Number.isFinite(value)) return 'Enter a number.'
  if (value < rule.minimum) return `At least ${rule.minimum}.`
  return value
}

export function errorsByPath(
  message: string,
  paths: Iterable<string>
): Map<string, string> {
  const found = new Map<string, string>()
  const sentences = message.split(/(?<=\.)\s+/)
  for (const path of paths)
    for (const sentence of sentences)
      if (sentence.includes(path))
        found.set(
          path,
          found.has(path) ? `${found.get(path)} ${sentence}` : sentence
        )
  return found
}

export function formatRuleValue(rule: Rule, value: number): string {
  if (isSwitch(rule)) return value === 1 ? 'On' : 'Off'
  return value.toLocaleString('en-US', {
    maximumFractionDigits: rule.integer ? 0 : 4,
  })
}
