import { SECTION_ATTR } from './entryOutline'

export type SearchHit = {
  key: string
  sectionId: string | null
  before: string
  match: string
  after: string
  range: Range
}

export const HIT_LIMIT = 400
const CONTEXT = 42
const MATCHES = 'entry-search'
const CURRENT = 'entry-current'
const SKIPPED = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'])

type HighlightRegistry = {
  set: (name: string, value: unknown) => void
  delete: (name: string) => void
}

type HighlightConstructor = new (...ranges: Range[]) => unknown

function registry(): {
  highlights: HighlightRegistry
  Make: HighlightConstructor
} | null {
  const highlights = (CSS as unknown as { highlights?: HighlightRegistry })
    .highlights
  const Make = (globalThis as unknown as { Highlight?: HighlightConstructor })
    .Highlight
  return highlights && Make ? { highlights, Make } : null
}

function visible(node: Text): boolean {
  const parent = node.parentElement
  if (!parent || SKIPPED.has(parent.tagName)) return false
  return parent.closest('[aria-hidden="true"]') === null
}

function clip(text: string, from: number, to: number) {
  const start = Math.max(0, from - CONTEXT)
  const end = Math.min(text.length, to + CONTEXT)
  return {
    before: `${start > 0 ? '…' : ''}${text.slice(start, from)}`.replace(
      /\s+/g,
      ' '
    ),
    match: text.slice(from, to),
    after: `${text.slice(to, end)}${end < text.length ? '…' : ''}`.replace(
      /\s+/g,
      ' '
    ),
  }
}

export function findHits(root: HTMLElement | null, query: string): SearchHit[] {
  const needle = query.trim().toLocaleLowerCase()
  if (!root || needle.length === 0) return []
  const hits: SearchHit[] = []
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  for (
    let node = walker.nextNode();
    node && hits.length < HIT_LIMIT;
    node = walker.nextNode()
  ) {
    const text = node as Text
    const content = text.data
    if (!content.trim() || !visible(text)) continue
    const lower = content.toLocaleLowerCase()
    for (
      let at = lower.indexOf(needle);
      at !== -1 && hits.length < HIT_LIMIT;
      at = lower.indexOf(needle, at + needle.length)
    ) {
      const range = document.createRange()
      range.setStart(text, at)
      range.setEnd(text, at + needle.length)
      const owner = text.parentElement?.closest(`[${SECTION_ATTR}]`)
      hits.push({
        key: `${hits.length}`,
        sectionId: owner?.getAttribute(SECTION_ATTR) ?? null,
        range,
        ...clip(content, at, at + needle.length),
      })
    }
  }
  return hits
}

export function paintHits(hits: SearchHit[], current: SearchHit | null) {
  const found = registry()
  if (!found) return
  const { highlights, Make } = found
  if (hits.length === 0) highlights.delete(MATCHES)
  else highlights.set(MATCHES, new Make(...hits.map((hit) => hit.range)))
  if (current) highlights.set(CURRENT, new Make(current.range))
  else highlights.delete(CURRENT)
}

export function clearHits() {
  paintHits([], null)
}
