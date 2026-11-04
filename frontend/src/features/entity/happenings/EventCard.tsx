import { useMemo, useState } from 'react'
import {
  CalendarRange,
  Flag,
  Gauge,
  Lock,
  MapPin,
  Minus,
  Plus,
  Quote,
  Skull,
  TriangleAlert,
  Unlock,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Medallion,
  Section,
  ShowMore,
  StatBar,
  useShowMore,
  Paged,
  LoadingBlock,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { useNames } from '../api/queries'
import {
  AGE_ORDER,
  AGE_SPEC,
  type AgeBand,
  CLASS_SPEC,
  SEX_SPEC,
  type Sex,
  type SocialClass,
} from '../society/labels'
import {
  AdjustPanel,
  EditorGroup,
  HeldStrip,
  IconPicker,
  NumberEditor,
  Panel,
} from '../society/parts'
import { METER_TONE, WORKING, badTone } from '../society/tones'
import { type EventView, useEventView } from './api'
import {
  type EventPhase,
  PHASE_ORDER,
  PHASE_SPEC,
  fieldLabel,
  kindSpec,
} from './labels'

const PERCENT = 100
const TOLL_SHOWN = 4
const NO_SEASON = 'none'

function yearsText(view: EventView): string {
  const start = view.start_year ?? '?'
  if (view.end_year === null) return `Since the year ${start}`
  return view.end_year === view.start_year
    ? `In the year ${start}`
    : `From ${start} to ${view.end_year}`
}

function seasonText(view: EventView): string | null {
  const start = view.start_season?.name
  const end = view.end_season?.name
  if (start && end && start !== end) return `${start} to ${end}`
  return start ?? end ?? null
}

function PhaseTrack({ view }: { view: EventView }) {
  return (
    <ol
      aria-label='Phases'
      className='grid min-w-0 auto-cols-fr grid-flow-col gap-2'
    >
      <Paged items={view.steps} as='li'>
        {(step) => {
          const spec = PHASE_SPEC[step.phase]
          return (
            <li
              key={step.phase}
              className={cn(
                'flex min-w-0 items-center gap-2 rounded-lg border p-2',
                step.current && 'border-primary bg-primary/5',
                !step.reached && 'opacity-50'
              )}
            >
              <Medallion
                icon={spec.icon}
                tone={step.reached ? spec.tone : 'muted'}
                size='sm'
              />
              <div className='flex min-w-0 flex-col'>
                <Text as='span' weight='medium' truncate>
                  {spec.label}
                </Text>
                <Muted as='span' variant='caption' truncate>
                  {step.current
                    ? `Now, since age ${step.since_epoch ?? view.phase_epoch}`
                    : step.reached
                      ? step.since_epoch !== null
                        ? `Age ${step.since_epoch}`
                        : 'Passed'
                      : 'Not reached'}
                </Muted>
              </div>
            </li>
          )
        }}
      </Paged>
    </ol>
  )
}

type Tally = {
  community_id: number
  community: string
  total: number
  ages: Record<string, number>
}

function tallies(view: EventView): Tally[] {
  const found = new Map<number, Tally>()
  for (const row of view.casualties) {
    const item = found.get(row.community_id) ?? {
      community_id: row.community_id,
      community: row.community,
      total: 0,
      ages: {},
    }
    item.total += row.count
    item.ages[row.age_band] = (item.ages[row.age_band] ?? 0) + row.count
    found.set(row.community_id, item)
  }
  return [...found.values()].sort((a, b) => b.total - a.total)
}

function TollPanel({ view }: { view: EventView }) {
  const rows = tallies(view)
  const shown = useShowMore(rows, TOLL_SHOWN)
  return (
    <Panel
      title='The toll by cohort'
      icon={Skull}
      tone='danger'
      hint='Who died, by community and age'
    >
      {rows.length === 0 ? (
        <Muted>No one is counted among its dead.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-3'>
          {shown.visible.map((row) => (
            <li
              key={row.community_id}
              className='flex min-w-0 flex-col gap-1.5'
            >
              <div className='flex min-w-0 items-center justify-between gap-2'>
                <EntityLink kind='entity' id={String(row.community_id)}>
                  {row.community || `#${row.community_id}`}
                </EntityLink>
                <Badge size='sm' variant='destructive'>
                  <Skull />
                  {formatInteger(row.total)}
                </Badge>
              </div>
              {AGE_ORDER.map((age) => {
                const spec = AGE_SPEC[age]
                const count = row.ages[age] ?? 0
                return (
                  <StatBar
                    key={age}
                    label={spec.label}
                    icon={spec.icon}
                    value={count}
                    max={Math.max(1, row.total)}
                    tone={METER_TONE[spec.tone ?? 'muted']}
                  />
                )
              })}
            </li>
          ))}
        </ul>
      )}
      <ShowMore state={shown} noun={['community', 'communities']} />
    </Panel>
  )
}

function FootprintPanel({
  view,
  blocked,
}: {
  view: EventView
  blocked: string | null
}) {
  const names = useNames()
  const [region, setRegion] = useState<string | null>(null)
  const regions = useMemo(
    () =>
      (names.data ?? [])
        .filter(
          (entry) =>
            entry.kind === 'entity' &&
            entry.type === 'region' &&
            (view.world_id === null || entry.world_id === view.world_id)
        )
        .map((entry) => ({ value: String(entry.id), label: entry.name })),
    [names.data, view.world_id]
  )
  const reach = useGodAction({
    run: ({ id, present }: { id: number; present: boolean }) =>
      unwrap(
        api.POST('/api/actions/event:footprint', {
          body: { event_id: view.entity_id, region_id: id, present },
        })
      ),
  })
  const busy = blocked ?? (reach.isPending ? WORKING : null)
  return (
    <Panel
      title='Its reach'
      icon={MapPin}
      tone='warning'
      hint='The lands it touched'
    >
      <ul className='flex min-w-0 flex-col gap-1.5'>
        <Paged items={view.footprint} as='li'>
          {(item) => (
            <li
              key={item.region_id}
              className='flex min-w-0 items-center gap-2 rounded-lg border bg-muted/30 p-2'
            >
              <MapPin
                aria-hidden='true'
                className='size-icon-xs text-warning'
              />
              <EntityLink kind='entity' id={String(item.region_id)}>
                {item.region || `#${item.region_id}`}
              </EntityLink>
              <Muted as='span' variant='caption' className='ms-auto'>
                {`Since age ${item.joined_epoch}`}
              </Muted>
              <Button
                size='icon'
                variant='ghost'
                aria-label={`Remove ${item.region}`}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  reach.mutate({ id: item.region_id, present: false })
                }
              >
                <Minus />
              </Button>
            </li>
          )}
        </Paged>
      </ul>
      <div className='flex min-w-0 items-center gap-2'>
        <div className='min-w-0 flex-1'>
          <RecordCombobox
            options={regions}
            value={region}
            onChange={(value) => setRegion(value)}
            placeholder='Add a land'
            aria-label='Land to add to its reach'
            disabled={busy !== null}
          />
        </div>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || region === null}
          disabledReason={
            busy ?? (region === null ? 'Choose a land first' : undefined)
          }
          onClick={() =>
            region && reach.mutate({ id: Number(region), present: true })
          }
        >
          <Plus />
          Add
        </Button>
      </div>
    </Panel>
  )
}

function PhaseControls({
  view,
  blocked,
}: {
  view: EventView
  blocked: string | null
}) {
  const move = useGodAction({
    run: ({ phase, hold }: { phase: EventPhase; hold: boolean }) =>
      unwrap(
        api.POST('/api/actions/event:phase', {
          body: { event_id: view.entity_id, phase, hold },
        })
      ),
  })
  const end = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/event:end', {
          body: { event_id: view.entity_id },
        })
      ),
  })
  const busy = blocked ?? (move.isPending || end.isPending ? WORKING : null)
  return (
    <EditorGroup title='Its course' icon={Flag}>
      {PHASE_ORDER.map((phase) => {
        const spec = PHASE_SPEC[phase]
        const here = view.phase === phase && !view.ended
        return (
          <Panel
            key={phase}
            title={spec.label}
            icon={spec.icon}
            tone={here ? spec.tone : 'muted'}
            hint={spec.hint}
          >
            <div className='mt-auto flex min-w-0 flex-wrap gap-1.5'>
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null || here}
                disabledReason={busy ?? (here ? 'It is there now' : undefined)}
                onClick={() => move.mutate({ phase, hold: false })}
              >
                <Unlock />
                Move here
              </Button>
              <Button
                size='sm'
                variant='secondary'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => move.mutate({ phase, hold: true })}
              >
                <Lock />
                Hold here
              </Button>
            </div>
          </Panel>
        )
      })}
      <Panel
        title='End it'
        icon={Flag}
        tone='success'
        hint='Close the event now, in this age'
      >
        <Button
          size='sm'
          variant='outline'
          className='mt-auto'
          disabled={busy !== null || view.ended}
          disabledReason={
            busy ?? (view.ended ? 'It is already over' : undefined)
          }
          onClick={() => end.mutate(undefined)}
        >
          <Flag />
          End the event
        </Button>
      </Panel>
    </EditorGroup>
  )
}

function RecordControls({
  view,
  blocked,
}: {
  view: EventView
  blocked: string | null
}) {
  const edit = useGodAction({
    run: (values: Record<string, number | string | null>) =>
      unwrap(
        api.POST('/api/actions/event:edit', {
          body: { event_id: view.entity_id, values, lock: true },
        })
      ),
  })
  const busy = blocked ?? (edit.isPending ? WORKING : null)
  const seasons = Object.fromEntries([
    [
      NO_SEASON,
      { label: 'No season', icon: CalendarRange, tone: 'muted' as const },
    ],
    ...view.seasons.map((season) => [
      String(season.position),
      { label: season.name, icon: CalendarRange, tone: 'gold' as const },
    ]),
  ])
  const numbers = [
    {
      key: 'severity',
      label: 'Severity',
      icon: Gauge,
      value: view.severity ?? 0,
      min: 0,
      max: PERCENT,
    },
    {
      key: 'start_year',
      label: fieldLabel('start_year'),
      icon: CalendarRange,
      value: view.start_year ?? 0,
      min: 0,
      max: 1000000,
    },
    {
      key: 'end_year',
      label: fieldLabel('end_year'),
      icon: CalendarRange,
      value: view.end_year ?? view.start_year ?? 0,
      min: 0,
      max: 1000000,
    },
  ]
  return (
    <EditorGroup title='Its record' icon={CalendarRange}>
      {numbers.map((field) => (
        <NumberEditor
          key={`${field.key}-${field.value}`}
          id={`event-${view.entity_id}`}
          field={field}
          held={view.locked.includes(field.key)}
          blocked={busy}
          pending={edit.isPending}
          onSet={(value) => edit.mutate({ [field.key]: value })}
        />
      ))}
      {(['start_season', 'end_season'] as const).map((key) => {
        const current =
          key === 'start_season' ? view.start_season : view.end_season
        return (
          <div
            key={key}
            className='flex min-w-0 flex-col gap-1.5 rounded-lg border bg-card p-3'
          >
            <IconPicker
              label={fieldLabel(key)}
              value={current ? String(current.position) : NO_SEASON}
              table={seasons}
              blocked={busy}
              onPick={(value) =>
                edit.mutate({
                  [key]: value === NO_SEASON ? null : Number(value),
                })
              }
            />
          </div>
        )
      })}
    </EditorGroup>
  )
}

function CasualtyControls({
  view,
  blocked,
}: {
  view: EventView
  blocked: string | null
}) {
  const names = useNames()
  const [community, setCommunity] = useState<string | null>(
    view.casualties[0] ? String(view.casualties[0].community_id) : null
  )
  const [age, setAge] = useState<AgeBand>('adult')
  const [sex, setSex] = useState<Sex>('male')
  const [social, setSocial] = useState<SocialClass>('farmer')
  const [phase, setPhase] = useState<EventPhase>(view.phase)
  const [count, setCount] = useState('0')
  const communities = useMemo(
    () =>
      (names.data ?? [])
        .filter(
          (entry) =>
            entry.kind === 'entity' &&
            (entry.type === 'settlement' || entry.type === 'people') &&
            (view.world_id === null || entry.world_id === view.world_id)
        )
        .map((entry) => ({ value: String(entry.id), label: entry.name })),
    [names.data, view.world_id]
  )
  const toll = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/event:casualties', {
          body: {
            event_id: view.entity_id,
            community_id: Number(community),
            age_band: age,
            sex,
            social_class: social,
            phase,
            count: Math.max(0, Number(count) || 0),
          },
        })
      ),
  })
  const busy = blocked ?? (toll.isPending ? WORKING : null)
  const reason =
    busy ?? (community === null ? 'Choose a community first' : null)
  return (
    <EditorGroup title='Its toll' icon={Users} pairs>
      <Panel
        title='Set the dead of one cohort'
        icon={Skull}
        tone='danger'
        hint='0 clears the cohort'
        wide
      >
        <RecordCombobox
          options={communities}
          value={community}
          onChange={(value) => setCommunity(value)}
          placeholder='Choose a community'
          aria-label='Community'
          disabled={busy !== null}
        />
        <div className='grid min-w-0 grid-cols-1 gap-2 @md:grid-cols-4'>
          <IconPicker
            label='Age'
            value={age}
            table={AGE_SPEC}
            blocked={busy}
            onPick={(value) => setAge(value as AgeBand)}
          />
          <IconPicker
            label='Sex'
            value={sex}
            table={SEX_SPEC}
            blocked={busy}
            onPick={(value) => setSex(value as Sex)}
          />
          <IconPicker
            label='Class'
            value={social}
            table={CLASS_SPEC}
            blocked={busy}
            onPick={(value) => setSocial(value as SocialClass)}
          />
          <IconPicker
            label='Phase'
            value={phase}
            table={PHASE_SPEC}
            blocked={busy}
            onPick={(value) => setPhase(value as EventPhase)}
          />
        </div>
        <div className='flex min-w-0 items-end gap-2'>
          <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
            <FieldLabel htmlFor={`toll-${view.entity_id}`}>Dead</FieldLabel>
            <Input
              id={`toll-${view.entity_id}`}
              type='number'
              min={0}
              value={count}
              disabled={busy !== null}
              onChange={(event) => setCount(event.target.value)}
            />
          </div>
          <Button
            size='sm'
            variant='outline'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
            onClick={() => toll.mutate(undefined)}
          >
            <Skull />
            Set the toll
          </Button>
        </div>
      </Panel>
    </EditorGroup>
  )
}

export function EventSection({
  eventId,
  readOnlyReason,
}: {
  eventId: number
  readOnlyReason?: string | null
}) {
  const view = useEventView(eventId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const release = useGodAction({
    run: (fields: string[]) =>
      Promise.all(
        fields.map((field) =>
          unwrap(
            api.POST('/api/actions/event:release', {
              body: {
                event_id: eventId,
                field: field as
                  | 'phase'
                  | 'start_year'
                  | 'start_season'
                  | 'end_year'
                  | 'end_season',
              },
            })
          )
        )
      ).then((results) => results[results.length - 1]),
  })
  const data = view.data
  const spec = kindSpec(data?.kind)
  const phase = data ? PHASE_SPEC[data.phase] : null
  const season = data ? seasonText(data) : null
  return (
    <Section
      id='section-event'
      title='The event'
      description='When it began and ended, the lands it reached, the phase it is in, and its dead by cohort.'
      icon={spec.icon}
      tone={spec.tone}
    >
      {view.isPending && <LoadingBlock label='Reading the event' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Not yet set down'
          description={view.error.message}
        />
      )}
      {data && phase && (
        <div
          data-surface='EventCard'
          className='@container/event flex min-w-0 flex-col gap-4'
        >
          <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
            <Medallion icon={spec.icon} tone={spec.tone} />
            <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
              <Text weight='semibold' className='first-letter:uppercase'>
                {data.name}
              </Text>
              <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                <Badge size='sm' variant='secondary'>
                  <spec.icon />
                  {spec.label}
                </Badge>
                <Badge
                  size='sm'
                  variant={
                    data.ended
                      ? 'success'
                      : data.phase === 'peak'
                        ? 'destructive'
                        : 'warning'
                  }
                >
                  <phase.icon />
                  {data.ended ? 'Over' : phase.label}
                </Badge>
                {data.locked.includes('phase') && (
                  <Badge size='sm' variant='default'>
                    <Lock />
                    Held
                  </Badge>
                )}
                {data.location_id !== null && (
                  <EntityLink
                    kind='entity'
                    id={String(data.location_id)}
                    showIcon
                  >
                    {data.location ?? 'Where it happened'}
                  </EntityLink>
                )}
              </div>
              <Muted variant='caption'>
                {`${yearsText(data)}${season ? `, ${season}` : ''}`}
              </Muted>
            </div>
          </div>
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl/event:grid-cols-4'>
            <KpiTile
              label='Dead'
              value={formatInteger(data.toll)}
              icon={Skull}
              tone={data.toll > 0 ? 'danger' : 'muted'}
              hint={data.toll > 0 ? 'Counted by cohort' : 'None counted'}
            />
            <KpiTile
              label='Lands'
              value={formatInteger(data.footprint.length)}
              icon={MapPin}
              tone='warning'
              hint='Within its reach'
            />
            <KpiTile
              label='Severity'
              value={formatInteger(data.severity ?? 0)}
              icon={Gauge}
              tone={badTone(data.severity ?? 0)}
              meter={{
                value: data.severity ?? 0,
                max: PERCENT,
                label: 'Severity',
              }}
            />
            <KpiTile
              label='Phase'
              value={data.ended ? 'Over' : phase.label}
              icon={phase.icon}
              tone={data.ended ? 'success' : phase.tone}
              hint={
                data.multi_season
                  ? 'It moves through its phases each age'
                  : 'A single happening'
              }
            />
          </div>
          <PhaseTrack view={data} />
          {data.incident_text && (
            <div className='flex min-w-0 items-start gap-2 rounded-lg border bg-muted/30 p-3'>
              <Quote
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-primary'
              />
              <Text variant='prose'>{data.incident_text}</Text>
            </div>
          )}
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/event:grid-cols-2'>
            <TollPanel view={data} />
            <FootprintPanel view={data} blocked={blocked} />
          </div>
          <AdjustPanel
            title='Shape the event'
            note='Move or hold its phase, end it, change its years and seasons, its reach and its toll. Every change goes into the ledger and can be undone.'
          >
            <HeldStrip
              keys={data.locked}
              labelOf={fieldLabel}
              blocked={blocked ?? (release.isPending ? WORKING : null)}
              onRelease={(keys) => release.mutate(keys)}
            />
            <PhaseControls view={data} blocked={blocked} />
            <RecordControls view={data} blocked={blocked} />
            <CasualtyControls view={data} blocked={blocked} />
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}
