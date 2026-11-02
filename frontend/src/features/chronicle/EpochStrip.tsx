import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'

type EpochStripProps = {
  epochs: number[]
  onJump: (epoch: number) => void
}

export function EpochStrip({ epochs, onJump }: EpochStripProps) {
  const [current, setCurrent] = useState<number | null>(null)
  const signature = epochs.join(',')
  useEffect(() => {
    const articles = Array.from(
      document.querySelectorAll<HTMLElement>('[data-epoch-article]')
    )
    if (articles.length === 0 || typeof IntersectionObserver === 'undefined')
      return
    const observer = new IntersectionObserver(
      (entries) => {
        const top = entries
          .filter((entry) => entry.isIntersecting)
          .sort(
            (left, right) =>
              left.boundingClientRect.top - right.boundingClientRect.top
          )[0]
        if (top)
          setCurrent(Number(top.target.getAttribute('data-epoch-article')))
      },
      { rootMargin: '0px 0px -70% 0px' }
    )
    for (const article of articles) observer.observe(article)
    return () => observer.disconnect()
  }, [signature])
  if (epochs.length < 2) return null
  return (
    <nav
      aria-label='Jump to an epoch'
      className='sticky top-0 no-scrollbar flex min-w-0 gap-1 overflow-x-auto border-b bg-background pb-2'
    >
      {epochs.map((epoch) => (
        <Button
          key={epoch}
          variant={current === epoch ? 'secondary' : 'ghost'}
          size='sm'
          aria-current={current === epoch ? 'true' : undefined}
          onClick={() => onJump(epoch)}
        >
          {`E${epoch}`}
        </Button>
      ))}
    </nav>
  )
}
