import { Globe, Maximize, Shuffle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Toggle } from '@/components/ui/toggle'
import { Muted } from '@/components/typography'

type Graph3DControlsProps = {
  rotate: boolean
  onRotate: (on: boolean) => void
  onFit: () => void
  onRelayout: () => void
}

export function Graph3DControls({
  rotate,
  onRotate,
  onFit,
  onRelayout,
}: Graph3DControlsProps) {
  return (
    <div
      data-graph-3d-controls
      className='flex min-w-0 flex-wrap items-center gap-2'
    >
      <Button size='sm' variant='outline' onClick={onFit}>
        <Maximize />
        Fit
      </Button>
      <Toggle
        size='sm'
        variant='outline'
        pressed={rotate}
        onPressedChange={onRotate}
      >
        <Globe aria-hidden='true' />
        Rotate
      </Toggle>
      <Button size='sm' variant='outline' onClick={onRelayout}>
        <Shuffle />
        Re-layout
      </Button>
      <Muted variant='caption' className='min-w-0 flex-1'>
        Drag: rotate · right-drag: pan · wheel: zoom · click: select ·
        double-click: page · Shift+click: how connected · right-click: focus
      </Muted>
    </div>
  )
}
