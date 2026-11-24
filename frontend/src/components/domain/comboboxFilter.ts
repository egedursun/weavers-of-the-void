import { type ReactNode } from 'react'

export type ComboboxOption = {
  value: string
  label: string
  hint?: string
  adornment?: ReactNode
  keywords?: string
}

export const DEFAULT_MAX_SHOWN = 60

export function matchesOption(option: ComboboxOption, needle: string): boolean {
  if (!needle) return true
  const haystack =
    `${option.label} ${option.hint ?? ''} ${option.keywords ?? ''}`.toLowerCase()
  return needle
    .split(/\s+/)
    .filter(Boolean)
    .every((part) => haystack.includes(part))
}

export function filterOptions(
  options: ComboboxOption[],
  query: string,
  limit: number
): ComboboxOption[] {
  const needle = query.trim().toLowerCase()
  const exact: ComboboxOption[] = []
  const rest: ComboboxOption[] = []
  for (const option of options) {
    if (!matchesOption(option, needle)) continue
    if (needle && option.label.toLowerCase().startsWith(needle))
      exact.push(option)
    else rest.push(option)
    if (exact.length >= limit) break
  }
  return [...exact, ...rest].slice(0, limit)
}
