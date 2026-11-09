import { useState } from 'react'
import {
  Ban,
  Eye,
  EyeOff,
  Gavel,
  Globe,
  Plus,
  Save,
  Trash2,
  TriangleAlert,
  Undo2,
  Users,
} from 'lucide-react'
import { type ActionBody, type EditValues } from '@/api/actions'
import { actKindValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  LoadingBlock,
  Medallion,
  Paged,
  Section,
  StatBar,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { busyOf } from '@/features/entity/lore/model'
import {
  Card,
  Group,
  Held,
  NumberField,
  SwitchField,
} from '@/features/entity/wilds/parts'
import { useGodGate } from '@/features/pantheon/gate'
import {
  type CreatorDivinity,
  useCreatorDivinity,
  useDivineAction,
} from './api'
import { heldLabel } from './labels'
import { NodeName, PickRow, RegardForm, StandingList } from './parts'

const actLabel = (value: string) =>
  value.replaceAll('_', ' ').replace(/^./, (first) => first.toUpperCase())

function TaboosCard({
  view,
  busy,
}: {
  view: CreatorDivinity
  busy: string | null
}) {
  const [act, setAct] = useState('')
  const [severity, setSeverity] = useState('50')
  const set = useDivineAction(
    'taboo:set',
    (vars: { act: string; severity: number }) => ({
      act: vars.act as ActionBody<'taboo:set'>['act'],
      severity: vars.severity,
    })
  )
  const remove = useDivineAction('taboo:remove', (value: string) => ({
    act: value as ActionBody<'taboo:remove'>['act'],
  }))
  const pending = busyOf(busy, set.isPending, remove.isPending)
  const table = Object.fromEntries(
    actKindValues.map((value) => [value, actLabel(value)])
  )
  const problem = act === '' ? 'Choose an act' : null
  return (
    <Card
      title='Taboos'
      icon={Ban}
      tone='danger'
      hint='Acts that anger the Creator when sons or mortals commit them; the Creator may strike the place of the breaker'
      wide
    >
      {view.taboos.length === 0 ? (
        <EmptyState
          icon={Ban}
          title='No taboo yet'
          description='Name an act the Creator abhors.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={view.taboos} as='li'>
            {(row) => (
              <li
                key={row.act}
                className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
              >
                <div className='flex min-w-0 items-center gap-2'>
                  <Medallion icon={Ban} tone='danger' size='sm' />
                  <div className='flex min-w-0 flex-1 flex-col gap-1'>
                    <Text weight='semibold'>{row.label}</Text>
                    <Muted variant='caption'>
                      {row.broken > 0
                        ? `Broken ${row.broken} times, last in epoch ${row.last_broken_epoch ?? '?'}`
                        : `Kept since epoch ${row.since_epoch}`}
                    </Muted>
                  </div>
                  {row.last_breaker && <NodeName item={row.last_breaker} />}
                  <Button
                    size='sm'
                    variant='ghost'
                    disabled={pending !== null}
                    disabledReason={pending ?? undefined}
                    onClick={() => remove.mutate(row.act)}
                  >
                    <Trash2 />
                    Lift
                  </Button>
                </div>
                <StatBar
                  label='Severity'
                  value={row.severity}
                  max={100}
                  tone='destructive'
                />
              </li>
            )}
          </Paged>
        </ul>
      )}
      <Group title='Name a taboo or change its severity' icon={Plus}>
        <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
          <PickRow
            label='Act'
            table={table}
            value={act}
            blocked={pending}
            onPick={setAct}
          />
          <NumberField
            label='Severity'
            value={severity}
            min={1}
            max={100}
            disabled={pending !== null}
            onChange={setSeverity}
          />
        </div>
        <Button
          disabled={pending !== null || problem !== null}
          disabledReason={pending ?? problem ?? undefined}
          onClick={() => set.mutate({ act, severity: Number(severity) })}
        >
          <Gavel />
          Hold this taboo
        </Button>
      </Group>
    </Card>
  )
}

function AttentionCard({
  view,
  busy,
}: {
  view: CreatorDivinity
  busy: string | null
}) {
  const set = useDivineAction(
    'attention:set',
    (vars: { world: number; values: EditValues; release: string[] }) => ({
      world_id: vars.world,
      values: vars.values,
      release: vars.release,
    })
  )
  const clear = useDivineAction('attention:clear', (world: number) => ({
    world_id: world,
  }))
  const [draft, setDraft] = useState<Record<number, string>>({})
  const pending = busyOf(busy, set.isPending, clear.isPending)
  return (
    <Card
      title='The Creator’s eye'
      icon={Eye}
      tone='gold'
      hint={`Interest is spent on watched worlds; below ${view.far_below} a world is far from the eye and its sons grow bolder`}
      wide
    >
      {view.attention.length === 0 ? (
        <EmptyState
          icon={Globe}
          title='No world watched yet'
          description='The Creator turns its eye on worlds after the next epoch.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={view.attention} as='li'>
            {(row) => (
              <li
                key={row.world.id}
                className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'
              >
                <div className='flex min-w-0 flex-wrap items-center gap-2'>
                  <Medallion
                    icon={row.far ? EyeOff : Eye}
                    tone={row.far ? 'muted' : 'gold'}
                    size='sm'
                  />
                  <NodeName item={row.world} />
                  {row.far && (
                    <Badge size='sm' variant='warning'>
                      Far from the eye
                    </Badge>
                  )}
                </div>
                <StatBar
                  label='Attention'
                  value={row.attention}
                  max={100}
                  icon={Eye}
                  tone={row.far ? 'muted' : 'default'}
                />
                <Held
                  keys={row.locked}
                  label={heldLabel}
                  busy={pending}
                  onRelease={() =>
                    set.mutate({
                      world: row.world.id,
                      values: {},
                      release: row.locked,
                    })
                  }
                />
                <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
                  <SwitchField
                    label='Watched'
                    checked={row.watched}
                    disabled={pending !== null}
                    onChange={(watched) =>
                      set.mutate({
                        world: row.world.id,
                        values: { watched },
                        release: [],
                      })
                    }
                  />
                  <NumberField
                    label='Hold attention at'
                    value={draft[row.world.id] ?? ''}
                    min={0}
                    max={100}
                    disabled={pending !== null}
                    onChange={(text) =>
                      setDraft((old) => ({ ...old, [row.world.id]: text }))
                    }
                  />
                  <div className='flex min-w-0 items-end gap-2'>
                    <Button
                      size='sm'
                      disabled={
                        pending !== null || (draft[row.world.id] ?? '') === ''
                      }
                      disabledReason={
                        pending ??
                        ((draft[row.world.id] ?? '') === ''
                          ? 'Set a value first'
                          : undefined)
                      }
                      onClick={() =>
                        set.mutate({
                          world: row.world.id,
                          values: { attention: Number(draft[row.world.id]) },
                          release: [],
                        })
                      }
                    >
                      <Save />
                      Hold
                    </Button>
                    <Button
                      size='sm'
                      variant='ghost'
                      disabled={pending !== null}
                      disabledReason={pending ?? undefined}
                      onClick={() => clear.mutate(row.world.id)}
                    >
                      <Undo2 />
                      Start afresh
                    </Button>
                  </div>
                </div>
              </li>
            )}
          </Paged>
        </ul>
      )}
    </Card>
  )
}

function CreatorStandingCard({
  view,
  busy,
  creatorId,
}: {
  view: CreatorDivinity
  busy: string | null
  creatorId: number
}) {
  const save = useDivineAction(
    'divine_standing:set',
    (vars: { community: number; values: EditValues; release: string[] }) => ({
      community_id: vars.community,
      god_id: creatorId,
      values: vars.values,
      release: vars.release,
    })
  )
  const clear = useDivineAction(
    'divine_standing:clear',
    (community: number) => ({ community_id: community, god_id: creatorId })
  )
  const pending = busyOf(busy, save.isPending, clear.isPending)
  return (
    <Card
      title='Standing among the peoples'
      icon={Users}
      tone='verdigris'
      hint='How each people regards the Creator'
      wide
    >
      {view.standing.length === 0 && (
        <EmptyState
          icon={Users}
          title='No regard yet'
          description='Every people forms a regard of the Creator after the next epoch.'
        />
      )}
      <StandingList
        rows={view.standing}
        focus='god'
        busy={pending}
        onSave={(row, values, release) =>
          save.mutate({ community: row.community.id, values, release })
        }
        onClear={(row) => clear.mutate(row.community.id)}
      />
      <RegardForm
        busy={pending}
        onSave={(community, values) =>
          save.mutate({ community, values, release: [] })
        }
      />
    </Card>
  )
}

export function CreatorDivinityPanel({ creatorId }: { creatorId: number }) {
  const view = useCreatorDivinity()
  const { reason } = useGodGate()
  const busy = reason()
  return (
    <Section
      id='section-creator-divinity'
      title='Taboos, the eye and standing'
      description='What the Creator abhors, where its eye rests and how the peoples regard it.'
      icon={Eye}
      tone='gold'
    >
      {view.isPending && <LoadingBlock label='Reading the Creator’s regard' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='This could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='CreatorDivinity'
          className='@container/wild grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'
        >
          <TaboosCard view={view.data} busy={busy} />
          <AttentionCard view={view.data} busy={busy} />
          <CreatorStandingCard
            view={view.data}
            busy={busy}
            creatorId={creatorId}
          />
        </div>
      )}
    </Section>
  )
}
