import { ENTRY_REVEAL } from '@/components/layout/entry/EntryWindow'

const ENTRY = '[data-layout="entry"]'

function sectionTarget(id: string, root?: ParentNode | null) {
  const selector = `[id="${CSS.escape(id)}"]`
  const scope = root ?? document.querySelector(ENTRY)
  return (
    scope?.querySelector<HTMLElement>(selector) ?? document.getElementById(id)
  )
}

export function scrollToSection(id: string, root?: ParentNode | null) {
  const target = sectionTarget(id, root)
  if (!target) return
  const owner = target.closest(`${ENTRY} [data-entry-filter]`)
  if (owner) {
    owner.dispatchEvent(new CustomEvent(ENTRY_REVEAL, { detail: id }))
    return
  }
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
