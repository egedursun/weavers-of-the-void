import {
  ENTRY_CATEGORIES,
  type EntryCategory,
  SECTION_CATEGORY,
} from './entryCategories'

export type OutlineSection = {
  id: string
  label: string
  category: EntryCategory
}

export type Outline = {
  sections: OutlineSection[]
  title: string | null
  kind: string | null
}

export const CATEGORY_ATTR = 'data-entry-category'
export const SECTION_ATTR = 'data-entry-section'
export const COLLAPSED_ATTR = 'data-entry-collapsed'
const SECTION_PREFIX = 'section-'
const BAY = 'ornate-bay'
const FIRST_CATEGORY: EntryCategory = ENTRY_CATEGORIES[0].key

function anchorOf(element: Element): HTMLElement | null {
  if (element.id.startsWith(SECTION_PREFIX)) return element as HTMLElement
  const inner = element.firstElementChild
  if (
    element.getAttribute('data-slot') === BAY &&
    inner instanceof HTMLElement &&
    inner.id.startsWith(SECTION_PREFIX)
  )
    return inner
  return null
}

function labelOf(anchor: HTMLElement): string {
  const heading = anchor.getAttribute('aria-labelledby')
  const named = heading ? document.getElementById(heading) : null
  const text = (named ?? anchor.querySelector('h2, h3, h4'))?.textContent ?? ''
  return (
    text.trim() || anchor.id.slice(SECTION_PREFIX.length).replace(/[-_]/g, ' ')
  )
}

export function categoryOf(id: string): EntryCategory {
  return SECTION_CATEGORY[id] ?? FIRST_CATEGORY
}

function holdsSection(element: Element): boolean {
  return element.querySelector(`[id^="${SECTION_PREFIX}"]`) !== null
}

export function readOutline(root: HTMLElement | null): Outline {
  if (!root) return { sections: [], title: null, kind: null }
  const sections: OutlineSection[] = []
  const seen = new Set<string>()
  let current: EntryCategory = FIRST_CATEGORY
  const visit = (parent: Element) => {
    for (const child of Array.from(parent.children)) {
      const anchor = anchorOf(child)
      if (anchor) {
        current = categoryOf(anchor.id)
        child.setAttribute(CATEGORY_ATTR, current)
        child.setAttribute(SECTION_ATTR, anchor.id)
        if (!seen.has(anchor.id)) {
          seen.add(anchor.id)
          sections.push({
            id: anchor.id,
            label: labelOf(anchor),
            category: current,
          })
        }
      } else if (holdsSection(child)) {
        child.removeAttribute(CATEGORY_ATTR)
        visit(child)
      } else {
        child.setAttribute(CATEGORY_ATTR, current)
      }
    }
  }
  visit(root)
  const title = root.querySelector('h1')?.textContent?.trim() || null
  const kind =
    root
      .querySelector('[data-entry-kind]')
      ?.getAttribute('data-entry-kind')
      ?.trim() || null
  return { sections, title, kind }
}

export function sameOutline(left: Outline, right: Outline): boolean {
  return (
    left.title === right.title &&
    left.kind === right.kind &&
    left.sections.length === right.sections.length &&
    left.sections.every(
      (section, index) =>
        section.id === right.sections[index].id &&
        section.label === right.sections[index].label
    )
  )
}

export function anchorIn(
  root: HTMLElement | null,
  id: string
): HTMLElement | null {
  return root?.querySelector<HTMLElement>(`[id="${CSS.escape(id)}"]`) ?? null
}
