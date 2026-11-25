export type LibrarySearch = {
  artifact?: number
  subject?: number
}

function positive(value: unknown): number | undefined {
  const number = typeof value === 'number' ? value : Number(value)
  return Number.isInteger(number) && number > 0 ? number : undefined
}

export function validateLibrarySearch(
  search: Record<string, unknown>
): LibrarySearch {
  const result: LibrarySearch = {}
  const artifact = positive(search.artifact)
  if (artifact) result.artifact = artifact
  const subject = positive(search.subject)
  if (subject) result.subject = subject
  return result
}
