import { useState } from 'react'
import {
  Activity,
  Bug,
  CircleSlash,
  Dna,
  EyeOff,
  FlaskConical,
  Gauge,
  Hammer,
  Hourglass,
  Lock,
  MapPin,
  PawPrint,
  ScrollText,
  ShieldCheck,
  Skull,
  Sparkles,
  Swords,
  Thermometer,
  Trash2,
  Unlock,
  Wand2,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  EntityLink,
  Medallion,
  MiniStat,
  Paged,
  RangeField,
  ShowMore,
  StatBar,
  useShowMore,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AFFINITY_SPEC,
  AGE_SPEC,
  JOB_ORDER,
  JOB_SPEC,
  STATUS_SPEC,
  TARGET_ORDER,
  TARGET_SPEC,
  VECTOR_SPEC,
  type AgeBand,
  type ClimateAffinity,
  type DiseaseTarget,
  type DiseaseVector,
  type Job,
  type OutbreakStatus,
  type Spec,
  fieldLabel,
} from './labels'
import { EditorGroup, EditorTile, HeldStrip, IconPicker, Panel } from './parts'
import { METER_TONE, WORKING, badTone } from './tones'
import { useWorldOptions } from './worldOptions'

type Disease = components['schemas']['DiseaseView']
type Outbreak = components['schemas']['OutbreakView']
type ProfileValue = number | string | string[] | null

const PERCENT = 100
const ALL_BANDS = 'all'
const TARGET_JOBS: Record<DiseaseTarget, Job[]> = {
  breath: ['farming', 'herding', 'fishing', 'mining', 'building', 'soldiering'],
  vital: JOB_ORDER,
  cognition: ['scholarship', 'clergy', 'trade', 'crafting'],
  sight: ['crafting', 'scholarship', 'fishing', 'herding'],
  skin: ['trade', 'clergy'],
}
const LEVY_TARGETS = new Set<DiseaseTarget>(['breath', 'vital', 'sight'])
const DESIGN_NUMBERS = [
  { key: 'virulence', icon: Activity, min: 1, max: PERCENT, start: 40 },
  { key: 'lethality', icon: Skull, min: 1, max: PERCENT, start: 30 },
  { key: 'chronic_rate', icon: Hourglass, min: 0, max: PERCENT, start: 10 },
  { key: 'incubation', icon: Thermometer, min: 0, max: 20, start: 1 },
  { key: 'immunity_epochs', icon: ShieldCheck, min: 1, max: 1000, start: 6 },
  { key: 'mutation_rate', icon: Dna, min: 0, max: PERCENT, start: 8 },
  { key: 'stigma', icon: EyeOff, min: 0, max: PERCENT, start: 30 },
  { key: 'cure_level', icon: FlaskConical, min: 0, max: 20, start: 4 },
] as const
const OUTBREAK_NUMBERS = [
  { key: 'severity', icon: Gauge, max: PERCENT },
  { key: 'infected', icon: Thermometer, max: 1000000000 },
  { key: 'dead', icon: Skull, max: 1000000000 },
] as const
const BAND_SPEC: Record<string, Spec> = {
  [ALL_BANDS]: { label: 'Every age', icon: ShieldCheck },
  ...AGE_SPEC,
}

function TargetChips({
  value,
  blocked,
  onToggle,
}: {
  value: DiseaseTarget[]
  blocked: string | null
  onToggle: (target: DiseaseTarget) => void
}) {
  return (
    <div className='flex min-w-0 flex-wrap gap-1.5'>
      {TARGET_ORDER.map((target) => {
        const spec = TARGET_SPEC[target]
        const on = value.includes(target)
        const last = on && value.length === 1
        return (
          <Button
            key={target}
            size='sm'
            variant={on ? 'default' : 'outline'}
            aria-pressed={on}
            title={
              last ? 'A disease must strike at least one function' : undefined
            }
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => {
              if (!last) onToggle(target)
            }}
          >
            <spec.icon />
            {spec.label}
          </Button>
        )
      })}
    </div>
  )
}

export function StrikesPanel({ view }: { view: Disease }) {
  return (
    <Panel
      title='What it strikes'
      icon={Skull}
      tone='danger'
      hint='The body functions it wounds, the work the sick lose and whether they can still be levied'
    >
      <ul className='flex min-w-0 flex-col gap-2'>
        {view.target_functions.map((target) => {
          const spec = TARGET_SPEC[target]
          const jobs = TARGET_JOBS[target]
          return (
            <li
              key={target}
              className='flex min-w-0 items-start gap-2.5 rounded-lg border bg-muted/30 p-2'
            >
              <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
              <div className='flex min-w-0 flex-1 flex-col gap-1'>
                <Text weight='medium'>{spec.label}</Text>
                <Muted variant='caption'>{spec.hint}</Muted>
                <div className='flex min-w-0 flex-wrap gap-1'>
                  {jobs.length === JOB_ORDER.length && (
                    <Badge size='sm' variant='secondary'>
                      <Hammer />
                      Every kind of work
                    </Badge>
                  )}
                  {(jobs.length === JOB_ORDER.length ? [] : jobs).map((job) => {
                    const work = JOB_SPEC[job]
                    return (
                      <Badge key={job} size='sm' variant='secondary'>
                        <work.icon />
                        {work.label}
                      </Badge>
                    )
                  })}
                  {LEVY_TARGETS.has(target) && (
                    <Badge size='sm' variant='destructive'>
                      <Swords />
                      No levy
                    </Badge>
                  )}
                </div>
              </div>
            </li>
          )
        })}
      </ul>
      <Muted variant='caption'>
        {`Survivors may keep a lasting weakness there: ${view.chronic_rate} in 100 carry it for life.`}
      </Muted>
    </Panel>
  )
}

export function TravelPanel({ view }: { view: Disease }) {
  const vector = VECTOR_SPEC[view.vector]
  return (
    <Panel
      title='How it travels'
      icon={vector.icon}
      tone={vector.tone}
      hint={vector.hint}
    >
      <StatBar
        label='Spreads unseen in its first age'
        icon={EyeOff}
        value={view.unseen_pct}
        max={PERCENT}
        tone={METER_TONE[badTone(view.unseen_pct)]}
      />
      <Muted variant='caption'>
        {view.incubation > 0
          ? `It hides ${view.incubation} years before the sick show it, so travellers carry it off and quarantines close too late for ${view.unseen_pct}% of the first outbreak; part of its first toll falls an age later.`
          : 'It shows itself at once; quarantines catch it from the first day.'}
      </Muted>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <MiniStat
          icon={Thermometer}
          label='Lying sick now'
          value={formatInteger(view.sick)}
          tone={view.sick > 0 ? 'danger' : 'muted'}
          hint='People in the sick cohorts of the lands it rages in'
        />
        <MiniStat
          icon={vector.icon}
          label='Borne by'
          value={vector.label}
          tone={vector.tone}
          hint={vector.hint}
        />
      </div>
    </Panel>
  )
}

export function HostsPanel({ view }: { view: Disease }) {
  return (
    <Panel
      title='Carried by beasts'
      icon={PawPrint}
      tone='verdigris'
      hint='Host species keep it alive; killing them off starves it'
    >
      {view.hosts.length === 0 ? (
        <Muted>No beast carries it; it passes only between people.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={view.hosts} as='li'>
            {(host) => (
              <li
                key={host.species_id}
                className='flex min-w-0 items-center gap-2.5 rounded-lg border bg-muted/30 p-2'
              >
                <Medallion
                  icon={host.immune ? ShieldCheck : Bug}
                  tone={
                    host.abundance === 0
                      ? 'muted'
                      : host.immune
                        ? 'info'
                        : 'warning'
                  }
                  size='sm'
                />
                <div className='flex min-w-0 flex-1 flex-col gap-1'>
                  <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                    <EntityLink kind='entity' id={String(host.species_id)}>
                      {host.name}
                    </EntityLink>
                    {host.primary && (
                      <Badge size='sm' variant='default'>
                        Main host
                      </Badge>
                    )}
                    {host.immune && (
                      <Badge size='sm' variant='info'>
                        Immune
                      </Badge>
                    )}
                  </div>
                  <StatBar
                    label={
                      host.lands > 0
                        ? `Most abundant, in ${host.lands} lands`
                        : 'Gone from every land'
                    }
                    value={host.abundance}
                    max={PERCENT}
                    tone={host.abundance > 0 ? 'warning' : 'muted'}
                  />
                </div>
              </li>
            )}
          </Paged>
        </ul>
      )}
    </Panel>
  )
}

export function OriginLine({ view }: { view: Disease }) {
  if (!view.origin)
    return (
      <Muted variant='caption'>{`Emerged in epoch ${view.emerged_epoch}`}</Muted>
    )
  return (
    <div className='flex min-w-0 items-start gap-1.5'>
      <ScrollText
        aria-hidden='true'
        className='size-icon-xs shrink-0 text-muted-foreground'
      />
      <Muted variant='caption'>
        {`Rose in epoch ${view.origin.epoch}${view.origin.year !== null ? `, year ${view.origin.year}` : ''}: ${view.origin.text}`}
      </Muted>
      {view.origin.place_id !== null && (
        <EntityLink kind='entity' id={String(view.origin.place_id)} showIcon>
          The place
        </EntityLink>
      )}
    </div>
  )
}

export function OutbreakHolds({ item }: { item: Outbreak }) {
  return (
    <>
      {item.unseen_pct > 0 && (
        <Badge size='sm' variant='warning'>
          <EyeOff />
          {`${item.unseen_pct}% unseen`}
        </Badge>
      )}
      {item.locked.length > 0 && (
        <Badge size='sm' variant='default'>
          <Lock />
          {`${item.locked.length} held`}
        </Badge>
      )}
    </>
  )
}

export function ShapeControls({
  view,
  blocked,
}: {
  view: Disease
  blocked: string | null
}) {
  const options = useWorldOptions(view.entity_id)
  const edit = useGodAction({
    run: (body: {
      values?: Record<string, ProfileValue>
      release?: string[]
    }) =>
      unwrap(
        api.POST('/api/actions/disease:edit', {
          body: { disease_id: view.entity_id, hold: true, ...body },
        })
      ),
    success: (_result, body) =>
      body.release ? 'Released' : 'The sickness is reshaped',
  })
  const busy = blocked ?? (edit.isPending ? WORKING : null)
  const toggle = (target: DiseaseTarget) => {
    const next = view.target_functions.includes(target)
      ? view.target_functions.filter((item) => item !== target)
      : [...view.target_functions, target]
    edit.mutate({ values: { target_functions: next } })
  }
  const incidents: Record<string, Spec> = Object.fromEntries(
    view.incidents.map((item) => [
      String(item.id),
      { label: `Epoch ${item.epoch}: ${item.text}`, icon: ScrollText },
    ])
  )
  return (
    <>
      <EditorGroup title='What it strikes, what carries it' icon={Sparkles}>
        <EditorTile
          icon={Skull}
          tone={view.locked.includes('target_functions') ? 'gold' : 'muted'}
          label='Struck body functions'
          hint='Wounds the matching organ; the sick lose the work it serves'
          held={view.locked.includes('target_functions')}
        >
          <TargetChips
            value={view.target_functions}
            blocked={busy}
            onToggle={toggle}
          />
        </EditorTile>
        <EditorTile
          icon={PawPrint}
          tone={view.locked.includes('host_species_id') ? 'gold' : 'muted'}
          label='Host species'
          hint='The beast that carries it; none means people alone'
          held={view.locked.includes('host_species_id')}
        >
          <RecordCombobox
            options={options.species}
            value={
              view.host_species_id !== null
                ? String(view.host_species_id)
                : null
            }
            onChange={(value) =>
              edit.mutate({
                values: {
                  host_species_id: value === null ? null : Number(value),
                },
              })
            }
            placeholder='No host'
            aria-label='Host species'
            clearable
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
          />
        </EditorTile>
        <EditorTile
          icon={ScrollText}
          tone={view.locked.includes('origin_incident_id') ? 'gold' : 'muted'}
          label='Origin event'
          hint='The moment the world remembers it rising'
          held={view.locked.includes('origin_incident_id')}
        >
          {view.incidents.length === 0 && (
            <Muted variant='caption'>No event names it yet.</Muted>
          )}
          <IconPicker
            label='Rose in'
            value={
              view.origin_incident_id !== null
                ? String(view.origin_incident_id)
                : view.incidents.length > 0
                  ? String(view.incidents[0].id)
                  : ''
            }
            table={incidents}
            blocked={
              busy ??
              (view.incidents.length === 0 ? 'No event names it yet' : null)
            }
            onPick={(value) =>
              edit.mutate({ values: { origin_incident_id: Number(value) } })
            }
          />
        </EditorTile>
      </EditorGroup>
      <HeldStrip
        keys={view.locked}
        labelOf={fieldLabel}
        blocked={busy}
        onRelease={(keys) => edit.mutate({ release: keys })}
      />
    </>
  )
}

export function OutbreakControls({
  view,
  blocked,
}: {
  view: Disease
  blocked: string | null
}) {
  const live = view.outbreaks.filter((item) => item.status !== 'ended')
  const all = live.length > 0 ? live : view.outbreaks
  const [chosen, setChosen] = useState<string | null>(
    all.length > 0 ? String(all[0].id) : null
  )
  const item = view.outbreaks.find((row) => String(row.id) === chosen) ?? null
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const edit = useGodAction({
    run: (body: {
      values?: Record<string, number | string | boolean>
      release?: string[]
    }) =>
      unwrap(
        api.POST('/api/actions/outbreak:edit', {
          body: { outbreak_id: Number(chosen), hold: true, ...body },
        })
      ),
    success: (_result, body) =>
      body.release ? 'Released' : 'The outbreak is reshaped',
  })
  const busy = blocked ?? (edit.isPending ? WORKING : null)
  const outbreaks: Record<string, Spec> = Object.fromEntries(
    view.outbreaks.map((row) => [
      String(row.id),
      {
        label: `${row.region}, epoch ${row.started_epoch}`,
        icon: STATUS_SPEC[row.status].icon,
        tone: STATUS_SPEC[row.status].tone,
      },
    ])
  )
  if (!item || chosen === null)
    return (
      <EditorGroup title='Outbreaks' icon={MapPin}>
        <Muted>It has broken out nowhere yet.</Muted>
      </EditorGroup>
    )
  return (
    <EditorGroup title='Reshape an outbreak' icon={MapPin}>
      <IconPicker
        label='Outbreak'
        value={chosen}
        table={outbreaks}
        blocked={busy}
        onPick={(value) => {
          setChosen(value)
          setDrafts({})
        }}
      />
      {OUTBREAK_NUMBERS.map((field) => {
        const value = drafts[field.key] ?? String(item[field.key])
        const parsed = Number(value)
        const bad =
          !Number.isInteger(parsed) || parsed < 0 || parsed > field.max
        return (
          <EditorTile
            key={`${item.id}-${field.key}`}
            icon={field.icon}
            tone={item.locked.includes(field.key) ? 'gold' : 'muted'}
            label={fieldLabel(field.key)}
            htmlFor={`outbreak-${field.key}`}
            hint={`0–${formatInteger(field.max)}`}
            held={item.locked.includes(field.key)}
          >
            <div className='flex min-w-0 flex-col gap-2'>
              <Input
                id={`outbreak-${field.key}`}
                type='number'
                min={0}
                value={value}
                disabled={busy !== null}
                onChange={(event) =>
                  setDrafts({ ...drafts, [field.key]: event.target.value })
                }
              />
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null || bad}
                disabledReason={
                  busy ?? (bad ? 'Give a whole number in range' : undefined)
                }
                onClick={() => edit.mutate({ values: { [field.key]: parsed } })}
              >
                <Lock />
                Set and hold
              </Button>
            </div>
          </EditorTile>
        )
      })}
      <EditorTile
        icon={STATUS_SPEC[item.status].icon}
        tone={item.locked.includes('status') ? 'gold' : 'muted'}
        label='State'
        hint='Raging, waning or over; held, the course keeps it'
        held={item.locked.includes('status')}
      >
        <IconPicker
          label='State'
          value={item.status}
          table={STATUS_SPEC}
          blocked={busy}
          onPick={(value) =>
            edit.mutate({ values: { status: value as OutbreakStatus } })
          }
        />
      </EditorTile>
      <EditorTile
        icon={Lock}
        tone={item.quarantined ? 'info' : 'muted'}
        label='Sealed'
        hint='A sealed outbreak spreads as through a quarantine'
        held={item.locked.includes('quarantined')}
        control={
          <Switch
            checked={item.quarantined}
            disabled={busy !== null}
            aria-label='Seal the outbreak'
            onCheckedChange={(checked) =>
              edit.mutate({ values: { quarantined: checked } })
            }
          />
        }
      />
      <div className='col-span-full min-w-0'>
        <HeldStrip
          keys={item.locked}
          labelOf={fieldLabel}
          blocked={busy}
          onRelease={(keys) => edit.mutate({ release: keys })}
        />
      </div>
    </EditorGroup>
  )
}

export function EndemicControls({
  view,
  blocked,
}: {
  view: Disease
  blocked: string | null
}) {
  const options = useWorldOptions(view.entity_id)
  const [land, setLand] = useState<string | null>(
    view.endemic[0]
      ? String(view.endemic[0].region_id)
      : view.origin_region_id !== null
        ? String(view.origin_region_id)
        : null
  )
  const current = view.endemic.find((row) => String(row.region_id) === land)
  const [load, setLoad] = useState(current?.load ?? 20)
  const [hold, setHold] = useState(current?.locked ?? true)
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/endemic:set', {
          body: {
            region_id: Number(land),
            disease_id: view.entity_id,
            load: Math.max(1, Math.min(PERCENT, load)),
            hold,
          },
        })
      ),
  })
  const remove = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/endemic:remove', {
          body: { region_id: Number(land), disease_id: view.entity_id },
        })
      ),
  })
  const busy = blocked ?? (set.isPending || remove.isPending ? WORKING : null)
  const noLand = busy ?? (land === null ? 'Choose a land first' : null)
  return (
    <EditorGroup title='Where it lingers' icon={MapPin} pairs>
      <Panel
        title='Settle it in a land'
        icon={MapPin}
        tone='warning'
        hint='An endemic disease weighs on its land, guards locals against invaders and repels settlers'
      >
        <RecordCombobox
          options={options.lands}
          value={land}
          onChange={(value) => {
            setLand(value)
            const row = view.endemic.find(
              (item) => String(item.region_id) === value
            )
            if (row) {
              setLoad(row.load)
              setHold(row.locked)
            }
          }}
          placeholder='Choose a land'
          aria-label='Land where it lingers'
          disabled={busy !== null}
        />
        <RangeField
          label='Load'
          icon={Gauge}
          value={load}
          min={1}
          max={PERCENT}
          level={load >= 60 ? 'Heavy' : load >= 30 ? 'Steady' : 'Faint'}
          lowLabel='Faint'
          highLabel='Crushing'
          onChange={setLoad}
        />
        <div className='flex min-w-0 items-center justify-between gap-2'>
          <FieldLabel htmlFor={`endemic-hold-${view.entity_id}`}>
            Hold it against fading
          </FieldLabel>
          <Switch
            id={`endemic-hold-${view.entity_id}`}
            checked={hold}
            disabled={busy !== null}
            onCheckedChange={setHold}
          />
        </div>
        <div className='mt-auto flex min-w-0 flex-col gap-1.5'>
          <Button
            className='self-start'
            size='sm'
            variant='outline'
            disabled={noLand !== null}
            disabledReason={noLand ?? undefined}
            onClick={() => set.mutate(undefined)}
          >
            {hold ? <Lock /> : <Unlock />}
            {current ? 'Set its load' : 'Make it endemic here'}
          </Button>
          <Button
            className='self-start'
            size='sm'
            variant='outline'
            disabled={noLand !== null || !current}
            disabledReason={
              noLand ?? (!current ? 'It does not linger there' : undefined)
            }
            onClick={() => remove.mutate(undefined)}
          >
            <Trash2 />
            Free the land of it
          </Button>
        </div>
      </Panel>
      <Panel
        title='Lands it haunts'
        icon={MapPin}
        tone='warning'
        hint='Held loads are kept by the world as you set them'
      >
        {view.endemic.length === 0 ? (
          <Muted>It has settled nowhere.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            <Paged items={view.endemic} as='li'>
              {(row) => (
                <li
                  key={row.region_id}
                  className='flex min-w-0 items-center gap-2'
                >
                  <div className='min-w-0 flex-1'>
                    <StatBar
                      label={row.region}
                      value={row.load}
                      max={PERCENT}
                      tone={METER_TONE[badTone(row.load)]}
                    />
                  </div>
                  {row.locked && (
                    <Badge size='sm' variant='default'>
                      <Lock />
                      Held
                    </Badge>
                  )}
                </li>
              )}
            </Paged>
          </ul>
        )}
      </Panel>
    </EditorGroup>
  )
}

export function ImmunityControls({
  view,
  blocked,
}: {
  view: Disease
  blocked: string | null
}) {
  const options = useWorldOptions(view.entity_id)
  const [community, setCommunity] = useState<string | null>(null)
  const [band, setBand] = useState<string>(ALL_BANDS)
  const [pct, setPct] = useState(PERCENT)
  const [hold, setHold] = useState(true)
  const act = useGodAction({
    run: (forget: boolean) =>
      unwrap(
        api.POST('/api/actions/disease:immunity', {
          body: {
            disease_id: view.entity_id,
            community_id: Number(community),
            immune_pct: pct,
            age_band: band === ALL_BANDS ? null : (band as AgeBand),
            hold,
            forget,
          },
        })
      ),
  })
  const busy = blocked ?? (act.isPending ? WORKING : null)
  const none = busy ?? (community === null ? 'Choose a community first' : null)
  return (
    <Panel
      title='Grant or take resistance'
      icon={ShieldCheck}
      tone='info'
      hint='Set the immune share of one age band, or of every age, and hold it against fading'
    >
      <RecordCombobox
        options={options.communities}
        value={community}
        onChange={(value) => setCommunity(value)}
        placeholder='Choose a community'
        aria-label='Community to make immune'
        disabled={busy !== null}
      />
      <IconPicker
        label='Age band'
        value={band}
        table={BAND_SPEC}
        blocked={busy}
        onPick={setBand}
      />
      <RangeField
        label='Immune'
        icon={ShieldCheck}
        value={pct}
        min={0}
        max={PERCENT}
        level={`${pct}%`}
        lowLabel='None'
        highLabel='All'
        onChange={setPct}
      />
      <div className='flex min-w-0 items-center justify-between gap-2'>
        <FieldLabel htmlFor={`immunity-hold-${view.entity_id}`}>
          Hold it against fading
        </FieldLabel>
        <Switch
          id={`immunity-hold-${view.entity_id}`}
          checked={hold}
          disabled={busy !== null}
          onCheckedChange={setHold}
        />
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-1.5'>
        <Button
          className='self-start'
          size='sm'
          variant='outline'
          disabled={none !== null}
          disabledReason={none ?? undefined}
          onClick={() => act.mutate(false)}
        >
          <ShieldCheck />
          Set their resistance
        </Button>
        <Button
          className='self-start'
          size='sm'
          variant='outline'
          disabled={none !== null}
          disabledReason={none ?? undefined}
          onClick={() => act.mutate(true)}
        >
          <CircleSlash />
          Make them forget it
        </Button>
      </div>
    </Panel>
  )
}

function DesignNumber({
  field,
  value,
  blocked,
  onChange,
}: {
  field: (typeof DESIGN_NUMBERS)[number]
  value: number
  blocked: string | null
  onChange: (value: number) => void
}) {
  const id = `forge-${field.key}`
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <FieldLabel htmlFor={id} className='flex items-center gap-1.5'>
        <field.icon aria-hidden='true' className='size-icon-xs text-primary' />
        {fieldLabel(field.key)}
      </FieldLabel>
      <Input
        id={id}
        type='number'
        aria-label={`${fieldLabel(field.key)} of the new sickness`}
        min={field.min}
        max={field.max}
        value={value}
        disabled={blocked !== null}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </div>
  )
}

export function ForgeDisease({
  anchorId,
  landId,
  targetId,
  blocked,
}: {
  anchorId: number
  landId?: number | null
  targetId?: number | null
  blocked: string | null
}) {
  const options = useWorldOptions(anchorId)
  const [name, setName] = useState('')
  const [land, setLand] = useState<string | null>(
    landId !== undefined && landId !== null ? String(landId) : null
  )
  const [vector, setVector] = useState<DiseaseVector>('air')
  const [affinity, setAffinity] = useState<ClimateAffinity>('any')
  const [targets, setTargets] = useState<DiseaseTarget[]>(['breath'])
  const [host, setHost] = useState<string | null>(null)
  const [numbers, setNumbers] = useState<Record<string, number>>(
    Object.fromEntries(DESIGN_NUMBERS.map((field) => [field.key, field.start]))
  )
  const [hold, setHold] = useState(true)
  const [looseOn, setLooseOn] = useState<string | null>(
    targetId !== undefined && targetId !== null ? String(targetId) : null
  )
  const [severity, setSeverity] = useState(60)
  const forge = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/disease:create', {
          body: {
            region_id: Number(land),
            name: name.trim() === '' ? null : name.trim(),
            values: {
              vector,
              climate_affinity: affinity,
              target_functions: targets,
              host_species_id: host === null ? null : Number(host),
              ...numbers,
            },
            hold,
            loose_on: looseOn === null ? null : Number(looseOn),
            severity,
          },
        })
      ),
  })
  const busy = blocked ?? (forge.isPending ? WORKING : null)
  const outOfRange = DESIGN_NUMBERS.find((field) => {
    const value = numbers[field.key]
    return !Number.isInteger(value) || value < field.min || value > field.max
  })
  const shortName = name.trim().length === 1
  const reason =
    busy ??
    (land === null
      ? 'Choose the land where it rises'
      : outOfRange
        ? `${fieldLabel(outOfRange.key)} must be ${outOfRange.min}–${outOfRange.max}`
        : shortName
          ? 'A name needs at least two letters'
          : null)
  const spec = VECTOR_SPEC[vector]
  return (
    <div data-surface='ForgeDisease' className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 items-center gap-2.5 rounded-lg border border-primary/30 bg-primary/5 p-3'>
        <Medallion icon={Wand2} tone='gold' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold'>Forge a new sickness</Text>
          <Muted variant='caption'>
            Design every trait it carries. Left nameless, the world names it
            from its vector and its climate.
          </Muted>
        </div>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel htmlFor={`forge-name-${anchorId}`}>Name</FieldLabel>
          <Input
            id={`forge-name-${anchorId}`}
            value={name}
            placeholder='Named by the world'
            maxLength={120}
            disabled={busy !== null}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel>Rises in</FieldLabel>
          <RecordCombobox
            options={options.lands}
            value={land}
            onChange={(value) => setLand(value)}
            placeholder='Choose a land'
            aria-label='Land where it rises'
            disabled={busy !== null}
          />
        </div>
        <IconPicker
          label='Spreads by'
          value={vector}
          table={VECTOR_SPEC}
          blocked={busy}
          onPick={(value) => setVector(value as DiseaseVector)}
        />
        <IconPicker
          label='Thrives in'
          value={affinity}
          table={AFFINITY_SPEC}
          blocked={busy}
          onPick={(value) => setAffinity(value as ClimateAffinity)}
        />
      </div>
      <Muted variant='caption' className='flex items-center gap-1.5'>
        <spec.icon aria-hidden='true' className='size-icon-xs shrink-0' />
        {spec.hint}
      </Muted>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <FieldLabel>Strikes</FieldLabel>
        <TargetChips
          value={targets}
          blocked={busy}
          onToggle={(target) =>
            setTargets(
              targets.includes(target)
                ? targets.filter((item) => item !== target)
                : [...targets, target]
            )
          }
        />
      </div>
      <div className='flex min-w-0 flex-col gap-1.5'>
        <FieldLabel>Carried by</FieldLabel>
        <RecordCombobox
          options={options.species}
          value={host}
          onChange={(value) => setHost(value)}
          placeholder={
            vector === 'bite'
              ? 'A biting disease needs a host'
              : 'No host beast'
          }
          aria-label='Host species of the new sickness'
          clearable
          disabled={busy !== null}
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-3 @md:grid-cols-4'>
        {DESIGN_NUMBERS.map((field) => (
          <DesignNumber
            key={field.key}
            field={field}
            value={numbers[field.key]}
            blocked={busy}
            onChange={(value) => setNumbers({ ...numbers, [field.key]: value })}
          />
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 @md:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel>Loose it at once on</FieldLabel>
          <RecordCombobox
            options={options.targets}
            value={looseOn}
            onChange={(value) => setLooseOn(value)}
            placeholder='Keep it sleeping'
            aria-label='Where to loose the new sickness'
            clearable
            disabled={busy !== null}
          />
        </div>
        <RangeField
          label='First outbreak'
          icon={Gauge}
          value={severity}
          min={1}
          max={PERCENT}
          level={severity >= 60 ? 'Plague' : 'Sickness'}
          lowLabel='Mild'
          highLabel='Deadly'
          onChange={setSeverity}
        />
      </div>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
        <div className='flex min-w-0 items-center gap-2'>
          <Switch
            id={`forge-hold-${anchorId}`}
            checked={hold}
            disabled={busy !== null}
            onCheckedChange={setHold}
          />
          <FieldLabel htmlFor={`forge-hold-${anchorId}`}>
            Hold the design against the world
          </FieldLabel>
        </div>
        <Button
          size='sm'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          onClick={() => forge.mutate(undefined)}
        >
          <Hammer />
          {looseOn === null ? 'Forge it' : 'Forge and loose it'}
        </Button>
      </div>
    </div>
  )
}

const TARGET_PAGE = 12

export function TargetBadges({ targets }: { targets: DiseaseTarget[] }) {
  const more = useShowMore(targets, TARGET_PAGE)
  return (
    <span className='inline-flex min-w-0 flex-col gap-1'>
      <span className='inline-flex min-w-0 flex-wrap items-center gap-1'>
        {more.visible.map((target) => {
          const spec = TARGET_SPEC[target]
          return (
            <Badge key={target} size='sm' variant='warning'>
              <spec.icon />
              {spec.label}
            </Badge>
          )
        })}
      </span>
      <ShowMore state={more} noun={['target', 'targets']} />
    </span>
  )
}
