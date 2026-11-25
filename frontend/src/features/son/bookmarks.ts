import { universeKey } from '@/lib/universeStorage'

const BOOKMARK_KEY = 'aerona.bookmarks'

function read(): string[] {
  try {
    const raw = localStorage.getItem(universeKey(BOOKMARK_KEY))
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed)
      ? parsed.filter((item) => typeof item === 'string')
      : []
  } catch {
    return []
  }
}

export function isBookmarked(kind: string, id: number): boolean {
  return read().includes(`${kind}:${id}`)
}

export function toggleBookmark(kind: string, id: number): boolean {
  const key = `${kind}:${id}`
  const current = read()
  const next = current.includes(key)
    ? current.filter((item) => item !== key)
    : [...current, key]
  try {
    localStorage.setItem(universeKey(BOOKMARK_KEY), JSON.stringify(next))
  } catch {
    return current.includes(key)
  }
  return next.includes(key)
}
