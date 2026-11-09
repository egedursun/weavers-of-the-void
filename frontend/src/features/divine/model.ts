import { useForeignGods, useSons } from '@/features/pantheon/api'

const HEAT = [
  'bg-muted/30',
  'bg-primary/10',
  'bg-primary/20',
  'bg-primary/30',
  'bg-primary/40',
  'bg-primary/60',
] as const

export function heat(value: number): string {
  return HEAT[Math.min(HEAT.length - 1, Math.floor(value / 20))]
}

export function useGodTable(
  includeCreator?: { id: number; name: string } | null
): Record<string, string> {
  const sons = useSons()
  const gods = useForeignGods()
  const table: Record<string, string> = {}
  if (includeCreator)
    table[String(includeCreator.id)] = `${includeCreator.name} (the Creator)`
  for (const row of sons.data ?? []) table[String(row.son.id)] = row.son.name
  for (const god of gods.data ?? [])
    table[String(god.id)] = `${god.name} (foreign god)`
  return table
}
