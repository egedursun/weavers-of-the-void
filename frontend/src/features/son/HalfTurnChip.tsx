import { Hourglass } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { type SonPublic } from '@/features/pantheon/api'

export function HalfTurnChip({ view }: { view: SonPublic }) {
  if (view.band_action_loss <= 0) return null
  const lost = `${view.band_action_loss} ${view.band_action_loss === 1 ? 'action' : 'actions'} lost each epoch`
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          size='sm'
          variant='warning'
          tabIndex={0}
          data-half-turn
          aria-label={`Half turn: ${lost}. ${view.band_effect}`}
        >
          <Hourglass aria-hidden='true' />
          Half turn
        </Badge>
      </TooltipTrigger>
      <TooltipContent>{`${view.band_effect} ${lost}.`}</TooltipContent>
    </Tooltip>
  )
}
