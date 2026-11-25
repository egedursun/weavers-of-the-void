import { Compass } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Label, Muted, Text } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Chip, type Field, RecordEditor } from '@/features/cosmography/parts'
import { NamedRecord } from '@/features/entity/NamedRecord'
import { useMadeAction } from '@/features/minds/api'
import {
  AIMS,
  OBSTACLES,
  QUEST_TARGETS,
  REWARDS,
  SCALES,
} from '@/features/typedModels/labels'
import { useCosmos } from './api'
import {
  OUTCOME_LABEL,
  OUTCOME_VARIANT,
  DECLARER_LABEL,
  PERCENT,
  countdownText,
  expeditionProgress,
} from './expeditionFormat'
import { type GreatExpedition } from './expeditionsApi'

function RouteName({ id }: { id: number }) {
  const cosmos = useCosmos()
  const route = cosmos.data?.routes.find((item) => item.id === id)
  const world = (worldId: number) =>
    cosmos.data?.worlds.find((item) => item.world.id === worldId)?.world.name ??
    'a lost world'
  return (
    <Text as='span' variant='caption'>
      {route
        ? `the road ${world(route.world_a_id)} to ${world(route.world_b_id)}`
        : 'a road now gone'}
    </Text>
  )
}

function ExpeditionAim({ expedition }: { expedition: GreatExpedition }) {
  const aims = [
    expedition.target_star_id !== null && (
      <NamedRecord
        key='star'
        id={expedition.target_star_id}
        fallback='a star'
      />
    ),
    expedition.target_route_id !== null && (
      <RouteName key='route' id={expedition.target_route_id} />
    ),
    expedition.target_entity_id !== null && (
      <NamedRecord
        key='entity'
        id={expedition.target_entity_id}
        fallback='a record'
      />
    ),
  ].filter(Boolean)
  if (aims.length === 0) return null
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
      <Label>Its aim</Label>
      {aims}
    </div>
  )
}

const QUEST_FIELDS: readonly Field[] = [
  { key: 'aim', label: 'Aim', kind: 'pick', table: table(AIMS) },
  {
    key: 'target_kind',
    label: 'What it seeks',
    kind: 'pick',
    table: table(QUEST_TARGETS),
  },
  {
    key: 'obstacle',
    label: 'What stands in the way',
    kind: 'pick',
    table: table(OBSTACLES),
  },
  { key: 'reward', label: 'Reward', kind: 'pick', table: table(REWARDS) },
  { key: 'scale', label: 'Scale', kind: 'pick', table: table(SCALES) },
]

function QuestEditor({ expedition }: { expedition: GreatExpedition }) {
  const editing = useMadeAction(
    'legendary_quest:edit',
    (vars: { values: EditValues; release: string[] }) => ({
      thread_id: expedition.thread_id,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The legendary quest is set so'
  )
  return (
    <RecordEditor
      act={editing}
      title='Set the legendary quest'
      note='Values you set are held against the engine until you release them.'
      fields={QUEST_FIELDS}
      locked={expedition.locked}
      busy={editing.isPending ? 'Working on it.' : null}
      onSave={(values) => editing.mutate({ values, release: [] })}
      onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
    />
  )
}

export function ExpeditionCard({
  expedition,
}: {
  expedition: GreatExpedition
}) {
  const open = expedition.outcome === null
  return (
    <article
      data-expedition-id={expedition.thread_id}
      className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Compass
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-primary'
        />
        <Text as='span' weight='medium' truncate className='min-w-0 flex-1'>
          {expedition.name}
        </Text>
        <Badge
          size='sm'
          variant={
            expedition.outcome ? OUTCOME_VARIANT[expedition.outcome] : 'default'
          }
        >
          {expedition.outcome ? OUTCOME_LABEL[expedition.outcome] : 'Under way'}
        </Badge>
        <Badge
          size='sm'
          variant={
            expedition.thread_status === 'open' ? 'outline' : 'secondary'
          }
        >
          {expedition.thread_status === 'open' ? 'Story open' : 'Story closed'}
        </Badge>
      </div>
      <Muted variant='caption'>{expedition.text}</Muted>
      <ExpeditionAim expedition={expedition} />
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip
          icon={AIMS[expedition.aim].icon}
        >{`${AIMS[expedition.aim].label} ${QUEST_TARGETS[expedition.target_kind].label.toLowerCase()}`}</Chip>
        <Chip
          icon={OBSTACLES[expedition.obstacle].icon}
        >{`In the way: ${OBSTACLES[expedition.obstacle].label.toLowerCase()}`}</Chip>
        <Chip
          icon={REWARDS[expedition.reward].icon}
        >{`Reward: ${REWARDS[expedition.reward].label.toLowerCase()}`}</Chip>
        <Chip icon={SCALES[expedition.scale].icon}>
          {SCALES[expedition.scale].label}
        </Chip>
      </div>
      <QuestEditor expedition={expedition} />
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Badge
          size='sm'
          variant='outline'
        >{`Declared by ${DECLARER_LABEL[expedition.declared_by]}`}</Badge>
        <Badge
          size='sm'
          variant='outline'
        >{`Opened in epoch ${expedition.opened_epoch}`}</Badge>
        <Badge
          size='sm'
          variant='outline'
        >{`Deadline: epoch ${expedition.deadline_epoch}`}</Badge>
      </div>
      <Progress
        value={expeditionProgress(expedition) * PERCENT}
        size='sm'
        tone={
          open
            ? expedition.epochs_remaining <= 1
              ? 'warning'
              : 'default'
            : expedition.outcome === 'completed'
              ? 'success'
              : 'muted'
        }
        aria-label='Time until the deadline'
      />
      <Label>{countdownText(expedition)}</Label>
    </article>
  )
}

export function ExpeditionNote({
  expedition,
}: {
  expedition: GreatExpedition
}) {
  return (
    <div
      data-expedition-note={expedition.thread_id}
      className='flex min-w-0 flex-col gap-2'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Badge size='sm' variant='default'>
          <Compass aria-hidden='true' />
          {expedition.name}
        </Badge>
        <Badge
          size='sm'
          variant={
            expedition.outcome ? OUTCOME_VARIANT[expedition.outcome] : 'outline'
          }
        >
          {countdownText(expedition)}
        </Badge>
        <Badge
          size='sm'
          variant='outline'
        >{`Opened ${expedition.opened_epoch} · deadline ${expedition.deadline_epoch}`}</Badge>
      </div>
      <Progress
        value={expeditionProgress(expedition) * PERCENT}
        size='sm'
        tone={
          expedition.outcome === null
            ? 'default'
            : expedition.outcome === 'completed'
              ? 'success'
              : 'muted'
        }
        aria-label='Time until the deadline'
      />
    </div>
  )
}
