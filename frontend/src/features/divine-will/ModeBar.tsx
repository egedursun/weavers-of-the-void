import {
  Copy,
  Eye,
  Hammer,
  Lock,
  type LucideIcon,
  ShieldCheck,
} from 'lucide-react'
import { refusalIn, useTeamGate } from '@/api/teamGate'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { type KpiTone, Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { WILL_MODE_PERMISSION } from '@/features/team/permissions'
import { useWillModes } from './api'
import {
  MODE_LOOK,
  MODE_ORDER,
  type ModeImpact,
  TOOLSET_LABEL,
  impactOf,
  isMode,
} from './modes'
import { type DivineWillMode } from './types'

const TONE_TEXT: Record<KpiTone, string> = {
  gold: 'text-primary',
  verdigris: 'text-brand-verdigris',
  info: 'text-info',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-destructive',
  muted: 'text-muted-foreground',
}

const IMPACT_LOOK: Record<
  ModeImpact,
  { label: string; icon: LucideIcon; variant: 'warning' | 'info' | 'outline' }
> = {
  acts: { label: 'Changes the world', icon: Hammer, variant: 'warning' },
  after_approval: {
    label: 'Changes after approval',
    icon: ShieldCheck,
    variant: 'info',
  },
  copy: { label: 'Works on a copy', icon: Copy, variant: 'outline' },
  reads: { label: 'Only reads', icon: Eye, variant: 'outline' },
}

type ModeBarProps = {
  mode: DivineWillMode
  onChange: (mode: DivineWillMode) => void
  disabledReason?: string | null
}

export function ModeBar({
  mode,
  onChange,
  disabledReason = null,
}: ModeBarProps) {
  const modes = useWillModes()
  const team = useTeamGate()
  const served = modes.data?.modes.find((item) => item.mode === mode)
  const look = MODE_LOOK[mode]
  const impact = IMPACT_LOOK[impactOf(look, served)]
  const ImpactIcon = impact.icon
  return (
    <div data-domain='will-mode-bar' className='flex min-w-0 flex-col gap-2'>
      <ToggleGroup
        type='single'
        variant='outline'
        size='sm'
        value={mode}
        aria-label='Mode of the Divine Will'
        disabled={disabledReason !== null}
        onValueChange={(value) => {
          if (isMode(value)) onChange(value)
        }}
        className='grid w-full grid-cols-3 @4xl/will:grid-cols-6'
      >
        {MODE_ORDER.map((item) => {
          const itemLook = MODE_LOOK[item]
          const Icon = itemLook.icon
          const title =
            modes.data?.modes.find((entry) => entry.mode === item)?.name ??
            itemLook.label
          const refused = refusalIn(team, WILL_MODE_PERMISSION[item])
          return (
            <Tooltip key={item}>
              <TooltipTrigger asChild>
                <ToggleGroupItem
                  value={item}
                  aria-label={title}
                  aria-description={refused ?? undefined}
                  data-mode={item}
                  className='w-full min-w-0 justify-start'
                >
                  <Icon
                    aria-hidden='true'
                    className={cn(item === mode && TONE_TEXT[itemLook.tone])}
                  />
                  <span className='min-w-0 truncate'>{itemLook.tab}</span>
                  {refused !== null && (
                    <Lock
                      aria-hidden='true'
                      className='ms-auto size-icon-xs text-muted-foreground'
                    />
                  )}
                </ToggleGroupItem>
              </TooltipTrigger>
              <TooltipContent>
                {disabledReason ?? refused ?? itemLook.caption}
              </TooltipContent>
            </Tooltip>
          )
        })}
      </ToggleGroup>
      <div
        aria-live='polite'
        className='flex min-w-0 items-center gap-2.5 rounded-md surface-well px-2.5 py-2'
      >
        <Medallion icon={look.icon} tone={look.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text
            as='span'
            weight='semibold'
            className='text-gilded font-display'
          >
            {served?.name ?? look.label}
          </Text>
          <Muted as='span' variant='caption'>
            {served?.purpose ?? look.caption}
          </Muted>
        </div>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge size='sm' variant={impact.variant} tabIndex={0}>
              <ImpactIcon />
              {impact.label}
            </Badge>
          </TooltipTrigger>
          <TooltipContent className='flex flex-col gap-0.5'>
            {served ? (
              <>
                <span>
                  {served.toolsets
                    .map((toolset) => TOOLSET_LABEL[toolset])
                    .join(' · ')}
                </span>
                <span>{`${plural(served.tools.length, 'tool')} in this mode`}</span>
              </>
            ) : (
              <span>{look.caption}</span>
            )}
          </TooltipContent>
        </Tooltip>
      </div>
    </div>
  )
}
