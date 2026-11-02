import { Compass, Star } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Muted } from '@/components/typography'
import { SCALE_BAR_PX, leagues } from './mapModel'

type MapScaleOverlayProps = {
  scale: number
  starName: string | null
}

export function MapScaleOverlay({ scale, starName }: MapScaleOverlayProps) {
  const units = scale > 0 ? SCALE_BAR_PX / scale : 0
  return (
    <>
      <div
        aria-hidden='true'
        className='pointer-events-none absolute bottom-3 left-3 flex flex-col items-start gap-1 rounded-md bg-background/80 px-2 py-1'
      >
        <Muted variant='caption'>{`${leagues(units)} leagues`}</Muted>
        <div
          className='h-1 rounded-sm border-x-2 border-b-2 border-foreground/70'
          style={{ width: SCALE_BAR_PX }}
        />
      </div>
      <div
        aria-hidden='true'
        className='pointer-events-none absolute right-3 bottom-3 flex flex-col items-center gap-0.5 rounded-md bg-background/80 px-2 py-1 text-muted-foreground'
      >
        <Muted variant='caption' weight='semibold'>
          N
        </Muted>
        <Compass className='size-icon-xl' />
      </div>
      {starName && (
        <div className='pointer-events-none absolute top-3 right-3 flex max-w-1/2 min-w-0'>
          <Badge variant='outline' className='bg-background/80'>
            <Star aria-hidden='true' />
            <span className='min-w-0 truncate'>{`${starName} ascendant`}</span>
          </Badge>
        </div>
      )}
    </>
  )
}
