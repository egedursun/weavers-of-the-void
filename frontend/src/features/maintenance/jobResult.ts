export type ResultCounter = {
  key: string
  label: string
  value: number
}

const LEDGER_FIELD = 'ledger_entry_id'
const COUNTERS_FIELD = 'counters'
const HIDDEN_FIELDS = new Set([LEDGER_FIELD, 'son_id', 'task'])

export function counterLabel(key: string): string {
  const spaced = key.replace(/[_:]+/g, ' ').trim()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

function numericEntries(source: Record<string, unknown>): ResultCounter[] {
  return Object.entries(source)
    .filter(
      (entry): entry is [string, number] =>
        typeof entry[1] === 'number' && !HIDDEN_FIELDS.has(entry[0])
    )
    .map(([key, value]) => ({ key, label: counterLabel(key), value }))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function resultCounters(
  result: Record<string, unknown> | null | undefined
): ResultCounter[] {
  if (!result) return []
  const nested = result[COUNTERS_FIELD]
  return numericEntries(isRecord(nested) ? nested : result)
}

export function resultLedgerEntry(
  result: Record<string, unknown> | null | undefined
): number | null {
  const value = result?.[LEDGER_FIELD]
  return typeof value === 'number' ? value : null
}
