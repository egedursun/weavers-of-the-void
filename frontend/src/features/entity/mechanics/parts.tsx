import { useState } from 'react'
import {
  ArrowRight,
  Feather,
  Lock,
  Pause,
  PenLine,
  Play,
  ScrollText,
  Sparkles,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Medallion, TimelineItem, Paged } from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { named } from '@/features/entity/environment/labels'
import { useGodAction } from '@/features/pantheon/godAction'
import { INCIDENT_ROLE } from '@/features/records/labels'
import { roleTimelineTone } from '@/features/records/tones'
import { NamedRecord } from '../NamedRecord'
import { humanize } from '../actions/schema'
import { MindPicker } from '../mind/parts'
import { IncidentControls } from './IncidentForge'

type Effective = components['schemas']['EffectiveValue']
type Modifier = components['schemas']['ModifierRecord']
type Acting = components['schemas']['ActingMechanic']
type Incident = components['schemas']['IncidentRecord']

const DEFAULT_EPOCHS = 1
function shift(modifier: Modifier): string {
  if (modifier.op === 'multiply') return `× ${modifier.magnitude}`
  return `${modifier.magnitude > 0 ? '+' : ''}${modifier.magnitude}`
}

export function WhyBreakdown({
  values,
  modifiers,
}: {
  values: Effective[]
  modifiers: Modifier[]
}) {
  const byId = new Map(modifiers.map((item) => [item.id, item]))
  return (
    <div
      data-surface='WhyBreakdown'
      className='grid min-w-0 grid-cols-1 gap-2 @md/mech:grid-cols-2 @xl/mech:grid-cols-3'
    >
      <Paged items={values}>
        {(value) => {
          const applied = value.applied
            .map((id) => byId.get(id))
            .filter((item): item is Modifier => item !== undefined)
          const ignored = value.ignored
            .map((id) => byId.get(id))
            .filter((item): item is Modifier => item !== undefined)
          return (
            <div
              key={value.key}
              className='flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-gild/60 bg-card p-2'
            >
              <div className='flex min-w-0 items-baseline justify-between gap-2'>
                <Label truncate>{humanize(value.key)}</Label>
                <Stat value={Number(value.value.toFixed(1))} />
              </div>
              <Muted variant='caption'>
                {applied.length === 0
                  ? `Its own value: ${value.base}`
                  : `From ${value.base}:`}
              </Muted>
              <Paged items={applied}>
                {(item) => (
                  <Muted key={item.id} variant='caption'>
                    {`${shift(item)} because ${item.reason}`}
                  </Muted>
                )}
              </Paged>
              <Paged items={ignored}>
                {(item) => (
                  <Muted key={item.id} variant='caption'>
                    {`${shift(item)} does not stack with a stronger effect: ${item.reason}`}
                  </Muted>
                )}
              </Paged>
            </div>
          )
        }}
      </Paged>
    </div>
  )
}

export function CausalChain({
  causes,
  text,
}: {
  causes: string[]
  text: string | null
}) {
  if (causes.length === 0) return null
  return (
    <ol
      data-surface='CausalChain'
      aria-label='How it came about'
      className='flex min-w-0 flex-col gap-0.5'
    >
      <Paged items={causes} as='li'>
        {(cause, index) => (
          <li
            key={`${index}-${cause}`}
            className='flex min-w-0 items-start gap-1'
          >
            <ArrowRight
              className='size-icon-xs shrink-0 text-muted-foreground'
              aria-hidden='true'
            />
            <Muted variant='caption'>{cause}</Muted>
          </li>
        )}
      </Paged>
      {text && (
        <li className='flex min-w-0 items-start gap-1'>
          <ArrowRight
            className='size-icon-xs shrink-0 text-primary'
            aria-hidden='true'
          />
          <Text>{text}</Text>
        </li>
      )}
    </ol>
  )
}

export function ActingMechanics({
  nodeId,
  acting,
  statKeys,
  blocked,
}: {
  nodeId: number
  acting: Acting[]
  statKeys: string[]
  blocked: string | undefined
}) {
  const [editing, setEditing] = useState<string | null>(null)
  const [field, setField] = useState('')
  const [value, setValue] = useState('')
  const run = useGodAction({
    run: (mechanic: string) =>
      unwrap(
        api.POST('/api/actions/lever:run', {
          body: { mechanic, target_node_id: nodeId },
        })
      ),
  })
  const hold = useGodAction({
    run: (mechanic: string) =>
      unwrap(
        api.POST('/api/actions/lever:suppress', {
          body: { node_id: nodeId, mechanic, epochs: DEFAULT_EPOCHS },
        })
      ),
    success: 'The mechanic is held back here',
  })
  const free = useGodAction({
    run: (mechanic: string) =>
      unwrap(
        api.POST('/api/actions/lever:unsuppress', {
          body: { node_id: nodeId, mechanic },
        })
      ),
    success: 'The mechanic acts here again',
  })
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/lever:set', {
          body: { node_id: nodeId, key: field, value: Number(value) },
        })
      ),
    success: () => `${humanize(field)} set`,
  })
  const pin = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/lever:pin', {
          body: { node_id: nodeId, key: field, epochs: null },
        })
      ),
    success: () => `${humanize(field)} is pinned`,
  })
  const busy =
    blocked ??
    ([run, hold, free, set, pin].some((item) => item.isPending)
      ? 'Another change is being applied.'
      : undefined)
  if (acting.length === 0)
    return (
      <Muted>No registered mechanic acts on this kind of record yet.</Muted>
    )
  return (
    <ul className='flex min-w-0 flex-col gap-2'>
      <Paged items={acting} as='li'>
        {(mechanic) => {
          const own = mechanic.fields.filter((key) => statKeys.includes(key))
          const open = editing === mechanic.key
          return (
            <li
              key={mechanic.key}
              className='flex min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'
            >
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Medallion
                  icon={Sparkles}
                  tone={mechanic.suppressed ? 'muted' : 'verdigris'}
                  size='sm'
                />
                <div className='flex min-w-0 flex-1 flex-col'>
                  <Text weight='semibold' truncate>
                    {mechanic.title}
                  </Text>
                  <Muted variant='caption' truncate>
                    {mechanic.last_text
                      ? `Last, in epoch ${mechanic.last_epoch}: ${mechanic.last_text}`
                      : `Reads ${mechanic.reads.map(humanize).join(', ') || 'nothing here'}; writes ${mechanic.writes.map(humanize).join(', ') || 'nothing here'}`}
                  </Muted>
                </div>
                <Badge size='sm' variant='secondary'>
                  {humanize(mechanic.subsystem)}
                </Badge>
                {mechanic.suppressed && (
                  <Badge size='sm' variant='warning'>
                    Held back
                  </Badge>
                )}
              </div>
              {mechanic.affects.length > 0 && (
                <div className='flex min-w-0 flex-wrap items-center gap-1'>
                  <Muted variant='caption'>Reaches</Muted>
                  <Paged items={mechanic.affects}>
                    {(item) => (
                      <Badge key={item} size='sm' variant='outline'>
                        {humanize(item)}
                      </Badge>
                    )}
                  </Paged>
                </div>
              )}
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== undefined}
                  disabledReason={busy}
                  onClick={() => run.mutate(mechanic.key)}
                >
                  <Play />
                  Run on this record now
                </Button>
                <Button
                  size='sm'
                  variant='outline'
                  disabled={busy !== undefined}
                  disabledReason={busy}
                  onClick={() =>
                    mechanic.suppressed
                      ? free.mutate(mechanic.key)
                      : hold.mutate(mechanic.key)
                  }
                >
                  {mechanic.suppressed ? <Play /> : <Pause />}
                  {mechanic.suppressed ? 'Let it act' : 'Hold it back here'}
                </Button>
                {own.length > 0 && (
                  <Button
                    size='sm'
                    variant='ghost'
                    onClick={() => {
                      setEditing(open ? null : mechanic.key)
                      setField(own[0])
                      setValue('')
                    }}
                  >
                    <PenLine />
                    {open ? 'Close' : 'Edit its values'}
                  </Button>
                )}
              </div>
              {open && (
                <div className='flex min-w-0 flex-wrap items-end gap-2'>
                  <div className='min-w-40 flex-1'>
                    <MindPicker
                      label='Value'
                      value={field}
                      table={Object.fromEntries(
                        own.map((key) => [key, humanize(key)])
                      )}
                      blocked={busy ?? null}
                      onPick={setField}
                    />
                  </div>
                  <Input
                    aria-label='New value'
                    inputMode='numeric'
                    className='w-24'
                    value={value}
                    onChange={(event) => setValue(event.target.value)}
                  />
                  <Button
                    size='sm'
                    disabled={busy !== undefined || value === ''}
                    disabledReason={
                      busy ??
                      (value === '' ? 'Enter a value first.' : undefined)
                    }
                    onClick={() => set.mutate(undefined)}
                  >
                    Set
                  </Button>
                  <Button
                    size='sm'
                    variant='outline'
                    disabled={busy !== undefined}
                    disabledReason={busy}
                    onClick={() => pin.mutate(undefined)}
                  >
                    <Lock />
                    Pin it
                  </Button>
                </div>
              )}
            </li>
          )
        }}
      </Paged>
    </ul>
  )
}

export function IncidentEntry({
  incident,
  last,
  blocked,
  incidents = [],
}: {
  incident: Incident
  last: boolean
  blocked: string | undefined
  incidents?: Incident[]
}) {
  const [writing, setWriting] = useState(false)
  const [note, setNote] = useState(incident.note ?? '')
  const annotate = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/incident:annotate', {
          body: { incident_id: incident.id, note },
        })
      ),
    success: 'Your note is kept',
  })
  const busy = blocked ?? (annotate.isPending ? 'Saving the note.' : undefined)
  return (
    <TimelineItem
      icon={ScrollText}
      tone={roleTimelineTone(incident.role)}
      title={
        incident.text ??
        humanize(incident.kind.split('.').pop() ?? incident.kind)
      }
      timestamp={
        incident.year !== null
          ? `Year ${incident.year} · epoch ${incident.epoch}`
          : `Epoch ${incident.epoch}`
      }
      last={last}
    >
      <div className='flex min-w-0 flex-col gap-1.5'>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='outline'>
            {named(INCIDENT_ROLE, incident.role).label}
          </Badge>
          {incident.magnitude > 0 && (
            <Badge
              size='sm'
              variant='warning'
            >{`Weight ${incident.magnitude}`}</Badge>
          )}
          {incident.thread_id !== null && (
            <Badge size='sm' variant='info'>
              Part of a story thread
            </Badge>
          )}
          {incident.consequences.length > 0 && (
            <Badge
              size='sm'
              variant='secondary'
            >{`${incident.consequences.length} ${incident.consequences.length === 1 ? 'consequence' : 'consequences'}`}</Badge>
          )}
          {incident.place_entity_id !== null &&
            incident.place_entity_id !== undefined && (
              <Muted as='span' variant='caption'>
                {'At '}
                <NamedRecord id={incident.place_entity_id} />
              </Muted>
            )}
        </div>
        <CausalChain causes={incident.causes} text={null} />
        <IncidentControls
          incident={incident}
          incidents={incidents}
          blocked={blocked}
        />
        {incident.note && !writing && <Text>{incident.note}</Text>}
        {writing ? (
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Input
              aria-label='Your note'
              className='min-w-48 flex-1'
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
            <Button
              size='sm'
              disabled={busy !== undefined}
              disabledReason={busy}
              onClick={() => {
                annotate.mutate(undefined)
                setWriting(false)
              }}
            >
              Keep note
            </Button>
          </div>
        ) : (
          <Button
            size='sm'
            variant='ghost'
            className='self-start'
            onClick={() => setWriting(true)}
          >
            <Feather />
            {incident.note ? 'Change your note' : 'Add a note'}
          </Button>
        )}
      </div>
    </TimelineItem>
  )
}
