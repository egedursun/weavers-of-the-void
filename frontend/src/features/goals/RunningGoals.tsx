import { useState } from 'react'
import { CalendarClock, Flag, Pause, Pencil, Play, Trophy } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { EmptyState, FormRow, Medallion } from '@/components/domain'
import { Label, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { CountField, DeadlineField } from './GoalFields'
import {
  BASIS_LABEL,
  COMPARATOR_LABEL,
  type GoalsOverview,
  roman,
  type RunningScenario,
} from './api'
import {
  DEFAULT_DEADLINE,
  outOfRange,
  parseCount,
  useDeadlineMax,
} from './goalForm'
import { SCENARIO_ICON } from './goalIcons'

const FALLBACK_HOLD = 200
const FALLBACK_TARGET = 2000000000
const TITLE_MAX = 200

function EditGoalDialog({
  item,
  targetMax,
}: {
  item: RunningScenario
  targetMax: number
}) {
  const own = item.key === 'custom'
  const [open, setOpen] = useState(false)
  const [target, setTarget] = useState(String(item.target))
  const [timed, setTimed] = useState(item.deadline_epoch !== null)
  const [epochs, setEpochs] = useState(String(DEFAULT_DEADLINE))
  const [hold, setHold] = useState(String(item.hold_epochs))
  const [title, setTitle] = useState(item.title ?? '')
  const rule = useRuleLookup()
  const deadlineMax = useDeadlineMax()
  const holdMax = rule('goals.custom_hold_max_epochs') ?? FALLBACK_HOLD
  const { reason } = useGodGate()
  const chosen = parseCount(target)
  const held = parseCount(hold)
  const deadline = timed ? parseCount(epochs) : null
  const low = !own || item.basis === 'gained' ? 1 : 0
  const invalid =
    outOfRange(chosen, low, targetMax, 'target') ??
    (own ? outOfRange(held, 0, holdMax, 'hold') : null) ??
    (timed ? outOfRange(deadline, 1, deadlineMax, 'deadline') : null)
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/scenarios/{scenario_id}/edit', {
          params: { path: { scenario_id: item.id } },
          body: {
            target: chosen ?? item.target,
            deadline_epochs: deadline,
            hold_epochs: own ? (held ?? 0) : 0,
            title: own ? title.trim() || null : null,
          },
        })
      ),
    onDone: () => setOpen(false),
  })
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (next) {
          setTarget(String(item.target))
          setTimed(item.deadline_epoch !== null)
          setHold(String(item.hold_epochs))
          setTitle(item.title ?? '')
        }
      }}
    >
      <DialogTrigger asChild>
        <Button size='sm' variant='ghost'>
          <Pencil />
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{`Reshape ${item.name}`}</DialogTitle>
          <DialogDescription>
            The worth of the goal is weighed again from its new target, hold and
            deadline.
          </DialogDescription>
        </DialogHeader>
        <div className='flex min-w-0 flex-col gap-3'>
          <CountField
            label='Target'
            value={target}
            min={low}
            max={targetMax}
            onChange={setTarget}
          />
          {own && (
            <CountField
              label='Hold'
              description='Epochs in a row the mark must be kept.'
              value={hold}
              min={0}
              max={holdMax}
              onChange={setHold}
            />
          )}
          {own && (
            <FormRow label='Name of the goal'>
              {(id) => (
                <Input
                  id={id}
                  value={title}
                  maxLength={TITLE_MAX}
                  className='w-full'
                  onChange={(event) => setTitle(event.target.value)}
                />
              )}
            </FormRow>
          )}
          <DeadlineField
            enabled={timed}
            epochs={epochs}
            max={deadlineMax}
            onEnabled={setTimed}
            onEpochs={setEpochs}
          />
        </div>
        <DialogFooter>
          <ActionButton
            label='Reshape the goal'
            icon={Pencil}
            variant='default'
            blocked={reason() ?? invalid}
            pending={edit.isPending}
            onRun={() => edit.mutate()}
          />
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function DeadlineBadge({
  item,
  epoch,
}: {
  item: RunningScenario
  epoch: number
}) {
  if (item.deadline_epoch === null) return null
  const left = item.deadline_epoch - epoch
  return (
    <Badge size='sm' variant={left <= 1 ? 'destructive' : 'warning'}>
      <CalendarClock />
      {left > 0
        ? `Epoch ${item.deadline_epoch} · ${plural(left, 'epoch', 'epochs')} left`
        : `Due this epoch (${item.deadline_epoch})`}
    </Badge>
  )
}

function RunningGoal({
  item,
  epoch,
  targetMax,
}: {
  item: RunningScenario
  epoch: number
  targetMax: number
}) {
  const { reason } = useGodGate()
  const failed = item.progress.failed
  const hold = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/scenarios/{scenario_id}/hold', {
          params: { path: { scenario_id: item.id } },
          body: { held: !item.held },
        })
      ),
  })
  const abandon = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/scenarios/{scenario_id}/abandon', {
          params: { path: { scenario_id: item.id } },
        })
      ),
  })
  const measure =
    item.metric !== null && item.comparator !== null && item.basis !== null
      ? `${COMPARATOR_LABEL[item.comparator]} · ${BASIS_LABEL[item.basis]}`
      : null
  return (
    <li
      data-running={item.key}
      data-held={item.held || undefined}
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-xl border p-4',
        failed && 'border-destructive/40 bg-destructive/5',
        !failed && item.held && 'border-dashed bg-muted/30',
        !failed && !item.held && 'border-info/40 bg-info/5'
      )}
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={SCENARIO_ICON[item.key]}
          tone={failed ? 'danger' : item.held ? 'muted' : 'info'}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text as='span' weight='semibold' truncate>
            {item.name}
          </Text>
          <Text variant='caption' tone='muted' truncate={2}>
            {item.description}
          </Text>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant='outline'>{`Tier ${roman(item.tier)}`}</Badge>
        <Badge size='sm' variant='outline'>
          {`Target ${formatInteger(item.target)}`}
        </Badge>
        {item.hold_epochs > 0 && (
          <Badge size='sm' variant='outline'>
            {`Hold ${plural(item.hold_epochs, 'epoch', 'epochs')}`}
          </Badge>
        )}
        {measure && (
          <Badge size='sm' variant='secondary'>
            {measure}
          </Badge>
        )}
        <Badge size='sm'>
          <Trophy />
          {`+${formatInteger(item.points)}`}
        </Badge>
        <DeadlineBadge item={item} epoch={epoch} />
        {item.held && (
          <Badge size='sm' variant='secondary'>
            <Pause />
            Held
          </Badge>
        )}
      </div>
      <div className='flex min-w-0 items-center gap-3'>
        <Progress
          className='flex-1'
          value={item.progress.percent}
          tone={failed ? 'destructive' : item.held ? 'muted' : 'info'}
          aria-label={`${item.name} progress`}
        />
        <Text as='span' weight='medium'>{`${item.progress.percent}%`}</Text>
      </div>
      <Text variant='caption' tone={failed ? 'destructive' : 'muted'}>
        {item.progress.done
          ? `${item.progress.text} · reached; it is sealed at the end of the epoch.`
          : item.progress.text}
      </Text>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Label>
          {item.progress.value !== null && item.progress.value !== undefined
            ? `Since epoch ${item.start_epoch} · measured ${formatInteger(item.progress.value)}`
            : `Since epoch ${item.start_epoch}`}
        </Label>
        <div className='flex min-w-0 flex-wrap items-center gap-1'>
          <ActionButton
            label={item.held ? 'Release' : 'Hold'}
            icon={item.held ? Play : Pause}
            size='sm'
            variant='ghost'
            blocked={reason()}
            pending={hold.isPending}
            onRun={() => hold.mutate()}
          />
          <EditGoalDialog item={item} targetMax={targetMax} />
          <ActionButton
            label='Abandon'
            size='sm'
            variant='ghost'
            blocked={reason()}
            pending={abandon.isPending}
            confirm={{
              title: `Abandon ${item.name}?`,
              description: 'The goal ends now and counts as abandoned.',
            }}
            onRun={() => abandon.mutate()}
          />
        </div>
      </div>
    </li>
  )
}

export function RunningGoals({ data }: { data: GoalsOverview }) {
  const rule = useRuleLookup()
  const customMax = rule('goals.custom_target_max') ?? FALLBACK_TARGET
  const limits = new Map(
    data.scenarios.map((scenario) => [scenario.key, scenario.target_max])
  )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{`Running · ${data.running.length}`}</Label>
      {data.running.length === 0 ? (
        <EmptyState
          icon={Flag}
          size='compact'
          title='No running goal'
          description='Set one from the goal board or shape a goal of your own; progress is measured at each epoch end.'
        />
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
          {data.running.map((item) => (
            <RunningGoal
              key={item.id}
              item={item}
              epoch={data.epoch}
              targetMax={
                item.key === 'custom' ? customMax : (limits.get(item.key) ?? 1)
              }
            />
          ))}
        </ul>
      )}
    </div>
  )
}
