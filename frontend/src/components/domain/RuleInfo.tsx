import { Link } from '@tanstack/react-router'
import { SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'

type RuleInfoProps = {
  rule: string
  label?: string
}

export function RuleInfo({ rule, label }: RuleInfoProps) {
  const text = `${label ?? 'This number'} is set by the world rule ${rule}`
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant='ghost' size='icon-sm' asChild>
          <Link
            to='/settings/world-rules'
            search={{ q: rule }}
            aria-label={text}
            data-domain='rule-info'
            data-rule-path={rule}
          >
            <SlidersHorizontal />
          </Link>
        </Button>
      </TooltipTrigger>
      <TooltipContent>{text}</TooltipContent>
    </Tooltip>
  )
}
