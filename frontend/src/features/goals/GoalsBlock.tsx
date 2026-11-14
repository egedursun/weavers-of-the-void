import { Link } from '@tanstack/react-router'
import { ArrowRight, Flag, Play, Target, Trophy } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  KpiTile,
  Medallion,
  MiniStat,
  PagedList,
  Section,
  type KpiTone,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { humanize } from '@/features/pantheon/labels'
import { AchievementsGrid } from './AchievementsGrid'
import { ScoreSparkline } from './ScoreSparkline'
import {
  SCENARIO_STATUS_LABEL,
  SCORE_PART_LABEL,
  type ScenarioKey,
  type ScenarioStatus,
  useGoals,
} from './api'
import { SCENARIO_ICON, SCORE_PART_ICON, SCORE_PART_TONE } from './goalIcons'

type Scenario = components['schemas']['ScenarioView']
type Running = components['schemas']['RunningScenario']
type GoalsData = NonNullable<ReturnType<typeof useGoals>['data']>

const STATUS_TONE: Record<ScenarioStatus, KpiTone> = {
  running: 'info',
  completed: 'success',
  failed: 'danger',
  abandoned: 'muted',
}

const STATUS_BADGE: Record<
  ScenarioStatus,
  'info' | 'success' | 'destructive' | 'outline'
> = {
  running: 'info',
  completed: 'success',
  failed: 'destructive',
  abandoned: 'outline',
}

function signed(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}

function ScorePanel({ data }: { data: GoalsData }) {
  const parts = Object.entries(data.score.parts ?? {})
  const total = parts.reduce((sum, [, value]) => sum + value, 0)
  const completed = data.scenarios.reduce(
    (sum, scenario) =>
      sum +
      scenario.history.filter((entry) => entry.status === 'completed').length,
    0
  )
  const earned = data.achievements.filter((item) => item.earned).length
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-1 gap-3 lg:grid-cols-3'>
        <KpiTile
          label='Score'
          icon={Trophy}
          value={total}
          hint={`${completed} goals completed · ${earned}/${plural(data.achievements.length, 'achievement', 'achievements')}`}
        />
        <div className='flex min-w-0 flex-col gap-2 rounded-xl border bg-background p-4 lg:col-span-2'>
          <Label variant='overline'>Score over the epochs</Label>
          {data.score_history.length < 2 ? (
            <Muted variant='caption'>
              The score is measured at the end of each epoch.
            </Muted>
          ) : (
            <ScoreSparkline history={data.score_history} />
          )}
        </div>
      </div>
      {parts.length > 0 && (
        <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
          {parts.map(([key, value]) => (
            <MiniStat
              key={key}
              icon={SCORE_PART_ICON[key] ?? Flag}
              tone={value < 0 ? 'danger' : (SCORE_PART_TONE[key] ?? 'muted')}
              label={SCORE_PART_LABEL[key] ?? humanize(key)}
              value={signed(value)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function RunningGoal({
  item,
  onAbandon,
  pending,
  blocked,
}: {
  item: Running
  onAbandon: () => void
  pending: boolean
  blocked: string | null
}) {
  const failed = item.progress.failed
  return (
    <li
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-xl border p-4',
        failed
          ? 'border-destructive/40 bg-destructive/5'
          : 'border-info/40 bg-info/5'
      )}
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={SCENARIO_ICON[item.key]}
          tone={failed ? 'danger' : 'info'}
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='semibold' truncate>
            {item.name}
          </Text>
          <Label>{`Since Epoch ${item.start_epoch}`}</Label>
        </div>
        <ActionButton
          label='Abandon'
          size='sm'
          variant='ghost'
          blocked={blocked}
          pending={pending}
          confirm={{
            title: `Abandon ${item.name}?`,
            description: 'The goal ends now and counts as abandoned.',
          }}
          onRun={onAbandon}
        />
      </div>
      <div className='flex min-w-0 items-center gap-3'>
        <Progress
          className='flex-1'
          value={item.progress.percent}
          tone={failed ? 'destructive' : 'info'}
          aria-label={`${item.name} progress`}
        />
        <Text
          as='span'
          weight='medium'
        >{`${Math.round(item.progress.percent)}%`}</Text>
      </div>
      <Text variant='caption' tone={failed ? 'destructive' : 'muted'}>
        {item.progress.text}
      </Text>
    </li>
  )
}

function GoalCard({
  scenario,
  running,
  onStart,
  pending,
  blocked,
}: {
  scenario: Scenario
  running: boolean
  onStart: () => void
  pending: boolean
  blocked: string | null
}) {
  const last = scenario.history.at(-1)
  const status: ScenarioStatus | null = running
    ? 'running'
    : (last?.status ?? null)
  const done = status === 'completed'
  return (
    <li
      data-scenario={scenario.key}
      data-status={status ?? 'open'}
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-xl border p-4',
        done ? 'border-success/40 bg-success/5' : 'bg-background'
      )}
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={SCENARIO_ICON[scenario.key]}
          tone={status ? STATUS_TONE[status] : 'gold'}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text as='span' weight='semibold'>
            {scenario.name}
          </Text>
          <Muted variant='caption'>{scenario.description}</Muted>
        </div>
        <Badge size='sm' variant={done ? 'success' : 'default'}>
          <Trophy />
          {`+${scenario.points}`}
        </Badge>
      </div>
      {scenario.history.length > 0 && (
        <PagedList
          items={scenario.history}
          initial={5}
          noun={['entry', 'entries']}
          className='flex min-w-0 flex-col gap-1.5'
          itemKey={(entry) => entry.id}
        >
          {(entry) => (
            <li className='flex min-w-0 flex-col gap-1 rounded-lg border bg-muted/30 p-2'>
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Badge size='sm' variant={STATUS_BADGE[entry.status]}>
                  {SCENARIO_STATUS_LABEL[entry.status]}
                </Badge>
                <Label>
                  {`Epoch ${entry.start_epoch}${entry.end_epoch !== null ? ` to ${entry.end_epoch}` : ''}`}
                </Label>
              </div>
              {entry.result && (
                <Muted variant='caption' truncate={2}>
                  {entry.result}
                </Muted>
              )}
            </li>
          )}
        </PagedList>
      )}
      <div className='mt-auto flex min-w-0 items-center justify-end'>
        <ActionButton
          label='Start'
          icon={Play}
          size='sm'
          variant={done ? 'outline' : 'default'}
          blocked={blocked ?? (running ? 'Already running.' : null)}
          pending={pending}
          onRun={onStart}
        />
      </div>
    </li>
  )
}

export function GoalsBlock({
  achievementsOpen = false,
  summary = false,
}: {
  achievementsOpen?: boolean
  summary?: boolean
}) {
  const goals = useGoals()
  const { reason } = useGodGate()
  const start = useGodAction({
    run: (key: ScenarioKey) =>
      unwrap(api.POST('/api/scenarios', { body: { key } })),
    success: 'You set yourself a new goal',
  })
  const abandon = useGodAction({
    run: (scenarioId: number) =>
      unwrap(
        api.POST('/api/scenarios/{scenario_id}/abandon', {
          params: { path: { scenario_id: scenarioId } },
        })
      ),
    success: 'Goal abandoned',
  })
  const evaluate = useGodAction({
    run: () => unwrap(api.POST('/api/actions/goals:evaluate')),
    success: 'Goals measured',
  })
  if (goals.isPending) return <Skeleton className='h-textarea w-full' />
  if (goals.isError)
    return <Text tone='destructive'>{goals.error.message}</Text>
  const data = goals.data
  const running = new Set(data.running.map((item) => item.key))
  const runningList =
    data.running.length === 0 ? (
      <EmptyState
        icon={Flag}
        size='compact'
        title='No running goal'
        description='Pick one from the goal board; progress is measured at each epoch end.'
      />
    ) : (
      <ul className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        {data.running.map((item) => (
          <RunningGoal
            key={item.id}
            item={item}
            blocked={reason()}
            pending={abandon.isPending}
            onAbandon={() => abandon.mutate(item.id)}
          />
        ))}
      </ul>
    )
  return (
    <Section
      title='Your goals'
      description='Optional: set yourself a goal; progress is measured automatically at the end of each epoch.'
      actions={
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {summary && (
            <Button variant='outline' asChild>
              <Link to='/goals'>
                <ArrowRight />
                Goal board
              </Link>
            </Button>
          )}
          <ActionButton
            label='Measure now'
            icon={Target}
            blocked={reason()}
            pending={evaluate.isPending}
            onRun={() => evaluate.mutate()}
          />
        </div>
      }
    >
      <ScorePanel data={data} />
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>{`Running · ${data.running.length}`}</Label>
        {runningList}
      </div>
      {!summary && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>{`Goal board · ${data.scenarios.length}`}</Label>
          <ul className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-3'>
            {data.scenarios.map((scenario) => (
              <GoalCard
                key={scenario.key}
                scenario={scenario}
                running={running.has(scenario.key)}
                blocked={reason()}
                pending={start.isPending}
                onStart={() => start.mutate(scenario.key)}
              />
            ))}
          </ul>
        </div>
      )}
      <AchievementsGrid
        achievements={data.achievements}
        defaultOpen={achievementsOpen}
      />
    </Section>
  )
}
