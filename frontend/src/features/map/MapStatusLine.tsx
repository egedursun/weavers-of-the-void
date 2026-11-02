import { Grid3x3, Map as MapIcon, MapPin } from 'lucide-react'
import { formatNumber } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Muted } from '@/components/typography'

type MapStatusLineProps = {
  worldName: string
  typeLabel: string
  multiWorld: boolean
  knownCells: number
  regions: number
  markers: number
  past: boolean
  noteMode: boolean
}

export function MapStatusLine(props: MapStatusLineProps) {
  const hint = props.past
    ? "You're looking at the past; markers can't be moved."
    : props.noteMode
      ? 'Note pin is on: click an empty spot.'
      : 'Drag markers to move · click: open its page.'
  return (
    <div
      data-map-status
      className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2'
    >
      {props.multiWorld && (
        <Badge
          size='sm'
          variant='info'
        >{`${props.worldName} · ${props.typeLabel}`}</Badge>
      )}
      <Badge size='sm' variant='outline'>
        <Grid3x3 />
        {`${formatNumber(props.knownCells)} known cells`}
      </Badge>
      <Badge size='sm' variant='outline'>
        <MapIcon />
        {`${formatNumber(props.regions)} regions`}
      </Badge>
      <Badge size='sm' variant='outline'>
        <MapPin />
        {`${formatNumber(props.markers)} markers`}
      </Badge>
      <Muted variant='caption' truncate>
        {hint}
      </Muted>
    </div>
  )
}
