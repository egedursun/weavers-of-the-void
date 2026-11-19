import { useMemo, useState } from 'react'
import {
  CalendarRange,
  Gauge,
  Lock,
  Skull,
  Sparkles,
  TriangleAlert,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  Medallion,
  RangeField,
  Section,
  ShowMore,
  useShowMore,
  LoadingBlock,
  FieldTile,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { useNames } from '../api/queries'
import { AdjustPanel, IconPicker, Panel } from '../society/parts'
import { WORKING } from '../society/tones'
import { useHappeningsHere } from './api'
import {
  EVENT_ICON,
  type EventPhase,
  KIND_SPEC,
  PHASE_SPEC,
  kindSpec,
} from './labels'

type EngineKind = components['schemas']['EngineKind']
type Summary = components['schemas']['EventSummaryView']

const PERCENT = 100
const EVENTS_SHOWN = 8
const NO_SEASON = 'none'
const PAIRED = new Set(['wedding', 'schism_council', 'coronation'])
const SEVERITY_LEVELS = [
  { at: 80, label: 'Of legend' },
  { at: 55, label: 'Great' },
  { at: 30, label: 'Notable' },
  { at: 0, label: 'Small' },
]

function level(value: number): string {
  return SEVERITY_LEVELS.find((item) => value >= item.at)?.label ?? 'Small'
}

function years(item: Summary): string {
  if (item.start_year === null) return ''
  if (item.end_year === null) return `since ${item.start_year}`
  return item.end_year === item.start_year
    ? `${item.start_year}`
    : `${item.start_year}–${item.end_year}`
}

function EventRow({ item }: { item: Summary }) {
  const spec = kindSpec(item.kind)
  const phase = PHASE_SPEC[item.phase]
  return (
    <li className='flex min-w-0 items-center gap-2.5 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
        <EntityLink kind='entity' id={String(item.entity_id)}>
          {item.name}
        </EntityLink>
        <Muted as='span' variant='caption' truncate>
          {[spec.label, years(item)].filter(Boolean).join(' · ')}
        </Muted>
      </div>
      <Badge
        size='sm'
        variant={
          item.ended
            ? 'success'
            : item.phase === 'peak'
              ? 'destructive'
              : 'warning'
        }
      >
        <phase.icon />
        {item.ended ? 'Over' : phase.label}
      </Badge>
      {item.toll > 0 && (
        <Badge size='sm' variant='destructive'>
          <Skull />
          {formatInteger(item.toll)}
        </Badge>
      )}
    </li>
  )
}

function CreateEvent({
  locationId,
  worldId,
  kinds,
  seasons,
  blocked,
}: {
  locationId: number
  worldId: number | null
  kinds: EngineKind[]
  seasons: components['schemas']['SeasonRef'][]
  blocked: string | null
}) {
  const names = useNames()
  const [kind, setKind] = useState<string>('festival_of_note')
  const [name, setName] = useState('')
  const [severity, setSeverity] = useState(50)
  const [phase, setPhase] = useState<EventPhase>('onset')
  const [hold, setHold] = useState(false)
  const [year, setYear] = useState('')
  const [season, setSeason] = useState(NO_SEASON)
  const [partner, setPartner] = useState<string | null>(null)
  const table = useMemo(
    () => Object.fromEntries(kinds.map((item) => [item, kindSpec(item)])),
    [kinds]
  )
  const seasonTable = useMemo(
    () =>
      Object.fromEntries([
        [
          NO_SEASON,
          {
            label: 'Let the world choose',
            icon: CalendarRange,
            tone: 'muted' as const,
          },
        ],
        ...seasons.map((item) => [
          String(item.position),
          { label: item.name, icon: CalendarRange, tone: 'gold' as const },
        ]),
      ]),
    [seasons]
  )
  const partners = useMemo(
    () =>
      (names.data ?? [])
        .filter(
          (entry) =>
            entry.kind === 'entity' &&
            ['people', 'settlement', 'cult', 'mortal', 'polity'].includes(
              entry.type ?? ''
            ) &&
            (worldId === null || entry.world_id === worldId)
        )
        .map((entry) => ({ value: String(entry.id), label: entry.name })),
    [names.data, worldId]
  )
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/event:create', {
          body: {
            kind: kind as EngineKind,
            where_id: locationId,
            name: name.trim(),
            description: '',
            footprint: [],
            severity,
            phase,
            hold_phase: hold,
            start_year:
              year.trim() === '' ? null : Math.max(0, Number(year) || 0),
            start_season: season === NO_SEASON ? null : Number(season),
            partner_id: partner === null ? null : Number(partner),
          },
        })
      ),
    onDone: () => setName(''),
  })
  const busy = blocked ?? (create.isPending ? WORKING : null)
  const spec = KIND_SPEC[kind] ?? kindSpec(kind)
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @xl:grid-cols-2'>
      <Panel
        title='What happens'
        icon={spec.icon}
        tone={spec.tone}
        hint={spec.hint ?? 'Choose its kind and name it'}
      >
        <IconPicker
          label='Kind'
          value={kind}
          table={table}
          blocked={busy}
          onPick={setKind}
        />
        <FieldTile id={`event-name-${locationId}`} label='Name'>
          <Input
            id={`event-name-${locationId}`}
            value={name}
            placeholder='Leave empty to let the world name it'
            disabled={busy !== null}
            onChange={(event) => setName(event.target.value)}
          />
        </FieldTile>
        {PAIRED.has(kind) && (
          <FieldTile
            label={
              kind === 'wedding'
                ? 'The other house'
                : kind === 'coronation'
                  ? 'Who comes to rule'
                  : 'The breakaway sect'
            }
          >
            <RecordCombobox
              options={partners}
              value={partner}
              onChange={(value) => setPartner(value)}
              placeholder='Choose one'
              aria-label='Partner'
              disabled={busy !== null}
            />
          </FieldTile>
        )}
        <RangeField
          label='Severity'
          icon={Gauge}
          value={severity}
          min={0}
          max={PERCENT}
          level={level(severity)}
          lowLabel='Small'
          highLabel='Of legend'
          onChange={setSeverity}
        />
      </Panel>
      <Panel
        title='When and how it stands'
        icon={CalendarRange}
        tone='gold'
        hint='Its year, season and phase'
      >
        <div className='grid min-w-0 grid-cols-1 gap-2 @md:grid-cols-2'>
          <FieldTile id={`event-year-${locationId}`} label='Year'>
            <Input
              id={`event-year-${locationId}`}
              type='number'
              min={0}
              value={year}
              placeholder='This age'
              disabled={busy !== null}
              onChange={(event) => setYear(event.target.value)}
            />
          </FieldTile>
          <IconPicker
            label='Season'
            value={season}
            table={seasonTable}
            blocked={busy}
            onPick={setSeason}
          />
        </div>
        <IconPicker
          label='Phase'
          value={phase}
          table={PHASE_SPEC}
          blocked={busy}
          onPick={(value) => setPhase(value as EventPhase)}
        />
        <div className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
          <Lock aria-hidden='true' className='size-icon-xs text-primary' />
          <Text as='span' className='flex-1'>
            Hold it in this phase
          </Text>
          <Switch
            checked={hold}
            disabled={busy !== null}
            onCheckedChange={setHold}
            aria-label='Hold it in this phase'
          />
        </div>
        <Button
          size='sm'
          className='mt-auto'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => create.mutate(undefined)}
        >
          <Sparkles />
          Let it come to pass
        </Button>
      </Panel>
    </div>
  )
}

export function EventsHereSection({
  locationId,
  readOnlyReason,
}: {
  locationId: number
  readOnlyReason?: string | null
}) {
  const view = useHappeningsHere(locationId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const data = view.data
  const open = data ? data.events.filter((item) => !item.ended) : []
  const ordered = data
    ? [...open, ...data.events.filter((item) => item.ended)]
    : []
  const shown = useShowMore(ordered, EVENTS_SHOWN)
  return (
    <Section
      id='section-events-here'
      title='Events here'
      description='What has happened and is happening in this land, and a hand to make something happen.'
      icon={EVENT_ICON}
      tone='warning'
    >
      {view.isPending && <LoadingBlock label='Reading what happened here' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Nothing can be read'
          description={view.error.message}
        />
      )}
      {data && (
        <div
          data-surface='EventsHere'
          className='@container flex min-w-0 flex-col gap-4'
        >
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Badge size='sm' variant='warning'>
              <Users />
              {`${open.length} under way`}
            </Badge>
            <Badge size='sm' variant='secondary'>
              <EVENT_ICON />
              {`${data.events.length} in all`}
            </Badge>
          </div>
          {data.events.length === 0 ? (
            <Muted>Nothing of note has happened here yet.</Muted>
          ) : (
            <>
              <ul className='flex min-w-0 flex-col gap-2'>
                {shown.visible.map((item) => (
                  <EventRow key={item.entity_id} item={item} />
                ))}
              </ul>
              <ShowMore state={shown} noun={['event', 'events']} />
            </>
          )}
          <AdjustPanel
            title='Make something happen'
            note='Set down an event of any kind here: a festival, a coronation, a fire, a famine or an eruption. Its effects follow at once and it moves through its phases with the world. Undoable from the ledger.'
          >
            <CreateEvent
              locationId={data.location_id}
              worldId={data.world_id}
              kinds={data.kinds}
              seasons={data.seasons}
              blocked={blocked}
            />
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}
