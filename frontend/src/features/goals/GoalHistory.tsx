import { History, Trash2, Trophy } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { EmptyState, Medallion, PagedList } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type GoalsOverview,
  roman,
  type ScenarioHistory,
  type ScenarioKey,
  SCENARIO_STATUS_LABEL,
  type ScenarioStatus,
} from './api'
import { SCENARIO_ICON } from './goalIcons'

const SHOWN = 6

const STATUS_BADGE: Record<
  ScenarioStatus,
  'info' | 'success' | 'destructive' | 'outline'
> = {
  running: 'info',
  completed: 'success',
  failed: 'destructive',
  abandoned: 'outline',
}

const STATUS_TONE: Record<
  ScenarioStatus,
  'info' | 'success' | 'danger' | 'muted'
> = {
  running: 'info',
  completed: 'success',
  failed: 'danger',
  abandoned: 'muted',
}

type Entry = ScenarioHistory & { key: ScenarioKey }

function HistoryEntry({ entry }: { entry: Entry }) {
  const { reason } = useGodGate()
  const strike = useGodAction({
    writes: [{ lever: 'scenario:delete' }],
    run: () =>
      unwrap(
        api.POST('/api/scenarios/{scenario_id}/delete', {
          params: { path: { scenario_id: entry.id } },
        })
      ),
  })
  const reward =
    entry.status === 'completed'
      ? `+${formatInteger(entry.awarded_points)} of ${formatInteger(entry.points)}`
      : `Worth ${formatInteger(entry.points)}`
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={SCENARIO_ICON[entry.key]}
          tone={STATUS_TONE[entry.status]}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text as='span' weight='semibold' truncate>
            {entry.name}
          </Text>
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Badge size='sm' variant={STATUS_BADGE[entry.status]}>
              {SCENARIO_STATUS_LABEL[entry.status]}
            </Badge>
            <Badge
              size='sm'
              variant='outline'
            >{`Tier ${roman(entry.tier)}`}</Badge>
            <Badge size='sm' variant='outline'>
              {`Target ${formatInteger(entry.target)}`}
            </Badge>
            <Badge
              size='sm'
              variant={entry.awarded_points > 0 ? 'default' : 'outline'}
            >
              <Trophy />
              {reward}
            </Badge>
          </div>
        </div>
        <ActionButton
          act={strike}
          label='Strike'
          icon={Trash2}
          size='sm'
          variant='ghost'
          blocked={reason()}
          pending={strike.isPending}
          confirm={{
            title: `Strike ${entry.name} from the record?`,
            description:
              'The record is removed and any points it earned leave the score.',
          }}
          onRun={() => strike.mutate()}
        />
      </div>
      <Label>
        {`Epoch ${entry.start_epoch}${entry.end_epoch !== null ? ` to ${entry.end_epoch}` : ''}${entry.deadline_epoch !== null ? ` · deadline ${entry.deadline_epoch}` : ''}`}
      </Label>
      {entry.result && (
        <Muted variant='caption' truncate={2}>
          {entry.result}
        </Muted>
      )}
    </li>
  )
}

export function GoalHistory({ data }: { data: GoalsOverview }) {
  const entries: Entry[] = data.scenarios
    .flatMap((scenario) =>
      scenario.history.map((entry) => ({ ...entry, key: scenario.key }))
    )
    .filter((entry) => entry.status !== 'running')
    .sort(
      (first, second) =>
        (second.end_epoch ?? 0) - (first.end_epoch ?? 0) || second.id - first.id
    )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{`Record of goals · ${entries.length}`}</Label>
      {entries.length === 0 ? (
        <EmptyState
          icon={History}
          size='compact'
          title='No goal has ended yet'
          description='Completed, failed and abandoned goals are kept here with the points they earned.'
        />
      ) : (
        <PagedList
          items={entries}
          initial={SHOWN}
          noun={['record', 'records']}
          className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'
          itemKey={(entry) => entry.id}
        >
          {(entry) => <HistoryEntry entry={entry} />}
        </PagedList>
      )}
    </div>
  )
}
