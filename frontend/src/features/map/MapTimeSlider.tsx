import { useEffect, useRef, useState } from 'react'
import { Camera, Pause, Play } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import { EpochSlider } from '@/components/domain'
import { Muted, Stat } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

const DEBOUNCE_MS = 220
const STEP_MS = 1500

type MapTimeSliderProps = {
  current: number
  shown: number
  onShow: (epoch: number | null) => void
}

export function SnapshotButton() {
  const { reason } = useGodGate()
  const snapshot = useGodAction({
    run: () => unwrap(api.POST('/api/actions/map:snapshot')),
    success: 'The maps of this epoch were recorded',
  })
  return (
    <ActionButton
      label='Record this epoch'
      icon={Camera}
      size='sm'
      blocked={reason({ world: true })}
      pending={snapshot.isPending}
      onRun={() => snapshot.mutate()}
    />
  )
}

export function MapTimeSlider({ current, shown, onShow }: MapTimeSliderProps) {
  const [draft, setDraft] = useState(shown)
  const [playing, setPlaying] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  const [synced, setSynced] = useState(shown)
  if (synced !== shown) {
    setSynced(shown)
    setDraft(shown)
  }

  useEffect(() => () => window.clearTimeout(timer.current), [])

  useEffect(() => {
    if (!playing) return
    const handle = window.setTimeout(() => {
      if (shown >= current) {
        setPlaying(false)
        onShow(null)
        return
      }
      const next = shown + 1
      onShow(next >= current ? null : next)
      if (next >= current) setPlaying(false)
    }, STEP_MS)
    return () => window.clearTimeout(handle)
  }, [playing, shown, current, onShow])

  const change = (value: number) => {
    setPlaying(false)
    setDraft(value)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(
      () => onShow(value >= current ? null : value),
      DEBOUNCE_MS
    )
  }

  const toggle = () => {
    if (playing) {
      setPlaying(false)
      return
    }
    if (shown >= current) onShow(1)
    setPlaying(true)
  }

  return (
    <div
      data-map-time
      className='flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2'
    >
      <Button
        size='icon-sm'
        variant='outline'
        aria-label={playing ? 'Stop' : 'Play epochs in order'}
        onClick={toggle}
        disabled={current < 2}
        disabledReason='The world has lived only one epoch'
      >
        {playing ? <Pause /> : <Play />}
      </Button>
      <EpochSlider
        label='Time'
        value={draft}
        max={current}
        onChange={change}
        valueLabel={
          <span className='inline-flex items-baseline gap-1'>
            <Stat value={`E${draft}`} />
            <Muted as='span' variant='caption'>
              {draft >= current ? 'today' : `/ ${current}`}
            </Muted>
          </span>
        }
      />
      <SnapshotButton />
    </div>
  )
}
