import { named } from '@/features/entity/environment/labels'
import { type EventChange, type EventMoment, type FactUnit } from './api'
import { CHANGE_OPERATION, FACT_UNIT } from './labels'

const NO_UNIT = new Set<FactUnit>(['none', 'count'])

export function momentText(moment: EventMoment): string {
  const parts: string[] = []
  if (moment.year !== null) parts.push(`year ${moment.year}`)
  if (moment.season !== null) parts.push(`season ${moment.season + 1}`)
  if (moment.day !== null) parts.push(`day ${moment.day + 1}`)
  if (moment.hour !== null) parts.push(`hour ${moment.hour + 1}`)
  parts.push(`epoch ${moment.epoch}`)
  const text = parts.join(', ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export function spokenKey(key: string): string {
  const words = key.replaceAll('_', ' ').replaceAll('.', ' · ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function amountText(amount: number, unit: FactUnit | null): string {
  const shown = Number.isInteger(amount) ? String(amount) : amount.toFixed(2)
  if (unit === null || NO_UNIT.has(unit)) return shown
  return `${shown} ${named(FACT_UNIT, unit).label.toLowerCase()}`
}

export function changeTitle(change: EventChange): string {
  const operation = named(CHANGE_OPERATION, change.operation).label
  const what = change.field ? spokenKey(change.field).toLowerCase() : 'record'
  return `${operation}: ${what} of ${spokenKey(change.table_name).toLowerCase()}`
}
