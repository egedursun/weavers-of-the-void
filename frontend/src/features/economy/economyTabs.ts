export const ECONOMY_TABS = [
  'routes',
  'markets',
  'materials',
  'currencies',
  'debts',
] as const
export type EconomyTab = (typeof ECONOMY_TABS)[number]

export type EconomySearch = {
  ledger?: EconomyTab
}

export function validateEconomySearch(
  search: Record<string, unknown>
): EconomySearch {
  return ECONOMY_TABS.includes(search.ledger as EconomyTab)
    ? { ledger: search.ledger as EconomyTab }
    : {}
}

export function economyWorldId(
  choice: string,
  primaryWorldId: number | null | undefined,
  worldIds: readonly number[]
): number | null {
  const picked = Number(choice)
  if (choice !== '' && worldIds.includes(picked)) return picked
  if (
    primaryWorldId !== null &&
    primaryWorldId !== undefined &&
    worldIds.includes(primaryWorldId)
  )
    return primaryWorldId
  return worldIds[0] ?? null
}
