import { type ReactNode } from 'react'
import { formatInteger } from '@/lib/format'

export type MultiSelectOption = {
  value: string
  label: string
  detail?: string
  icon?: ReactNode
}

export function visibleOptions(
  options: MultiSelectOption[],
  chosen: ReadonlySet<string>,
  query: string
): MultiSelectOption[] {
  const needle = query.trim().toLowerCase()
  if (!needle) return options
  return options.filter(
    (option) =>
      chosen.has(option.value) ||
      option.label.toLowerCase().includes(needle) ||
      (option.detail ?? '').toLowerCase().includes(needle)
  )
}

export function selectionText(count: number, min: number): string {
  const selected = `${formatInteger(count)} selected`
  return min > 0 ? `${selected} · at least ${formatInteger(min)}` : selected
}
