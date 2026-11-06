import { useState } from 'react'
import { Lock, Minus, Moon, Plus, Send, Unlock, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Paged,
  Section,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Label, Muted, Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type DreamKind,
  type DreamReading,
  type Emotion,
  type FeelingDream,
  type FeelingGrief,
  type FeelingThought,
  type Feelings,
  type GriefStage,
  type ThoughtKind,
  signed,
  useFeelings,
} from '../mind/api'
import {
  DREAM_ICON,
  DREAM_KINDS,
  EMOTION_ICONS,
  FEELINGS_ICON,
  GRIEF_ICON,
  GRIEF_STAGES,
  MOOD_ICONS,
  READING_ICON,
} from '../mind/feelingLabels'
import { LOCKS, named, plain } from '../mind/labels'
import { ControlPanel, MindCard, MindPicker } from '../mind/parts'

const PERCENT = 100
const STEP = 10
const WORKING = 'Working on it.'

function nodeKind(kind: string): DrawerKind {
  if (kind === 'son') return 'son'
  if (kind === 'foreign_god') return 'foreign-god'
  return 'entity'
}

function NodeChip({
  node,
}: {
  node: { id: number; kind: string; name: string }
}) {
  return (
    <EntityLink kind={nodeKind(node.kind)} id={String(node.id)} showIcon>
      {node.name}
    </EntityLink>
  )
}

function FeelingsHero({ view }: { view: Feelings }) {
  const mood = named(MOOD_ICONS, view.mood ?? 'fine')
  const strongest = view.emotions[0]
  const mourning = view.griefs.filter(
    (item) => item.stage === 'shock' || item.stage === 'mourning'
  ).length
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @md/feel:grid-cols-2 @3xl/feel:grid-cols-4'>
      <KpiTile
        label='Mood'
        value={`${mood.label} ${signed(view.mood_score)}`}
        icon={mood.icon}
        tone={mood.tone}
        hint={view.mood_held ? 'Held by you' : 'The sum of recent feelings'}
      />
      <KpiTile
        label='Strongest feeling'
        value={strongest ? `${strongest.label} ${strongest.strength}` : 'None'}
        icon={
          strongest
            ? named(EMOTION_ICONS, strongest.emotion).icon
            : FEELINGS_ICON
        }
        tone={strongest && strongest.valence < 0 ? 'danger' : 'success'}
      />
      <KpiTile
        label='Formative memories'
        value={view.formative.length}
        icon={READING_ICON}
        tone='verdigris'
        hint={`Feelings of ${view.long_term_threshold} or more are kept for life`}
      />
      <KpiTile
        label='Mourning'
        value={mourning}
        icon={GRIEF_ICON}
        tone='info'
        hint={`${view.dreams.length} dreams recorded`}
      />
    </div>
  )
}

function ThoughtRow({
  item,
  blocked,
  onNudge,
  onRemove,
}: {
  item: FeelingThought
  blocked: string | null
  onNudge: (intensity: number) => void
  onRemove: () => void
}) {
  const spec = named(EMOTION_ICONS, item.emotion)
  return (
    <div className='flex min-w-0 flex-col gap-1.5 rounded-md border bg-muted/20 p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion
          icon={spec.icon}
          size='sm'
          tone={item.valence < 0 ? 'danger' : 'success'}
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {item.label}
          </Text>
          <Muted variant='caption' truncate>
            {`${item.emotion_label} · epoch ${item.epoch} · fades ${item.decay_pct}% an epoch`}
          </Muted>
        </div>
        {item.formative && <Badge variant='outline'>Formative</Badge>}
      </div>
      {item.subject && <NodeChip node={item.subject} />}
      <div className='flex min-w-0 items-center gap-2'>
        <Progress
          value={item.strength}
          size='sm'
          tone={item.valence < 0 ? 'destructive' : 'success'}
          aria-label={`${item.label} strength`}
        />
        <Muted variant='caption'>{`${item.strength}/${item.intensity}`}</Muted>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Soften ${item.label}`}
          disabled={blocked !== null || item.intensity <= 0}
          disabledReason={blocked ?? 'It is already as soft as it gets.'}
          onClick={() => onNudge(Math.max(0, item.intensity - STEP))}
        >
          <Minus />
        </Button>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Sharpen ${item.label}`}
          disabled={blocked !== null || item.intensity >= PERCENT}
          disabledReason={blocked ?? 'It is already as sharp as it gets.'}
          onClick={() => onNudge(Math.min(PERCENT, item.intensity + STEP))}
        >
          <Plus />
        </Button>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Take away ${item.label}`}
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={onRemove}
        >
          <X />
        </Button>
      </div>
    </div>
  )
}

function Thoughts({
  view,
  blocked,
}: {
  view: Feelings
  blocked: string | null
}) {
  const nudge = useGodAction({
    run: ({ id, intensity }: { id: number; intensity: number }) =>
      unwrap(
        api.POST('/api/actions/thought:edit', {
          body: { thought_id: id, intensity, clear_subject: false },
        })
      ),
  })
  const remove = useGodAction({
    run: (id: number) =>
      unwrap(
        api.POST('/api/actions/thought:remove', { body: { thought_id: id } })
      ),
  })
  const busy = blocked ?? (nudge.isPending || remove.isPending ? WORKING : null)
  return (
    <MindCard
      title='Thoughts and feelings'
      icon={FEELINGS_ICON}
      hint='What this mortal lived through, each with one feeling their temperament sharpens or dulls. Feelings fade each epoch; the strongest are kept for life.'
      wide
    >
      {view.emotions.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {view.emotions.slice(0, 6).map((item) => {
            const spec = named(EMOTION_ICONS, item.emotion)
            return (
              <Badge
                key={item.emotion}
                variant={item.valence < 0 ? 'outline' : 'default'}
              >
                <spec.icon aria-hidden='true' />
                {`${item.label} ${item.strength}`}
              </Badge>
            )
          })}
        </div>
      )}
      {view.thoughts.length === 0 ? (
        <EmptyState
          icon={FEELINGS_ICON}
          size='compact'
          title='No thoughts yet'
          description='The next epoch gives this mortal thoughts from what they live through and what they need.'
        />
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/feel:grid-cols-2'>
          <Paged
            items={view.thoughts}
            initial={6}
            noun={['thought', 'thoughts']}
          >
            {(item) => (
              <ThoughtRow
                key={item.id}
                item={item}
                blocked={busy}
                onNudge={(intensity) =>
                  nudge.mutate({ id: item.id, intensity })
                }
                onRemove={() => remove.mutate(item.id)}
              />
            )}
          </Paged>
        </div>
      )}
    </MindCard>
  )
}

function Formative({ view }: { view: Feelings }) {
  if (view.formative.length === 0) return null
  return (
    <MindCard
      title='Formative memories'
      icon={READING_ICON}
      hint='Feelings strong enough to shape beliefs and temperament for good. They come back on anniversaries and when their subject is near.'
    >
      <Paged items={view.formative} initial={4} noun={['memory', 'memories']}>
        {(item) => (
          <div
            key={item.id}
            className='flex min-w-0 flex-col gap-0.5 rounded-md border p-2'
          >
            <Text weight='semibold' truncate>
              {item.label}
            </Text>
            <Muted variant='caption'>
              {`${item.magnitude < 0 ? 'A wound' : 'A joy'} of ${Math.abs(item.magnitude)} · epoch ${item.epoch}`}
            </Muted>
            {item.subject && <NodeChip node={item.subject} />}
          </div>
        )}
      </Paged>
    </MindCard>
  )
}

function GriefCard({
  item,
  blocked,
  onStage,
  onRemove,
}: {
  item: FeelingGrief
  blocked: string | null
  onStage: (stage: GriefStage) => void
  onRemove: () => void
}) {
  const stage = named(GRIEF_STAGES, item.stage)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border bg-muted/20 p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={stage.icon} size='sm' tone={stage.tone} />
        <div className='flex min-w-0 flex-1 flex-col'>
          {item.deceased ? (
            <NodeChip node={item.deceased} />
          ) : (
            <Text>Someone lost</Text>
          )}
          <Muted variant='caption'>
            {`Since epoch ${item.started_epoch} · mourning lasts ${item.length_epochs} epochs`}
          </Muted>
        </div>
        <Badge variant='outline'>{stage.label}</Badge>
      </div>
      <Progress
        value={item.strength}
        size='sm'
        tone='default'
        aria-label='Strength of the grief'
      />
      <div className='flex min-w-0 items-end gap-2'>
        <div className='min-w-0 flex-1'>
          <MindPicker
            label='Stage'
            value={item.stage}
            table={Object.fromEntries(
              Object.entries(GRIEF_STAGES).map(([key, value]) => [
                key,
                value.label,
              ])
            )}
            blocked={blocked}
            onPick={(value) => onStage(value as GriefStage)}
          />
        </div>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label='Lift this grief'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={onRemove}
        >
          <X />
        </Button>
      </div>
    </div>
  )
}

function Griefs({ view, blocked }: { view: Feelings; blocked: string | null }) {
  const stage = useGodAction({
    run: ({ id, next }: { id: number; next: GriefStage }) =>
      unwrap(
        api.POST('/api/actions/grief:edit', {
          body: { grief_id: id, stage: next },
        })
      ),
  })
  const remove = useGodAction({
    run: (id: number) =>
      unwrap(api.POST('/api/actions/grief:remove', { body: { grief_id: id } })),
  })
  const busy = blocked ?? (stage.isPending || remove.isPending ? WORKING : null)
  return (
    <MindCard
      title='Grief'
      icon={GRIEF_ICON}
      hint='Shock, then mourning stretched by the mourning rites of their people, then acceptance or a grief that will not heal.'
    >
      {view.griefs.length === 0 ? (
        <EmptyState
          icon={GRIEF_ICON}
          size='compact'
          title='No grief'
          description='This mortal mourns no one.'
        />
      ) : (
        <Paged items={view.griefs} initial={3} noun={['grief', 'griefs']}>
          {(item) => (
            <GriefCard
              key={item.id}
              item={item}
              blocked={busy}
              onStage={(next) => stage.mutate({ id: item.id, next })}
              onRemove={() => remove.mutate(item.id)}
            />
          )}
        </Paged>
      )}
    </MindCard>
  )
}

function DreamCard({
  item,
  readings,
  blocked,
  onRead,
  onRemove,
}: {
  item: FeelingDream
  readings: Record<string, string>
  blocked: string | null
  onRead: (reading: DreamReading) => void
  onRemove: () => void
}) {
  const kind = named(DREAM_KINDS, item.kind)
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border bg-muted/20 p-2'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={kind.icon} size='sm' tone={kind.tone} />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {item.label}
          </Text>
          <Muted variant='caption'>{`Epoch ${item.epoch} · intensity ${item.intensity}`}</Muted>
        </div>
        {item.recurring && <Badge variant='outline'>Recurring</Badge>}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {item.sender && <NodeChip node={item.sender} />}
        {item.partner && <NodeChip node={item.partner} />}
        {item.world && <NodeChip node={item.world} />}
        {item.content
          .filter(
            (node) =>
              node.id !== item.sender?.id && node.id !== item.partner?.id
          )
          .map((node) => (
            <NodeChip key={node.id} node={node} />
          ))}
      </div>
      <div className='flex min-w-0 items-end gap-2'>
        <div className='min-w-0 flex-1'>
          <MindPicker
            label={
              item.reader
                ? `Read by ${item.reader.name}${item.reading_true === null ? '' : item.reading_true ? ', truly' : ', wrongly'}`
                : 'How it was read'
            }
            value={item.reading}
            table={readings}
            blocked={blocked}
            onPick={(value) => onRead(value as DreamReading)}
          />
        </div>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Forget ${item.label}`}
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={onRemove}
        >
          <X />
        </Button>
      </div>
    </div>
  )
}

function Dreams({ view, blocked }: { view: Feelings; blocked: string | null }) {
  const read = useGodAction({
    run: ({ id, reading }: { id: number; reading: DreamReading }) =>
      unwrap(
        api.POST('/api/actions/dream:edit', {
          body: { dream_id: id, reading, clear_reader: false },
        })
      ),
  })
  const remove = useGodAction({
    run: (id: number) =>
      unwrap(api.POST('/api/actions/dream:remove', { body: { dream_id: id } })),
  })
  const busy = blocked ?? (read.isPending || remove.isPending ? WORKING : null)
  const readings = Object.fromEntries(
    view.readings.map((item) => [item.key, item.label])
  )
  return (
    <MindCard
      title='Dreams'
      icon={DREAM_ICON}
      hint='Nightmares from fears and wounds, longing from unmet needs, prophecy for seers, shared dreams for lovers and visitations from gods. Dream readers turn them into omens.'
      wide
    >
      {view.dreams.length === 0 ? (
        <EmptyState
          icon={DREAM_ICON}
          size='compact'
          title='No dreams recorded'
          description='Named mortals dream as the epochs pass; you can send one below.'
        />
      ) : (
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/feel:grid-cols-2'>
          <Paged items={view.dreams} initial={4} noun={['dream', 'dreams']}>
            {(item) => (
              <DreamCard
                key={item.id}
                item={item}
                readings={readings}
                blocked={busy}
                onRead={(reading) => read.mutate({ id: item.id, reading })}
                onRemove={() => remove.mutate(item.id)}
              />
            )}
          </Paged>
        </div>
      )}
    </MindCard>
  )
}

function FeelingControls({ view }: { view: Feelings }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(true)
  const [kind, setKind] = useState<string>('sent_by_the_creator')
  const [emotion, setEmotion] = useState<string>('')
  const [dreamKind, setDreamKind] = useState<string>('visitation')
  const [lost, setLost] = useState<string | null>(null)
  const names = useNames()
  const lock = useGodAction({
    run: (field: string) =>
      unwrap(
        api.POST('/api/actions/mind:lock', {
          body: { node_id: view.node_id, field },
        })
      ),
  })
  const release = useGodAction({
    run: (field: string) =>
      unwrap(
        api.POST('/api/actions/mind:unlock', {
          body: { node_id: view.node_id, field },
        })
      ),
  })
  const send = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/thought:send', {
          body: {
            holder_id: view.node_id,
            kind: kind as ThoughtKind,
            emotion: emotion === '' ? null : (emotion as Emotion),
            intensity: 60,
          },
        })
      ),
  })
  const dream = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/dream:send', {
          body: {
            dreamer_id: view.node_id,
            kind: dreamKind as DreamKind,
            intensity: 60,
            reading: 'unread',
          },
        })
      ),
  })
  const mourn = useGodAction({
    run: (deceased: number) =>
      unwrap(
        api.POST('/api/actions/grief:start', {
          body: {
            mourner_id: view.node_id,
            deceased_id: deceased,
            strength: 70,
          },
        })
      ),
    onDone: () => setLost(null),
  })
  const busy =
    reason() ??
    (lock.isPending ||
    release.isPending ||
    send.isPending ||
    dream.isPending ||
    mourn.isPending
      ? WORKING
      : null)
  const held = new Set(view.locked)
  const thoughtChoices = Object.fromEntries(
    view.thought_kinds.map((item) => [item.kind, item.label])
  )
  const emotionChoices = Object.fromEntries(
    view.emotion_kinds.map((item) => [item.emotion, item.label])
  )
  const dreamChoices = Object.fromEntries(
    view.dream_kinds.map((item) => [item.key, item.label])
  )
  const people = (names.data ?? [])
    .filter((entry) => entry.id !== view.node_id && entry.type === 'mortal')
    .map((entry) => ({ value: String(entry.id), label: entry.name }))
  const setMood = ({ value }: { key: string; value: number }) =>
    unwrap(
      api.POST('/api/actions/thought:mood', {
        body: { node_id: view.node_id, score: value, hold },
      })
    )
  return (
    <ControlPanel
      title='Shape feelings, grief and dreams'
      note='Send a thought, a dream or a grief, set the mood, and hold any part so the world stops changing it until you release it. Every change goes into the ledger and can be undone.'
      hold={hold}
      onHold={setHold}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {view.lockable.map((field) =>
          held.has(field) ? (
            <Button
              key={field}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => release.mutate(field)}
            >
              <Unlock />
              {`Release ${plain(LOCKS, field)}`}
            </Button>
          ) : (
            <Button
              key={field}
              size='sm'
              variant='ghost'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => lock.mutate(field)}
            >
              <Lock />
              {`Hold ${plain(LOCKS, field)}`}
            </Button>
          )
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/feel:grid-cols-3'>
        <div className='flex min-w-0 flex-col gap-2 rounded-md border border-dashed p-2'>
          <MindPicker
            label='Send a thought'
            value={kind}
            table={thoughtChoices}
            blocked={busy}
            onPick={setKind}
          />
          <MindPicker
            label='With the feeling'
            value={emotion}
            table={emotionChoices}
            blocked={busy}
            placeholder='Its usual feeling'
            onPick={setEmotion}
          />
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => send.mutate()}
          >
            <Send />
            Send
          </Button>
        </div>
        <div className='flex min-w-0 flex-col gap-2 rounded-md border border-dashed p-2'>
          <MindPicker
            label='Send a dream'
            value={dreamKind}
            table={dreamChoices}
            blocked={busy}
            onPick={setDreamKind}
          />
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => dream.mutate()}
          >
            <Moon />
            Send the dream
          </Button>
        </div>
        <div className='flex min-w-0 flex-col gap-2 rounded-md border border-dashed p-2'>
          <Label>Make them mourn</Label>
          <RecordCombobox
            options={people}
            value={lost}
            onChange={(next) => setLost(next)}
            placeholder='Choose who they lost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            aria-label='Who they mourn'
          />
          <Button
            size='sm'
            disabled={busy !== null || lost === null}
            disabledReason={busy ?? 'Choose who they mourn first.'}
            onClick={() => mourn.mutate(Number(lost))}
          >
            <Plus />
            Begin mourning
          </Button>
        </div>
      </div>
      <AdjustStats
        id={`feelings-${view.node_id}`}
        groups={[
          {
            title: 'Mood (-100 to +100)',
            fields: [
              {
                key: 'mood',
                label: 'Mood',
                value: view.mood_score,
                min: -PERCENT,
                max: PERCENT,
              },
            ],
          },
        ]}
        note='Set the mood; with Hold what I set on, it stays until you release it.'
        run={setMood}
      />
    </ControlPanel>
  )
}

export function FeelingsSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const query = useFeelings(nodeId)
  const view = query.data
  if (query.isError)
    return (
      <Section
        id='section-feelings'
        title='Feelings, grief and dreams'
        icon={FEELINGS_ICON}
      >
        <EmptyState
          icon={FEELINGS_ICON}
          title='This could not be read'
          description={query.error.message}
        />
      </Section>
    )
  if (!view || !view.applies) return null
  return (
    <Section
      id='section-feelings'
      title='Feelings, grief and dreams'
      description='Only living mortals think, grieve and dream. What they live through gives them feelings that make a mood, and the strongest stay with them for life.'
      icon={FEELINGS_ICON}
    >
      <div className='@container/feel flex min-w-0 flex-col gap-4'>
        <FeelingsHero view={view} />
        <div className='grid min-w-0 grid-cols-1 gap-3 @xl/feel:grid-cols-2'>
          <Thoughts view={view} blocked={reason()} />
          <Formative view={view} />
          <Griefs view={view} blocked={reason()} />
          <Dreams view={view} blocked={reason()} />
        </div>
        <FeelingControls view={view} />
      </div>
    </Section>
  )
}
