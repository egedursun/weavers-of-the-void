const LOCALE = 'en-US'

const integerFormat = new Intl.NumberFormat(LOCALE, {
  maximumFractionDigits: 0,
})
const compactFormat = new Intl.NumberFormat(LOCALE, {
  notation: 'compact',
  maximumFractionDigits: 1,
})
const percentFormat = new Intl.NumberFormat(LOCALE, {
  style: 'percent',
  maximumFractionDigits: 0,
})

const dateTimeFormat = new Intl.DateTimeFormat(LOCALE, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export type NumberFormat = 'integer' | 'decimal' | 'percent' | 'compact'

export function formatInteger(value: number): string {
  return integerFormat.format(value)
}

export function formatDecimal(value: number, digits = 2): string {
  return new Intl.NumberFormat(LOCALE, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(value)
}

export function formatPercent(ratio: number): string {
  return percentFormat.format(ratio)
}

export function formatDateTime(value: string): string {
  return dateTimeFormat.format(new Date(value))
}

export function formatCompact(value: number): string {
  return compactFormat.format(value)
}

export function formatNumber(
  value: number,
  format: NumberFormat = 'integer'
): string {
  if (format === 'decimal') return formatDecimal(value)
  if (format === 'percent') return formatPercent(value)
  if (format === 'compact') return formatCompact(value)
  return formatInteger(value)
}
