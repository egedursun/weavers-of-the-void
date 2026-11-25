import { Skull } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { DEAD_SEAL } from './looks'

export function DeadSeal({
  death,
  size = 'default',
}: {
  death: string
  size?: 'default' | 'sm'
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          data-domain='presence-dead-seal'
          variant='destructive'
          size={size}
          tabIndex={0}
        >
          <Skull />
          {DEAD_SEAL}
        </Badge>
      </TooltipTrigger>
      <TooltipContent className='max-w-xs'>
        {`${death || 'It died.'} It speaks as one called back, and knows it.`}
      </TooltipContent>
    </Tooltip>
  )
}
