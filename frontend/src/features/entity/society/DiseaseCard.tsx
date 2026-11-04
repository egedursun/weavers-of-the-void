import { type ReactNode, useMemo, useState } from 'react'
import {
  Activity,
  Biohazard,
  CircleSlash,
  CloudRain,
  Dna,
  EyeOff,
  FlaskConical,
  Gauge,
  HeartPulse,
  Hourglass,
  Lock,
  MapPin,
  PawPrint,
  Shield,
  ShieldCheck,
  Skull,
  Sparkles,
  Thermometer,
  TriangleAlert,
  Users,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  EmptyState,
  EntityLink,
  IconStat,
  KpiTile,
  type KpiTone,
  Medallion,
  MiniStat,
  RangeField,
  Section,
  StatBar,
  Timeline,
  TimelineItem,
  type TimelineTone,
  Paged,
  LoadingBlock,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { useNames } from '../api/queries'
import { useDisease } from './api'
import {
  EndemicControls,
  ForgeDisease,
  HostsPanel,
  ImmunityControls,
  OriginLine,
  OutbreakControls,
  OutbreakHolds,
  ShapeControls,
  StrikesPanel,
  TravelPanel,
} from './diseaseParts'
import {
  AFFINITY_SPEC,
  AGE_SPEC,
  CURE_SPEC,
  PATH_SPEC,
  STATUS_SPEC,
  TARGET_SPEC,
  VECTOR_SPEC,
  fieldLabel,
} from './labels'
import {
  AdjustPanel,
  ChoiceEditor,
  EditorGroup,
  type NumberField,
  NumberEditor,
  Panel,
} from './parts'
import { METER_TONE, WORKING, badTone } from './tones'

type Disease = components['schemas']['DiseaseView']
type Outbreak = components['schemas']['OutbreakView']

const PERCENT = 100
const CURE_MAX = 20
const LAND_TYPES = new Set(['region'])
const COMMUNITY_TYPES = new Set(['people', 'settlement', 'faction', 'cult'])
const NATURE = [
  { key: 'virulence', icon: Activity, min: 1, max: PERCENT, unit: '' },
  { key: 'lethality', icon: Skull, min: 1, max: PERCENT, unit: '' },
  { key: 'chronic_rate', icon: Hourglass, min: 0, max: PERCENT, unit: '' },
  { key: 'mutation_rate', icon: Dna, min: 0, max: PERCENT, unit: '' },
  { key: 'stigma', icon: EyeOff, min: 0, max: PERCENT, unit: '' },
  { key: 'incubation', icon: Thermometer, min: 0, max: 20, unit: 'years' },
  {
    key: 'immunity_epochs',
    icon: ShieldCheck,
    min: 1,
    max: 1000,
    unit: 'epochs',
  },
  { key: 'cure_level', icon: FlaskConical, min: 0, max: CURE_MAX, unit: '' },
] as const
const SPREAD_KEYS = ['virulence', 'incubation'] as const
const HARM_KEYS = ['lethality', 'chronic_rate', 'stigma'] as const
const LAST_KEYS = ['mutation_rate', 'immunity_epochs', 'cure_level'] as const
const BARS = [
  { key: 'virulence', icon: Activity, hint: 'How readily it passes on' },
  { key: 'lethality', icon: Skull, hint: 'How many of the sick it kills' },
  {
    key: 'chronic_rate',
    icon: Hourglass,
    hint: 'How many carry it for life',
  },
  { key: 'mutation_rate', icon: Dna, hint: 'How fast new strains break off' },
  { key: 'stigma', icon: EyeOff, hint: 'How the sick are shunned' },
] as const

const TIMELINE_TONE: Record<Outbreak['status'], TimelineTone> = {
  active: 'destructive',
  waning: 'warning',
  ended: 'success',
}

const SEVERITY_LEVELS = [
  { at: 80, label: 'A great dying' },
  { at: 60, label: 'Plague' },
  { at: 35, label: 'Epidemic' },
  { at: 0, label: 'Sickness' },
]

function severityLevel(value: number): string {
  return SEVERITY_LEVELS.find((level) => value >= level.at)?.label ?? 'Sickness'
}

function OutbreakItem({
  item,
  last,
  blocked,
  onEnd,
}: {
  item: Outbreak
  last: boolean
  blocked: string | null
  onEnd: () => void
}) {
  const status = STATUS_SPEC[item.status]
  const path = PATH_SPEC[item.path]
  return (
    <TimelineItem
      icon={path.icon}
      tone={TIMELINE_TONE[item.status]}
      title={item.region}
      timestamp={
        item.ended_epoch !== null
          ? `Epoch ${item.started_epoch} to ${item.ended_epoch}`
          : `Since epoch ${item.started_epoch}`
      }
      last={last}
      framed
    >
      <div className='flex min-w-0 flex-col gap-2.5'>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge
            size='sm'
            variant={
              item.status === 'active'
                ? 'destructive'
                : item.status === 'waning'
                  ? 'warning'
                  : 'success'
            }
          >
            <status.icon />
            {status.label}
          </Badge>
          <Badge size='sm' variant='secondary'>
            <path.icon />
            {path.label}
          </Badge>
          {item.quarantined && (
            <Badge size='sm' variant='info'>
              <Lock />
              Sealed
            </Badge>
          )}
          <OutbreakHolds item={item} />
          {item.season_factor !== 100 && (
            <Badge
              size='sm'
              variant={item.season_factor > 100 ? 'warning' : 'secondary'}
            >
              <CloudRain />
              {item.season_factor > 100
                ? `Sickly season ×${(item.season_factor / 100).toFixed(1)}`
                : `Kind season ×${(item.season_factor / 100).toFixed(1)}`}
            </Badge>
          )}
          <EntityLink kind='entity' id={String(item.region_id)} showIcon>
            Open the land
          </EntityLink>
        </div>
        <StatBar
          label='Severity'
          icon={Gauge}
          value={item.severity}
          max={PERCENT}
          tone={METER_TONE[badTone(item.severity)]}
        />
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Badge size='sm' variant='warning'>
            <Thermometer />
            {`${formatInteger(item.infected)} fell sick`}
          </Badge>
          <Badge size='sm' variant='destructive'>
            <Skull />
            {`${formatInteger(item.dead)} died`}
          </Badge>
          {item.status !== 'ended' && (
            <Button
              size='sm'
              variant='outline'
              className='ms-auto'
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={onEnd}
            >
              <ShieldCheck />
              End it
            </Button>
          )}
        </div>
      </div>
    </TimelineItem>
  )
}

function Row({
  icon,
  tone,
  children,
  aside,
}: {
  icon: LucideIcon
  tone?: KpiTone
  children: ReactNode
  aside?: ReactNode
}) {
  return (
    <li className='flex min-w-0 items-center gap-2.5 rounded-lg border bg-muted/30 p-2'>
      <Medallion icon={icon} tone={tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1'>{children}</div>
      {aside}
    </li>
  )
}

function Reach({ view }: { view: Disease }) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @xl/sick:grid-cols-2'>
      <Panel
        title='Strains'
        icon={Dna}
        tone='verdigris'
        hint={
          view.parent_id !== null
            ? `Itself a strain of generation ${view.generation}`
            : 'Kinds that broke away from it'
        }
      >
        {view.parent_id === null && view.strains.length === 0 ? (
          <Muted>It has not changed its shape yet.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            {view.parent_id !== null && (
              <Row icon={Dna} tone='muted'>
                <EntityLink kind='entity' id={String(view.parent_id)}>
                  Its parent sickness
                </EntityLink>
              </Row>
            )}
            <Paged items={view.strains} as='li'>
              {(strain) => (
                <Row
                  key={strain.id}
                  icon={Dna}
                  tone='verdigris'
                  aside={
                    <div className='flex shrink-0 items-center gap-1.5'>
                      <IconStat
                        icon={Activity}
                        label='Virulence'
                        value={strain.virulence}
                        tone='warning'
                      />
                      <IconStat
                        icon={Skull}
                        label='Lethality'
                        value={strain.lethality}
                        tone='danger'
                      />
                    </div>
                  }
                >
                  <EntityLink kind='entity' id={String(strain.id)}>
                    {strain.name}
                  </EntityLink>
                  <Muted as='span' variant='caption'>
                    {`Generation ${strain.generation}`}
                  </Muted>
                </Row>
              )}
            </Paged>
          </ul>
        )}
      </Panel>
      <Panel
        title='Where it lingers'
        icon={MapPin}
        tone='warning'
        hint='Lands where it never fully leaves'
      >
        {view.endemic.length === 0 ? (
          <Muted>It has settled nowhere.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            <Paged items={view.endemic} as='li'>
              {(item) => (
                <Row key={item.region_id} icon={MapPin} tone='warning'>
                  <EntityLink kind='entity' id={String(item.region_id)}>
                    {item.region}
                  </EntityLink>
                  <StatBar
                    label={`Load, since epoch ${item.since_epoch}`}
                    value={item.load}
                    max={PERCENT}
                    tone={METER_TONE[badTone(item.load)]}
                  />
                </Row>
              )}
            </Paged>
          </ul>
        )}
      </Panel>
      <Panel
        title='Who knows the cure'
        icon={FlaskConical}
        tone='success'
        hint='Communities whose healers can end it'
      >
        {view.cures.length === 0 ? (
          <Muted>No healer has found the cure.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            <Paged items={view.cures} as='li'>
              {(item) => {
                const spec = CURE_SPEC[item.source]
                return (
                  <Row
                    key={item.community_id}
                    icon={spec.icon}
                    tone={spec.tone}
                  >
                    <EntityLink kind='entity' id={String(item.community_id)}>
                      {item.community}
                    </EntityLink>
                    <Muted as='span' variant='caption'>
                      {`${spec.label}, epoch ${item.since_epoch}`}
                    </Muted>
                  </Row>
                )
              }}
            </Paged>
          </ul>
        )}
      </Panel>
      <Panel
        title='Who resists it'
        icon={Shield}
        tone='info'
        hint='Immunity left by past sickness or granted'
      >
        {view.immunities.length === 0 ? (
          <Muted>No one has grown immune.</Muted>
        ) : (
          <ul className='flex min-w-0 flex-col gap-2'>
            <Paged items={view.immunities} as='li'>
              {(item) => {
                const age = AGE_SPEC[item.age_band]
                return (
                  <Row
                    key={`${item.community_id}-${item.age_band}`}
                    icon={age.icon}
                    tone='info'
                  >
                    <EntityLink kind='entity' id={String(item.community_id)}>
                      {item.community}
                    </EntityLink>
                    <StatBar
                      label={`${age.label} immune`}
                      value={item.immune_pct}
                      max={PERCENT}
                      tone='info'
                    />
                  </Row>
                )
              }}
            </Paged>
          </ul>
        )}
      </Panel>
    </div>
  )
}

function NatureControls({
  view,
  blocked,
}: {
  view: Disease
  blocked: string | null
}) {
  const edit = useGodAction({
    run: ({ key, value }: { key: string; value: number | string }) =>
      unwrap(
        api.POST('/api/actions/disease:edit', {
          body: {
            disease_id: view.entity_id,
            values: { [key]: value },
            hold: true,
          },
        })
      ),
    success: (_result, change) => `${fieldLabel(change.key)} set`,
  })
  const busy = blocked ?? (edit.isPending ? WORKING : null)
  const numbers = (keys: readonly string[]) =>
    NATURE.filter((item) => keys.includes(item.key)).map((item) => {
      const field: NumberField = {
        key: item.key,
        label: fieldLabel(item.key),
        icon: item.icon,
        value: view[item.key],
        min: item.min,
        max: item.max,
        unit: item.unit || undefined,
      }
      return (
        <NumberEditor
          key={`${field.key}-${field.value}`}
          id={`disease-${view.entity_id}`}
          field={field}
          held={view.locked.includes(field.key)}
          blocked={blocked}
          pending={edit.isPending && edit.variables?.key === field.key}
          onSet={(value) => edit.mutate({ key: field.key, value })}
        />
      )
    })
  return (
    <>
      <EditorGroup title='How it spreads' icon={Biohazard} pairs>
        <ChoiceEditor
          label='Spreads by'
          hint='How it passes from one to the next'
          value={view.vector}
          table={VECTOR_SPEC}
          held={view.locked.includes('vector')}
          blocked={busy}
          onPick={(value) => edit.mutate({ key: 'vector', value })}
        />
        <ChoiceEditor
          label='Thrives in'
          hint='Where it spreads fastest'
          value={view.climate_affinity}
          table={AFFINITY_SPEC}
          held={view.locked.includes('climate_affinity')}
          blocked={busy}
          onPick={(value) => edit.mutate({ key: 'climate_affinity', value })}
        />
        {numbers(SPREAD_KEYS)}
      </EditorGroup>
      <EditorGroup title='How it harms' icon={Skull}>
        {numbers(HARM_KEYS)}
      </EditorGroup>
      <EditorGroup title='How it lasts and ends' icon={Hourglass}>
        {numbers(LAST_KEYS)}
      </EditorGroup>
    </>
  )
}

function Levers({ view, blocked }: { view: Disease; blocked: string | null }) {
  const names = useNames()
  const [target, setTarget] = useState<string | null>(
    view.origin_region_id !== null ? String(view.origin_region_id) : null
  )
  const [land, setLand] = useState<string | null>(
    view.origin_region_id !== null ? String(view.origin_region_id) : null
  )
  const [community, setCommunity] = useState<string | null>(null)
  const [severity, setSeverity] = useState(60)
  const [epochs, setEpochs] = useState('2')
  const world = useMemo(
    () =>
      (names.data ?? []).find((entry) => entry.id === view.entity_id)
        ?.world_id ?? null,
    [names.data, view.entity_id]
  )
  const options = useMemo(() => {
    const local = (names.data ?? []).filter(
      (entry) =>
        entry.kind === 'entity' && (world === null || entry.world_id === world)
    )
    const pick = (types: Set<string>) =>
      local
        .filter((entry) => types.has(entry.type ?? ''))
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: fieldLabel(entry.type ?? ''),
        }))
    return {
      lands: pick(LAND_TYPES),
      communities: pick(COMMUNITY_TYPES),
      targets: pick(new Set([...LAND_TYPES, ...COMMUNITY_TYPES])),
    }
  }, [names.data, world])
  const loose = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/disease:loose', {
          body: {
            target_id: Number(target),
            disease_id: view.entity_id,
            severity: Math.max(1, Math.min(PERCENT, severity)),
          },
        })
      ),
  })
  const cure = useGodAction({
    run: (revoke: boolean) =>
      unwrap(
        api.POST('/api/actions/disease:cure', {
          body: {
            disease_id: view.entity_id,
            community_id: Number(community),
            revoke,
          },
        })
      ),
  })
  const immunity = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/disease:immunity', {
          body: {
            disease_id: view.entity_id,
            community_id: Number(community),
            immune_pct: PERCENT,
            forget: false,
          },
        })
      ),
  })
  const quarantine = useGodAction({
    run: (span: number) =>
      unwrap(
        api.POST('/api/actions/disease:quarantine', {
          body: { region_id: Number(land), epochs: span },
        })
      ),
  })
  const pending =
    loose.isPending ||
    cure.isPending ||
    immunity.isPending ||
    quarantine.isPending
  const busy = blocked ?? (pending ? WORKING : null)
  const noTarget =
    busy ?? (target === null ? 'Choose a land or community first' : null)
  const noLand = busy ?? (land === null ? 'Choose a land first' : null)
  const noCommunity =
    busy ?? (community === null ? 'Choose a community first' : null)
  return (
    <EditorGroup title='Loose, seal and heal' icon={Zap}>
      <Panel
        title='Loose it'
        icon={Biohazard}
        tone='danger'
        hint='Strike a land or community with it'
      >
        <RecordCombobox
          options={options.targets}
          value={target}
          onChange={(value) => setTarget(value)}
          placeholder='Choose a land or community'
          aria-label='Where to loose it'
          disabled={busy !== null}
        />
        <RangeField
          label='Severity'
          icon={Gauge}
          value={severity}
          min={1}
          max={PERCENT}
          level={severityLevel(severity)}
          lowLabel='Mild'
          highLabel='Deadly'
          onChange={setSeverity}
        />
        <Button
          size='sm'
          variant='destructive'
          className='mt-auto'
          disabled={noTarget !== null}
          disabledReason={noTarget ?? undefined}
          onClick={() => loose.mutate(undefined)}
        >
          <Biohazard />
          Loose it there
        </Button>
      </Panel>
      <Panel
        title='Seal a land'
        icon={Lock}
        tone='info'
        hint='Close roads and ports; 0 epochs lifts it'
      >
        <RecordCombobox
          options={options.lands}
          value={land}
          onChange={(value) => setLand(value)}
          placeholder='Choose a land'
          aria-label='Land to seal'
          disabled={busy !== null}
        />
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel htmlFor={`seal-${view.entity_id}`}>
            For how many epochs
          </FieldLabel>
          <Input
            id={`seal-${view.entity_id}`}
            type='number'
            min={0}
            value={epochs}
            disabled={busy !== null}
            onChange={(event) => setEpochs(event.target.value)}
          />
        </div>
        <Button
          size='sm'
          variant='outline'
          className='mt-auto'
          disabled={noLand !== null}
          disabledReason={noLand ?? undefined}
          onClick={() => quarantine.mutate(Math.max(0, Number(epochs) || 0))}
        >
          <Lock />
          Seal the land
        </Button>
      </Panel>
      <Panel
        title='Heal a community'
        icon={HeartPulse}
        tone='success'
        hint='Give or take the cure, or make them immune'
      >
        <RecordCombobox
          options={options.communities}
          value={community}
          onChange={(value) => setCommunity(value)}
          placeholder='Choose a community'
          aria-label='Community to heal'
          disabled={busy !== null}
        />
        <div className='mt-auto flex min-w-0 flex-col gap-1.5'>
          <Button
            className='self-start'
            size='sm'
            variant='outline'
            disabled={noCommunity !== null}
            disabledReason={noCommunity ?? undefined}
            onClick={() => cure.mutate(false)}
          >
            <FlaskConical />
            Give the cure
          </Button>
          <Button
            className='self-start'
            size='sm'
            variant='outline'
            disabled={noCommunity !== null}
            disabledReason={noCommunity ?? undefined}
            onClick={() => cure.mutate(true)}
          >
            <CircleSlash />
            Take the cure away
          </Button>
          <Button
            className='self-start'
            size='sm'
            variant='outline'
            disabled={noCommunity !== null}
            disabledReason={noCommunity ?? undefined}
            onClick={() => immunity.mutate(undefined)}
          >
            <ShieldCheck />
            Make them immune
          </Button>
        </div>
      </Panel>
    </EditorGroup>
  )
}

export function DiseaseSection({
  diseaseId,
  readOnlyReason,
}: {
  diseaseId: number
  readOnlyReason?: string | null
}) {
  const view = useDisease(diseaseId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const end = useGodAction({
    run: (outbreakId: number) =>
      unwrap(
        api.POST('/api/actions/outbreak:end', {
          body: { outbreak_id: outbreakId },
        })
      ),
  })
  const data = view.data
  const infected = data
    ? data.outbreaks.reduce((total, item) => total + item.infected, 0)
    : 0
  const dead = data
    ? data.outbreaks.reduce((total, item) => total + item.dead, 0)
    : 0
  const raging = data
    ? data.outbreaks.filter((item) => item.status !== 'ended').length
    : 0
  const vector = data ? VECTOR_SPEC[data.vector] : null
  const affinity = data ? AFFINITY_SPEC[data.climate_affinity] : null
  const origin = data?.outbreaks.find(
    (item) => item.region_id === data.origin_region_id
  )
  return (
    <Section
      id='section-disease'
      title='The sickness'
      description='How it spreads and kills, where it rose and raged, its strains, and who knows its cure or has grown immune.'
      icon={Biohazard}
      tone='danger'
    >
      {view.isPending && <LoadingBlock label='Reading the sickness' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Not yet studied'
          description={view.error.message}
        />
      )}
      {data && vector && affinity && (
        <div
          data-surface='DiseaseCard'
          className='@container/sick flex min-w-0 flex-col gap-4'
        >
          <div className='flex min-w-0 items-center gap-3 rounded-lg border bg-background p-3'>
            <Medallion icon={vector.icon} tone={vector.tone} />
            <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
              <Text weight='semibold' className='first-letter:uppercase'>
                {data.name}
              </Text>
              <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                <Badge size='sm' variant='destructive'>
                  <vector.icon />
                  {`Spreads by ${vector.label.toLowerCase()}`}
                </Badge>
                <Badge size='sm' variant='secondary'>
                  <affinity.icon />
                  {`Thrives in ${affinity.label.toLowerCase()}`}
                </Badge>
                {data.target_functions.map((item) => {
                  const spec = TARGET_SPEC[item]
                  return (
                    <Badge key={item} size='sm' variant='warning'>
                      <spec.icon />
                      {`Strikes the ${spec.label.toLowerCase()}`}
                    </Badge>
                  )
                })}
                {data.parent_id !== null && (
                  <Badge size='sm' variant='info'>
                    <Dna />
                    {`Strain, generation ${data.generation}`}
                  </Badge>
                )}
              </div>
              {data.hosts.length > 0 && (
                <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                  <Paged items={data.hosts}>
                    {(host) => (
                      <Badge
                        key={host.species_id}
                        size='sm'
                        variant='secondary'
                      >
                        <PawPrint />
                        {`Carried by ${host.name}`}
                      </Badge>
                    )}
                  </Paged>
                </div>
              )}
              <OriginLine view={data} />
              {origin && (
                <Muted variant='caption'>{`First outbreak in ${origin.region}`}</Muted>
              )}
            </div>
          </div>
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl/sick:grid-cols-4'>
            <KpiTile
              label='Outbreaks'
              value={formatInteger(data.outbreaks.length)}
              icon={Biohazard}
              tone={raging > 0 ? 'danger' : 'muted'}
              hint={raging > 0 ? `${raging} still raging` : 'All are over'}
            />
            <KpiTile
              label='Fell sick'
              value={formatInteger(infected)}
              icon={Thermometer}
              tone='warning'
              hint={
                data.outbreaks.length === 1
                  ? 'In one land'
                  : `Across ${data.outbreaks.length} lands`
              }
            />
            <KpiTile
              label='Dead'
              value={formatInteger(dead)}
              icon={Skull}
              tone='danger'
              hint={`${infected > 0 ? Math.round((dead / infected) * PERCENT) : 0}% of the sick died`}
              meter={{
                value: dead,
                max: Math.max(1, infected),
                label: 'Dead of the sick',
              }}
            />
            <KpiTile
              label='Cured in'
              value={formatInteger(data.cures.length)}
              icon={HeartPulse}
              tone={data.cures.length > 0 ? 'success' : 'muted'}
              hint='Communities whose healers know the cure'
            />
          </div>
          <Panel
            title='Its nature'
            icon={Sparkles}
            tone='danger'
            hint='How it spreads, kills and lasts; each out of 100'
          >
            <div className='grid min-w-0 grid-cols-1 gap-3 @xl/sick:grid-cols-2'>
              {BARS.map((item) => (
                <Tooltip key={item.key}>
                  <TooltipTrigger asChild>
                    <div
                      tabIndex={0}
                      className='min-w-0 @xl/sick:odd:last:col-span-2'
                    >
                      <StatBar
                        label={fieldLabel(item.key)}
                        icon={item.icon}
                        value={data[item.key]}
                        max={PERCENT}
                        tone={METER_TONE[badTone(data[item.key])]}
                      />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>{item.hint}</TooltipContent>
                </Tooltip>
              ))}
            </div>
            <div className='grid min-w-0 grid-cols-1 gap-2 @md/sick:grid-cols-3'>
              <MiniStat
                icon={Thermometer}
                label='Incubation'
                value={`${data.incubation} years`}
                tone='warning'
                hint='Years before the sick show it'
              />
              <MiniStat
                icon={ShieldCheck}
                label='Immunity lasts'
                value={`${formatInteger(data.immunity_epochs)} epochs`}
                tone='info'
                hint='How long survivors resist it'
              />
              <MiniStat
                icon={FlaskConical}
                label='Medicine to cure'
                value={`${data.cure_level} of ${CURE_MAX}`}
                tone='success'
                hint='The medicine a people needs before it can cure it'
              />
            </div>
          </Panel>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/sick:grid-cols-2'>
            <TravelPanel view={data} />
            <HostsPanel view={data} />
            <div className='min-w-0 @xl/sick:col-span-2'>
              <StrikesPanel view={data} />
            </div>
          </div>
          <Panel
            title='Outbreaks'
            icon={Users}
            tone='danger'
            hint='Where it rose and raged, oldest first'
          >
            {data.outbreaks.length === 0 ? (
              <Muted>It has broken out nowhere yet.</Muted>
            ) : (
              <Timeline label='Outbreaks'>
                <Paged items={data.outbreaks} as='li'>
                  {(item, index) => (
                    <OutbreakItem
                      key={item.id}
                      item={item}
                      last={index === data.outbreaks.length - 1}
                      blocked={blocked ?? (end.isPending ? WORKING : null)}
                      onEnd={() => end.mutate(item.id)}
                    />
                  )}
                </Paged>
              </Timeline>
            )}
          </Panel>
          <Reach view={data} />
          <AdjustPanel
            title='Shape the sickness'
            note='Change how it spreads, what it strikes and what carries it; reshape its outbreaks and where it lingers; loose it, seal lands, heal communities or forge a new sickness. Every change goes into the ledger and can be undone.'
          >
            <NatureControls view={data} blocked={blocked} />
            <ShapeControls view={data} blocked={blocked} />
            <OutbreakControls view={data} blocked={blocked} />
            <EndemicControls view={data} blocked={blocked} />
            <Levers view={data} blocked={blocked} />
            <EditorGroup title='Resistance by age' icon={ShieldCheck} pairs>
              <ImmunityControls view={data} blocked={blocked} />
            </EditorGroup>
            <ForgeDisease
              anchorId={data.entity_id}
              landId={data.origin_region_id}
              blocked={blocked}
            />
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}
