import { Play } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Text } from '@/components/typography'
import { type EnginePhase } from './api'
import { phaseLabel } from './phaseModel'

type PhaseRowProps = {
  phase: EnginePhase
  order: number
  busy: boolean
  readOnlyReason: string | null
  onToggle: (phase: EnginePhase, on: boolean) => void
  onRun: (phase: EnginePhase) => void
}

export function PhaseRow({
  phase,
  order,
  busy,
  readOnlyReason,
  onToggle,
  onRun,
}: PhaseRowProps) {
  const switchId = `phase-${phase.name}`
  return (
    <li
      data-phase={phase.name}
      className={cn(
        'flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border p-2.5',
        phase.enabled ? 'bg-background' : 'bg-muted/40'
      )}
    >
      <Badge
        size='sm'
        variant={phase.enabled ? 'default' : 'outline'}
        className='tabular-nums'
      >
        {order}
      </Badge>
      <div className='flex min-w-0 flex-1 basis-40 flex-col gap-1'>
        <Text
          as='label'
          htmlFor={switchId}
          weight='medium'
          truncate
          className={cn(!phase.enabled && 'line-through')}
        >
          {phaseLabel(phase.name)}
        </Text>
        {(phase.heavy || phase.essential || !phase.enabled) && (
          <div className='flex min-w-0 flex-wrap items-center gap-1'>
            {phase.heavy && (
              <Badge size='sm' variant='warning'>
                Changes a lot
              </Badge>
            )}
            {phase.essential && (
              <Badge size='sm' variant='secondary'>
                Always on
              </Badge>
            )}
            {!phase.enabled && (
              <Badge size='sm' variant='outline'>
                Switched off
              </Badge>
            )}
          </div>
        )}
      </div>
      <div className='flex min-w-0 items-center gap-2'>
        <Switch
          id={switchId}
          aria-label={`Run ${phaseLabel(phase.name)} every epoch`}
          checked={phase.enabled}
          disabled={busy || phase.essential || readOnlyReason !== null}
          onCheckedChange={(checked) => onToggle(phase, checked)}
        />
        <Button
          variant='outline'
          size='icon-sm'
          aria-label={`Run ${phaseLabel(phase.name)} now`}
          title='Run now'
          disabled={busy || !phase.runnable || readOnlyReason !== null}
          disabledReason={
            readOnlyReason ??
            (phase.runnable ? 'Working' : 'Advance the epoch instead')
          }
          onClick={() => onRun(phase)}
        >
          <Play />
        </Button>
      </div>
    </li>
  )
}
