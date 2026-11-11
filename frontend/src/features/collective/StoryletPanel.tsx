import { type ReactNode, useState } from 'react'
import { BookOpen, Drama, Link2, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PagedList } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Chip, Facts, ForgeCard, RecordRow } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import {
  type CollectiveView,
  type StoryletSpecView,
  type StoryletView,
  useCollectiveAction,
  useStoryletCatalog,
} from './api'
import { ROLES_IN_STORY, STORYLET_STATES, STORYLETS } from './labels'
import { Held, Listed } from './parts'

function cast(text: string) {
  return text.replace(/\{(\w+)\}/g, (_, role: string) =>
    role in ROLES_IN_STORY
      ? `the ${ROLES_IN_STORY[role as keyof typeof ROLES_IN_STORY].toLowerCase()}`
      : role
  )
}

function ChoiceButton({
  run,
  index,
  text,
  blocked,
}: {
  run: StoryletView
  index: number
  text: string
  blocked: string | null
}) {
  const choosing = useCollectiveAction(
    'storylet:choose',
    (_: void) => ({ run_id: run.id, choice: index }),
    'The choice is made'
  )
  const closed =
    run.status !== 'open' ? 'The choice has been made already' : null
  const busy = why(closed ?? blocked, choosing.isPending)
  const chosen = run.choice === index
  return (
    <Button
      size='sm'
      variant={chosen ? 'default' : 'outline'}
      disabled={busy !== null}
      disabledReason={busy ?? undefined}
      onClick={() => choosing.mutate()}
    >
      <Play />
      {`${index + 1}. ${text}`}
    </Button>
  )
}

function StoryletCard({
  row,
  blocked,
}: {
  row: StoryletView
  blocked: string | null
}) {
  const editing = useCollectiveAction(
    'storylet:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ run_id: row.id, ...vars }),
    'Set so'
  )
  const removing = useCollectiveAction(
    'storylet:delete',
    (_: void) => ({ run_id: row.id }),
    'Done'
  )
  const spec = STORYLETS[row.storylet]
  const state = STORYLET_STATES[row.status]
  const busy = why(blocked, editing.isPending, removing.isPending)
  return (
    <Held
      icon={spec.icon}
      tone={state.tone}
      title={row.title}
      caption={`Opened in epoch ${row.opened_epoch}${row.due_epoch !== null ? ` · decided by epoch ${row.due_epoch}` : ''}${row.resolved_epoch !== null ? ` · settled in epoch ${row.resolved_epoch}` : ''}`}
      removeLabel='Strike from the record'
      editTitle='Set the storylet'
      note='A storylet waits on its chooser; left past its day, the chooser decides by their own nature.'
      fields={[
        {
          key: 'status',
          label: 'State',
          kind: 'pick',
          table: table(STORYLET_STATES),
        },
        { key: 'due_epoch', label: 'Decided by epoch', kind: 'number', min: 0 },
        { key: 'choice', label: 'Choice made', kind: 'number', min: 0, max: 3 },
        {
          key: 'chooser_node_id',
          label: 'Chosen by',
          kind: 'node',
          types: ['mortal', 'polity', 'people', 'cult', 'house', 'settlement'],
        },
      ]}
      locked={row.locked}
      blocked={busy}
      onEdit={(vars) => editing.mutate(vars)}
      onRemove={() => removing.mutate()}
      extra={
        <>
          <Chip icon={state.icon}>{state.label}</Chip>
          {row.follows_run_id !== null && (
            <Chip icon={Link2}>{`Follows storylet ${row.follows_run_id}`}</Chip>
          )}
        </>
      }
    >
      <Text>{row.situation}</Text>
      <Facts
        items={[
          ['Chooser', <Ref key='chooser' node={row.chooser} empty='no one' />],
          ['Step', row.step + 1],
          ['World', row.world_id ?? 'none'],
          ['Event chain', row.collection_name ?? 'none'],
          ...row.cast.map((part): [string, ReactNode] => [
            ROLES_IN_STORY[part.role],
            <Ref key={part.role} node={part.node} />,
          ]),
        ]}
      />
      <Label variant='overline'>Choices</Label>
      <PagedList
        items={row.choices}
        initial={4}
        noun={['choice', 'choices']}
        className='flex min-w-0 flex-col gap-2'
        itemKey={(choice) => choice.index}
      >
        {(choice) => (
          <ChoiceButton
            run={row}
            index={choice.index}
            text={choice.text}
            blocked={busy}
          />
        )}
      </PagedList>
    </Held>
  )
}

function SpecCard({ spec }: { spec: StoryletSpecView }) {
  const named = STORYLETS[spec.storylet]
  return (
    <RecordRow
      icon={named.icon}
      tone={named.tone}
      title={spec.title}
      caption={`Chosen by the ${ROLES_IN_STORY[spec.chooser].toLowerCase()} · weight ${spec.weight}`}
      aside={
        <Chip icon={BookOpen}>
          {`${spec.steps.length} ${spec.steps.length === 1 ? 'step' : 'steps'}`}
        </Chip>
      }
    >
      <Muted variant='caption'>{`Parts: ${spec.roles.map((role) => ROLES_IN_STORY[role]).join(', ')}`}</Muted>
      {spec.steps.map((step, index) => (
        <div key={step.text} className='flex min-w-0 flex-col gap-1'>
          <Label>{`Step ${index + 1}`}</Label>
          <Text>{cast(step.text)}</Text>
          <Muted variant='caption'>
            {step.choices
              .map((choice, at) => `${at + 1}. ${cast(choice)}`)
              .join(' · ')}
          </Muted>
        </div>
      ))}
    </RecordRow>
  )
}

function StoryletForge({ blocked }: { blocked: string | null }) {
  const [storylet, setStorylet] = useState<keyof typeof STORYLETS>('lost_heir')
  const [world, setWorld] = useState<number | null>(null)
  const opening = useCollectiveAction(
    'storylet:open',
    (_: void) => ({ storylet, world_id: world ?? 0 }),
    'The storylet is in motion'
  )
  const busy = why(
    world === null ? 'Choose the world it happens in' : blocked,
    opening.isPending
  )
  return (
    <ForgeCard
      icon={Drama}
      tone='gold'
      title='Set a storylet in motion'
      note='Mortals who fit its parts are cast from the world as it stands; the one it falls to must choose what follows.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => opening.mutate()}
        >
          <Drama />
          Begin it
        </Button>
      }
    >
      <MindPicker
        label='Storylet'
        value={storylet}
        table={table(STORYLETS)}
        blocked={blocked}
        onPick={(value) => setStorylet(value as keyof typeof STORYLETS)}
      />
      <NodePicker
        label='World'
        value={world}
        onChange={setWorld}
        blocked={blocked}
        kinds={['world']}
      />
    </ForgeCard>
  )
}

export function StoryletPanel({
  data,
  blocked,
}: {
  data: CollectiveView
  blocked: string | null
}) {
  const catalog = useStoryletCatalog()
  return (
    <div
      id='section-storylets'
      data-surface='StoryletPanel'
      className='flex min-w-0 flex-col gap-3'
    >
      <Label variant='overline'>Storylets</Label>
      <Listed
        title='Storylets'
        items={data.storylets}
        empty='No storylet has touched this.'
        noun={['storylet', 'storylets']}
        itemKey={(row) => row.id}
      >
        {(row) => <StoryletCard row={row} blocked={blocked} />}
      </Listed>
      <StoryletForge blocked={blocked} />
      <Listed
        title='The catalogue'
        items={catalog.data ?? []}
        empty={
          catalog.isPending
            ? 'Reading the catalogue'
            : 'The catalogue could not be read.'
        }
        noun={['storylet', 'storylets']}
        itemKey={(spec) => spec.storylet}
      >
        {(spec) => <SpecCard spec={spec} />}
      </Listed>
    </div>
  )
}
