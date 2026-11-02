import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { EntityLink } from '@/components/domain'
import { type RouteRecord } from './api'
import {
  type RouteStateKey,
  routeState,
  routeStateText,
} from './model/cosmosModel'
import { type RuleBook, ruleText } from './model/rules'

type BadgeVariant =
  'success' | 'warning' | 'destructive' | 'secondary' | 'outline'

const STATE_VARIANT: Record<RouteStateKey, BadgeVariant> = {
  open: 'success',
  temporary: 'warning',
  misaligned: 'outline',
  unstable: 'outline',
  scorched: 'destructive',
  sealed: 'secondary',
  severed: 'destructive',
  forgotten: 'outline',
  collapsed: 'destructive',
  snapped: 'destructive',
}

function ruleNote(route: RouteRecord, rules: RuleBook): string | null {
  const state = routeState(route)
  if (route.method === 'slingshot_orbit')
    return `Open only while the worlds are aligned; the cycle returns every ${ruleText(rules.get('alignmentPeriod'))} epochs (World rules › Cosmos and travel).`
  if (state.key === 'severed')
    return `A severed route stays closed for the epochs its breaker chose; the default is ${ruleText(rules.get('severEpochs'))}.`
  return null
}

type RouteStatusChipsProps = {
  route: RouteRecord
  rules: RuleBook
  builderName?: string
}

export function RouteStatusChips({
  route,
  rules,
  builderName,
}: RouteStatusChipsProps) {
  const state = routeState(route)
  const note = ruleNote(route, rules)
  const variant =
    state.key === 'open' && state.untilEpoch !== null
      ? 'warning'
      : STATE_VARIANT[state.key]
  const tip = [route.description, note].filter(Boolean).join(' ')
  const chip = (
    <Badge size='sm' variant={variant}>
      {routeStateText(route)}
    </Badge>
  )
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
      {tip ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <span
              tabIndex={0}
              className='inline-flex min-w-0 rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring/50'
            >
              {chip}
            </span>
          </TooltipTrigger>
          <TooltipContent>{tip}</TooltipContent>
        </Tooltip>
      ) : (
        chip
      )}
      {!route.known && (
        <Badge size='sm' variant='outline'>
          Hidden
        </Badge>
      )}
      {route.builder_son_id !== null && (
        <Badge size='sm' variant='outline'>
          <span className='min-w-0 truncate'>Built by</span>
          <EntityLink kind='son' id={String(route.builder_son_id)}>
            {builderName ?? 'a son'}
          </EntityLink>
        </Badge>
      )}
    </div>
  )
}
