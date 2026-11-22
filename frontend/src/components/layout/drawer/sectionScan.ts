export type DrawerSection = { id: string; label: string }

const SECTION = '[id^="section-"]'

function labelOf(element: Element) {
  const heading = element.getAttribute('aria-labelledby')
  const named = heading ? document.getElementById(heading) : null
  const text = (named ?? element.querySelector('h2, h3'))?.textContent ?? ''
  return text.trim()
}

export function sectionsIn(root: ParentNode | null): DrawerSection[] {
  if (!root) return []
  const found: DrawerSection[] = []
  const seen = new Set<string>()
  for (const element of root.querySelectorAll(SECTION)) {
    if (element.parentElement?.closest(SECTION)) continue
    const label = labelOf(element)
    if (!label || seen.has(element.id)) continue
    seen.add(element.id)
    found.push({ id: element.id, label })
  }
  return found
}
