export const LANGUAGE_VIEWS = [
  'dictionary',
  'tree',
  'knowledge',
  'names',
] as const
export type LanguageViewKey = (typeof LANGUAGE_VIEWS)[number]

export type LanguagesSearch = {
  view?: LanguageViewKey
  language?: number
  q?: string
}

export function validateLanguagesSearch(
  search: Record<string, unknown>
): LanguagesSearch {
  const result: LanguagesSearch = {}
  if (
    typeof search.view === 'string' &&
    (LANGUAGE_VIEWS as readonly string[]).includes(search.view)
  )
    result.view = search.view as LanguageViewKey
  const language =
    typeof search.language === 'string'
      ? Number(search.language)
      : search.language
  if (
    typeof language === 'number' &&
    Number.isInteger(language) &&
    language > 0
  )
    result.language = language
  if (typeof search.q === 'string' && search.q.trim()) result.q = search.q
  return result
}
