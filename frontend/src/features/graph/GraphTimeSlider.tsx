import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { EpochSlider } from '@/components/domain'
import { Muted, Stat } from '@/components/typography'

const DEBOUNCE_MS = 200

type GraphTimeSliderProps = {
  current: number
  shown: number | null
  onShow: (epoch: number | null) => void
}

export function GraphTimeSlider({
  current,
  shown,
  onShow,
}: GraphTimeSliderProps) {
  const value = shown ?? current
  const [draft, setDraft] = useState(value)
  const [synced, setSynced] = useState(value)
  const timer = useRef<number | undefined>(undefined)
  if (synced !== value) {
    setSynced(value)
    setDraft(value)
  }
  useEffect(() => () => window.clearTimeout(timer.current), [])
  return (
    <div
      data-graph-time
      className='flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2'
    >
      <EpochSlider
        label='Time'
        value={draft}
        max={current}
        onChange={(next) => {
          setDraft(next)
          window.clearTimeout(timer.current)
          timer.current = window.setTimeout(
            () => onShow(next >= current ? null : next),
            DEBOUNCE_MS
          )
        }}
        valueLabel={
          <span className='inline-flex items-baseline gap-1'>
            <Stat value={`E${draft}`} />
            <Muted as='span' variant='caption'>
              {draft >= current ? 'today' : `/ ${current}`}
            </Muted>
          </span>
        }
        actions={
          draft < current && (
            <Button size='sm' variant='outline' onClick={() => onShow(null)}>
              Today
            </Button>
          )
        }
      />
    </div>
  )
}
