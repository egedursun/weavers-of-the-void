import { describe, expect, it } from 'vitest'
import { type Rule } from './api'
import {
  ALL_GROUPS,
  buildRows,
  errorsByPath,
  exceedsMaximum,
  formatRuleValue,
  isSwitch,
  parseDraft,
} from './rulesModel'

function rule(
  namespace: string,
  key: string,
  group: string,
  extra: Partial<Rule> = {}
): Rule {
  return {
    namespace,
    key,
    group,
    label: `${key} label`,
    value: 5,
    default: 5,
    minimum: 0,
    maximum: 10,
    integer: true,
    ...extra,
  }
}

const RULES = [
  rule('war', 'fatigue', 'War'),
  rule('war', 'peace', 'War', { value: 7 }),
  rule('engine_phases', 'sky', 'Engine phases', {
    value: 0,
    default: 1,
    maximum: 1,
  }),
]

const CLOSED = {
  query: '',
  group: ALL_GROUPS,
  onlyChanged: false,
  open: new Set<string>(),
}

describe('world rules model', () => {
  it('shows closed groups until one is opened', () => {
    expect(buildRows(RULES, CLOSED).map((row) => row.type)).toEqual([
      'group',
      'group',
    ])
    const open = buildRows(RULES, { ...CLOSED, open: new Set(['War']) })
    expect(open.filter((row) => row.type === 'rule')).toHaveLength(2)
  })

  it('searches labels, paths and groups and filters changed rules', () => {
    const found = buildRows(RULES, { ...CLOSED, query: 'peace' })
    expect(
      found
        .filter((row) => row.type === 'rule')
        .map((row) => row.type === 'rule' && row.path)
    ).toEqual(['war.peace'])
    const changed = buildRows(RULES, { ...CLOSED, onlyChanged: true })
    expect(changed.filter((row) => row.type === 'rule')).toHaveLength(2)
    const byGroup = buildRows(RULES, { ...CLOSED, query: 'engine' })
    expect(byGroup.filter((row) => row.type === 'rule')).toHaveLength(1)
  })

  it('validates drafts against the rule range and kind', () => {
    expect(parseDraft(RULES[0], '3')).toBe(3)
    expect(parseDraft(RULES[0], '3.5')).toBe(3.5)
    expect(parseDraft(RULES[0], '11')).toBe(11)
    expect(exceedsMaximum(RULES[0], '11')).toBe(true)
    expect(exceedsMaximum(RULES[0], '10')).toBe(false)
    expect(parseDraft(RULES[0], '-1')).toBe('At least 0.')
    expect(parseDraft(RULES[0], '')).toMatch(/Enter a number/)
  })

  it('renders switches and maps constraint messages to rules', () => {
    expect(isSwitch(RULES[2])).toBe(true)
    expect(formatRuleValue(RULES[2], 1)).toBe('On')
    const errors = errorsByPath(
      'war.fatigue (9) must be below war.peace (7). Other text.',
      ['war.fatigue', 'war.peace', 'x.y']
    )
    expect([...errors.keys()]).toEqual(['war.fatigue', 'war.peace'])
  })
})
