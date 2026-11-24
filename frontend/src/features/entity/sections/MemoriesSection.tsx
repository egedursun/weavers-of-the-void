import { useMemo, useState } from 'react'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  EntityLink,
  FormRow,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
  type TimelineTone,
  Paged,
  FieldTile,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { type EntryKind } from '@/components/layout/entry/entryStack'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { useNames } from '../api/queries'
import {
  type Mind,
  type MindMemory,
  type MindOpinion,
  type MemoryKind,
  signed,
  useMind,
} from '../mind/api'
import {
  MEMORY_ICON,
  MEMORY_ICONS,
  OPINION_COMPONENTS,
  OPINION_NEGATIVE,
  OPINION_TERMS,
  named,
  plain,
  labelTable,
} from '../mind/labels'
import { ControlPanel, MindCard, MindPicker } from '../mind/parts'

const RELATION_MIN = -100
const RELATION_MAX = 100
const PERCENT = 100
const DEFAULT_SIZE = '-30'
const WORKING = 'Working on it.'

function entryKind(kind: string): EntryKind {
  if (kind === 'son') return 'son'
  if (kind === 'foreign_god') return 'foreign-god'
  if (kind === 'creator') return 'creator'
  return 'entity'
}

function memoryTone(strength: number): TimelineTone {
  if (strength > 0) return 'success'
  if (strength < 0) return 'destructive'
  return 'default'
}

function inRange(text: string, low: number, high: number): number | null {
  const value = Number(text)
  return text.trim() !== '' &&
    Number.isInteger(value) &&
    value >= low &&
    value <= high
    ? value
    : null
}

function MemoryEditor({
  memory,
  blocked,
}: {
  memory: MindMemory
  blocked: string | null
}) {
  const [size, setSize] = useState(String(memory.magnitude))
  const [decay, setDecay] = useState(String(memory.decay_pct))
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/mind:memory_edit', {
          body: {
            memory_id: memory.id,
            magnitude: inRange(size, RELATION_MIN, RELATION_MAX),
            decay_pct: inRange(decay, 0, PERCENT),
          },
        })
      ),
  })
  const forget = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/mind:memory_remove', {
          body: { memory_id: memory.id },
        })
      ),
  })
  const busy = blocked ?? (edit.isPending || forget.isPending ? WORKING : null)
  const invalid =
    inRange(size, RELATION_MIN, RELATION_MAX) === null ||
    inRange(decay, 0, PERCENT) === null
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      <FieldTile
        id={`memory-size-${memory.id}`}
        label='Strength (−100 to +100)'
      >
        <Input
          id={`memory-size-${memory.id}`}
          type='number'
          min={RELATION_MIN}
          max={RELATION_MAX}
          value={size}
          disabled={busy !== null}
          onChange={(event) => setSize(event.target.value)}
          className='w-28'
        />
      </FieldTile>
      <FieldTile id={`memory-decay-${memory.id}`} label='Fades per epoch (%)'>
        <Input
          id={`memory-decay-${memory.id}`}
          type='number'
          min={0}
          max={PERCENT}
          value={decay}
          disabled={busy !== null}
          onChange={(event) => setDecay(event.target.value)}
          className='w-28'
        />
      </FieldTile>
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null || invalid}
        disabledReason={busy ?? 'Write whole numbers in range.'}
        onClick={() => edit.mutate()}
      >
        <Pencil />
        Change
      </Button>
      <Button
        size='sm'
        variant='ghost'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => forget.mutate()}
      >
        <Trash2 />
        Erase
      </Button>
    </div>
  )
}

function MemoryItem({
  memory,
  last,
  blocked,
}: {
  memory: MindMemory
  last: boolean
  blocked: string | null
}) {
  const spec = named(MEMORY_ICONS, memory.kind)
  const [open, setOpen] = useState(false)
  return (
    <TimelineItem
      icon={spec.icon}
      tone={memoryTone(memory.strength)}
      last={last}
      timestamp={`Epoch ${memory.epoch}`}
      title={
        <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
          {memory.subject ? (
            <EntityLink
              kind={entryKind(memory.subject.kind)}
              id={String(memory.subject.id)}
            >
              {memory.subject.name}
            </EntityLink>
          ) : (
            <Text as='span'>Someone forgotten</Text>
          )}
          <Text as='span'>{memory.label.toLowerCase()}</Text>
        </span>
      }
    >
      <div className='flex min-w-0 flex-col gap-2'>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge
            size='sm'
            variant={memory.strength < 0 ? 'destructive' : 'success'}
          >{`Now ${signed(memory.strength)} (was ${signed(memory.magnitude)})`}</Badge>
          <Badge size='sm' variant='secondary'>
            {memory.decay_pct === 0
              ? 'Never fades'
              : `Fades ${memory.decay_pct}% an epoch`}
          </Badge>
          {memory.inherited_from && (
            <Badge
              size='sm'
              variant='info'
            >{`Inherited from ${memory.inherited_from.name}`}</Badge>
          )}
          {memory.note && <Muted variant='caption'>{memory.note}</Muted>}
          <Button
            size='sm'
            variant='ghost'
            onClick={() => setOpen(!open)}
            aria-expanded={open}
          >
            <Pencil />
            {open ? 'Close' : 'Edit'}
          </Button>
        </div>
        {open && <MemoryEditor memory={memory} blocked={blocked} />}
      </div>
    </TimelineItem>
  )
}

export function OpinionBreakdown({ opinion }: { opinion: MindOpinion }) {
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {opinion.holder && <Text weight='semibold'>{opinion.holder.name}</Text>}
        <Muted variant='caption'>regards</Muted>
        {opinion.subject && (
          <EntityLink
            kind={entryKind(opinion.subject.kind)}
            id={String(opinion.subject.id)}
          >
            {opinion.subject.name}
          </EntityLink>
        )}
        <Badge
          size='sm'
          variant={
            opinion.value < 0
              ? 'destructive'
              : opinion.value > 0
                ? 'success'
                : 'secondary'
          }
        >
          {signed(opinion.value)}
        </Badge>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/mind:grid-cols-2'>
        {opinion.components.map((item) => {
          const spec = named(OPINION_COMPONENTS, item.component)
          return (
            <StatBar
              key={item.component}
              label={
                item.value < 0
                  ? plain(OPINION_NEGATIVE, item.component)
                  : spec.label
              }
              value={Math.abs(item.value)}
              max={RELATION_MAX}
              icon={spec.icon}
              tone={
                item.component === 'grievance' ||
                item.component === 'fear' ||
                item.value < 0
                  ? 'destructive'
                  : 'success'
              }
              showMax={false}
            />
          )
        })}
      </div>
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {opinion.alignment !== 0 && (
          <Badge
            size='sm'
            variant={opinion.alignment > 0 ? 'success' : 'warning'}
          >{`Values ${opinion.alignment > 0 ? 'agree' : 'clash'} ${signed(opinion.alignment)}`}</Badge>
        )}
        {opinion.terms.map((term) => (
          <Badge
            key={term.key}
            size='sm'
            variant={term.value < 0 ? 'destructive' : 'secondary'}
          >{`${plain(OPINION_TERMS, term.key)} ${signed(term.value)}`}</Badge>
        ))}
      </div>
      {opinion.memories.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-0.5'>
          <Paged items={opinion.memories} as='li'>
            {(item) => (
              <li key={item.id}>
                <Muted variant='caption'>{`Epoch ${item.epoch}: ${item.note ?? item.label} — ${signed(item.strength)}, weighed ${item.weight_pct}% by their values → ${signed(item.contribution)}`}</Muted>
              </li>
            )}
          </Paged>
        </ul>
      )}
    </div>
  )
}

function PlantMemory({ mind }: { mind: Mind }) {
  const { reason } = useGodGate()
  const names = useNames()
  const [subject, setSubject] = useState<string | null>(null)
  const [kind, setKind] = useState('')
  const [size, setSize] = useState(DEFAULT_SIZE)
  const [decay, setDecay] = useState('5')
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter(
          (entry) =>
            entry.id !== mind.node_id &&
            (entry.kind !== 'entity' ||
              !entry.status ||
              entry.status === 'canon' ||
              entry.status === 'dead')
        )
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: entry.type.replaceAll('_', ' '),
        })),
    [names.data, mind.node_id]
  )
  const plant = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/mind:memory', {
          body: {
            holder_id: mind.node_id,
            subject_id: Number(subject),
            kind: kind as MemoryKind,
            magnitude: Number(size),
            decay_pct: decay.trim() === '' ? null : Number(decay),
          },
        })
      ),
    onDone: () => {
      setSubject(null)
      setKind('')
    },
  })
  const sizeValue = inRange(size, RELATION_MIN, RELATION_MAX)
  const decayValid = decay.trim() === '' || inRange(decay, 0, PERCENT) !== null
  const busy = reason() ?? (plant.isPending ? WORKING : null)
  const missing =
    subject === null
      ? 'Choose who the memory is about.'
      : kind === ''
        ? 'Choose what they remember.'
        : null
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md/mind:grid-cols-2 @3xl/mind:grid-cols-4'>
      <FormRow label='About'>
        {(id) => (
          <RecordCombobox
            id={id}
            options={options}
            value={subject}
            onChange={setSubject}
            placeholder='Choose someone'
            clearable
            aria-label='About whom'
          />
        )}
      </FormRow>
      <MindPicker
        label='What they remember'
        value={kind}
        table={labelTable(MEMORY_ICONS)}
        blocked={busy}
        placeholder='Choose a memory'
        onPick={setKind}
      />
      <FieldTile
        id={`plant-size-${mind.node_id}`}
        label='Strength (−100 to +100)'
      >
        <Input
          id={`plant-size-${mind.node_id}`}
          type='number'
          min={RELATION_MIN}
          max={RELATION_MAX}
          value={size}
          disabled={busy !== null}
          onChange={(event) => setSize(event.target.value)}
        />
      </FieldTile>
      <FieldTile
        id={`plant-decay-${mind.node_id}`}
        label='Fades per epoch (%, blank for its kind)'
      >
        <Input
          id={`plant-decay-${mind.node_id}`}
          type='number'
          min={0}
          max={PERCENT}
          value={decay}
          disabled={busy !== null}
          onChange={(event) => setDecay(event.target.value)}
        />
      </FieldTile>
      <div className='flex justify-end @md/mind:col-span-2 @3xl/mind:col-span-4'>
        <Button
          size='sm'
          disabled={
            busy !== null ||
            missing !== null ||
            sizeValue === null ||
            sizeValue === 0 ||
            !decayValid
          }
          disabledReason={
            busy ??
            missing ??
            'Write a strength other than 0 and a fade from 0 to 100.'
          }
          onClick={() => plant.mutate()}
        >
          <Plus />
          Plant the memory
        </Button>
      </div>
    </div>
  )
}

export function MemoriesSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const query = useMind(nodeId)
  const mind = query.data
  return (
    <Section
      id='section-memories'
      title='Memories and opinions'
      description='What this one remembers of others and how it regards them. Memories fade with time, are weighed by its values, pass to heirs and can set a mortal on vengeance.'
      icon={MEMORY_ICON}
    >
      {!mind ? (
        <EmptyState
          icon={MEMORY_ICON}
          title='No memories yet'
          description='The next epoch gives this one a mind and the memories of its past.'
        />
      ) : (
        <div className='@container/mind flex min-w-0 flex-col gap-4'>
          {mind.opinions.length > 0 && (
            <MindCard
              title='How they regard others'
              icon={OPINION_COMPONENTS.trust.icon}
              hint='Each opinion is built from memories, how close their values are and the bonds they share.'
            >
              <div className='flex min-w-0 flex-col gap-2'>
                <Paged items={mind.opinions}>
                  {(opinion) => (
                    <OpinionBreakdown
                      key={opinion.subject?.id ?? opinion.value}
                      opinion={opinion}
                    />
                  )}
                </Paged>
              </div>
            </MindCard>
          )}
          {mind.memories.length === 0 ? (
            <EmptyState
              icon={MEMORY_ICON}
              title='Nothing remembered'
              description='No deed of others has marked this one yet.'
            />
          ) : (
            <MindCard
              title={`${plural(mind.memories.length, 'memory', 'memories')}`}
              icon={MEMORY_ICON}
            >
              <Timeline label='Memories'>
                <Paged items={mind.memories} as='li'>
                  {(memory, index) => (
                    <MemoryItem
                      key={memory.id}
                      memory={memory}
                      last={index === mind.memories.length - 1}
                      blocked={reason()}
                    />
                  )}
                </Paged>
              </Timeline>
            </MindCard>
          )}
          <ControlPanel
            title='Plant a memory'
            note='Make this one remember a deed of someone else. Strength below zero is a grievance, above zero is warmth. Every change goes into the ledger and can be undone.'
          >
            <PlantMemory mind={mind} />
          </ControlPanel>
        </div>
      )}
    </Section>
  )
}
