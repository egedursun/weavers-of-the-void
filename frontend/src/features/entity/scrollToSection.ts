const DRAWER = '[data-layout="drawer"]'

export function sectionTarget(id: string, root?: ParentNode | null) {
  const selector = `[id="${CSS.escape(id)}"]`
  const scope = root ?? document.querySelector(DRAWER)
  return (
    scope?.querySelector<HTMLElement>(selector) ?? document.getElementById(id)
  )
}

export function scrollToSection(id: string, root?: ParentNode | null) {
  sectionTarget(id, root)?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}
