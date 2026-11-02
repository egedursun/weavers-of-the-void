export const WARS_TABS = ['ongoing', 'ended', 'captives', 'tributes'] as const
export type WarsTab = (typeof WARS_TABS)[number]

export type WarsSearch = {
  tab?: WarsTab
  war?: number
}

export function validateWarsSearch(
  search: Record<string, unknown>
): WarsSearch {
  const result: WarsSearch = {}
  if (WARS_TABS.includes(search.tab as WarsTab))
    result.tab = search.tab as WarsTab
  const war = Number(search.war)
  if (Number.isInteger(war) && war > 0) result.war = war
  return result
}
