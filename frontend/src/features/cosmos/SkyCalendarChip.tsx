import { CalendarClock } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { type RuleBook } from './model/rules'
import { skyCalendar, skyCalendarText } from './model/skyCalendar'

type SkyCalendarChipProps = {
  epoch: number | undefined
  alignmentUntil: number | null | undefined
  rules: RuleBook
}

export function SkyCalendarChip({
  epoch,
  alignmentUntil,
  rules,
}: SkyCalendarChipProps) {
  const period = rules.get('alignmentPeriod')
  if (epoch === undefined || period === undefined) return null
  const calendar = skyCalendar(epoch, period, alignmentUntil ?? null)
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          tabIndex={0}
          variant={calendar.aligned ? 'warning' : 'outline'}
          aria-label={`Sky calendar: ${skyCalendarText(calendar)}`}
        >
          <CalendarClock aria-hidden='true' />
          {skyCalendarText(calendar)}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>
        {`The planets align every ${plural(calendar.period, 'epoch', 'epochs')}; next cycle at epoch ${calendar.nextCycle}${calendar.forced ? ', and a sky event holds them aligned now' : ''}. The period is a World rule: Cosmos and travel › Planetary alignment.`}
      </TooltipContent>
    </Tooltip>
  )
}
