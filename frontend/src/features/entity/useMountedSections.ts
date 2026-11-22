import { type RefObject, useEffect, useState } from 'react'

const SECTION = '[id^="section-"]'

function sameIds(left: ReadonlySet<string> | null, right: ReadonlySet<string>) {
  return (
    left !== null &&
    left.size === right.size &&
    [...right].every((id) => left.has(id))
  )
}

export function useMountedSections(anchor: RefObject<HTMLElement | null>) {
  const [ids, setIds] = useState<ReadonlySet<string> | null>(null)
  useEffect(() => {
    const root =
      anchor.current?.closest('[data-layout="drawer"]') ??
      anchor.current?.closest('main') ??
      document.body
    let frame = 0
    const read = () => {
      frame = 0
      const next = new Set(
        [...root.querySelectorAll(SECTION)].map((element) => element.id)
      )
      setIds((previous) => (sameIds(previous, next) ? previous : next))
    }
    read()
    const observer = new MutationObserver(() => {
      if (!frame) frame = requestAnimationFrame(read)
    })
    observer.observe(root, { childList: true, subtree: true })
    return () => {
      observer.disconnect()
      if (frame) cancelAnimationFrame(frame)
    }
  }, [anchor])
  return ids
}
