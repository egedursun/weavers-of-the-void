import { useState } from 'react'
import { Play, Trophy } from 'lucide-react'
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
import { EmptyState, Medallion, PagedList } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { CategoryFilter } from './CategoryFilter'
import { CountField, DeadlineField, QuotePreview } from './GoalFields'
import {
  type GoalCategory,
  type GoalsOverview,
  roman,
  SCENARIO_STATUS_LABEL,
  type ScenarioView,
  useGoalQuote,
} from './api'
import {
  DEFAULT_DEADLINE,
  outOfRange,
  parseCount,
  useDeadlineMax,
} from './goalForm'
import { CATEGORY_TONE, SCENARIO_ICON } from './goalIcons'

const SHOWN = 9

function GoalStartDialog({
  scenario,
  running,
}: {
  scenario: ScenarioView
  running: boolean
}) {
  const [open, setOpen] = useState(false)
  const [target, setTarget] = useState(String(scenario.default_target))
  const [timed, setTimed] = useState(false)
  const [epochs, setEpochs] = useState(String(DEFAULT_DEADLINE))
  const deadlineMax = useDeadlineMax()
  const { reason } = useGodGate()
  const chosen = parseCount(target)
  const deadline = timed ? parseCount(epochs) : null
  const invalid =
    outOfRange(chosen, 1, scenario.target_max, 'target') ??
    (timed ? outOfRange(deadline, 1, deadlineMax, 'deadline') : null)
  const quote = useGoalQuote(
    open && invalid === null && chosen !== null
      ? {
          key: scenario.key,
          target: chosen,
          deadline_epochs: deadline ?? undefined,
        }
      : null
  )
  const start = useGodAction({
    writes: [{ lever: 'scenario:start' }],
    run: () =>
      unwrap(
        api.POST('/api/scenarios', {
          body: {
            key: scenario.key,
            target: chosen,
            deadline_epochs: deadline,
          },
        })
      ),
    onDone: () => setOpen(false),
  })
  const blocked =
    reason() ?? (running ? 'This goal is already running.' : invalid)
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (next) setTarget(String(scenario.default_target))
      }}
    >
      <DialogTrigger asChild>
        <Button act={start} size='sm' variant={running ? 'outline' : 'default'}>
          <Play />
          {running ? 'Running' : 'Set this goal'}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{scenario.name}</DialogTitle>
          <DialogDescription>{scenario.description}</DialogDescription>
        </DialogHeader>
        <div className='flex min-w-0 flex-col gap-3'>
          <CountField
            label='Target'
            description={`Tier ${roman(scenario.next_tier)} suggests ${formatInteger(scenario.default_target)}; a higher target is worth more.`}
            value={target}
            min={1}
            max={scenario.target_max}
            onChange={setTarget}
          />
          <DeadlineField
            enabled={timed}
            epochs={epochs}
            max={deadlineMax}
            onEnabled={setTimed}
            onEpochs={setEpochs}
          />
          <QuotePreview
            quote={invalid === null ? quote.data : undefined}
            pending={quote.isFetching}
            deadline={deadline}
          />
        </div>
        <DialogFooter>
          <ActionButton
            act={start}
            label='Begin the goal'
            icon={Play}
            variant='default'
            blocked={blocked}
            pending={start.isPending}
            onRun={() => start.mutate()}
          />
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function GoalCard({
  scenario,
  running,
}: {
  scenario: ScenarioView
  running: boolean
}) {
  const completed = scenario.history.filter(
    (entry) => entry.status === 'completed'
  ).length
  const last = scenario.history.at(-1)
  return (
    <li
      data-scenario={scenario.key}
      data-status={running ? 'running' : (last?.status ?? 'open')}
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4',
        running && 'border-info/40 bg-info/5',
        !running && completed > 0 && 'border-success/40 bg-success/5',
        !running && completed === 0 && 'bg-card'
      )}
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={SCENARIO_ICON[scenario.key]}
          tone={running ? 'info' : CATEGORY_TONE[scenario.category]}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text as='span' weight='semibold'>
            {scenario.name}
          </Text>
          <Muted variant='caption'>{scenario.description}</Muted>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant={completed > 0 ? 'success' : 'outline'}>
          {`Tier ${roman(scenario.next_tier)}`}
        </Badge>
        <Badge size='sm' variant='outline'>
          {`Target ${formatInteger(scenario.default_target)}`}
        </Badge>
        <Badge size='sm'>
          <Trophy />
          {`+${formatInteger(scenario.points)}`}
        </Badge>
        {last && (
          <Badge size='sm' variant='secondary'>
            {`Last: ${SCENARIO_STATUS_LABEL[last.status]}`}
          </Badge>
        )}
      </div>
      <div className='mt-auto flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Label>
          {completed > 0
            ? `${plural(completed, 'time', 'times')} completed`
            : 'Never completed'}
        </Label>
        <GoalStartDialog scenario={scenario} running={running} />
      </div>
    </li>
  )
}

export function GoalBoard({ data }: { data: GoalsOverview }) {
  const [category, setCategory] = useState<GoalCategory | null>(null)
  const presets = data.scenarios.filter((item) => item.key !== 'custom')
  const running = new Set(data.running.map((item) => item.key))
  const counts = data.categories.map((entry) => {
    const inside = presets.filter((item) => item.category === entry.category)
    return {
      category: entry.category,
      label: entry.label,
      done: inside.filter((item) =>
        item.history.some((row) => row.status === 'completed')
      ).length,
      total: inside.length,
    }
  })
  const shown = presets.filter(
    (item) => category === null || item.category === category
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <CategoryFilter
        title={`Goal board · ${presets.length}`}
        counts={counts}
        value={category}
        onChange={setCategory}
      />
      {shown.length === 0 ? (
        <EmptyState
          icon={Trophy}
          size='compact'
          title='No goal in this field'
          description='Choose another field, or set a goal of your own below.'
        />
      ) : (
        <PagedList
          items={shown}
          initial={SHOWN}
          noun={['goal', 'goals']}
          className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-3'
          itemKey={(item) => item.key}
        >
          {(item) => (
            <GoalCard scenario={item} running={running.has(item.key)} />
          )}
        </PagedList>
      )}
    </div>
  )
}
