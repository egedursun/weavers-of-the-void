import { useMemo, useState } from 'react'
import {
  ArrowRightLeft,
  Gauge,
  Network,
  Save,
  TriangleAlert,
  Users,
  Fingerprint,
  Unlock,
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
  KpiTile,
  Section,
  StatBar,
  ValueRadar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { useDemography } from './api'
import {
  AGE_ORDER,
  AGE_SPEC,
  CLASS_ORDER,
  CLASS_SPEC,
  JOB_SPEC,
  choices,
  words,
  type AgeBand,
  type Job,
  type SocialClass,
} from './labels'

type Demography = components['schemas']['DemographyView']
type Cohort = components['schemas']['PopulationCohortView']

const WORKING = 'Working…'
const PERCENT = 100
const PALETTE = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
  'var(--color-info)',
  'var(--color-warning)',
  'var(--color-success)',
  'var(--color-destructive)',
  'var(--color-brand-verdigris)',
]
const SANKEY_WIDTH = 640
const SANKEY_ROW = 26
const SANKEY_GAP = 6
const SANKEY_NODE = 10
const SANKEY_LEFT = 150
const SANKEY_RIGHT = SANKEY_WIDTH - 150
const ANY = 'any'

function classColor(socialClass: SocialClass): string {
  return PALETTE[CLASS_ORDER.indexOf(socialClass) % PALETTE.length]
}

const PYRAMID_WIDTH = 640
const PYRAMID_ROW = 30
const PYRAMID_LABEL = 96
const PYRAMID_BAR = 22
const LEGEND_DOT = 5
const LABEL_SIZE = 11

function Pyramid({ cohorts }: { cohorts: Cohort[] }) {
  const rows = AGE_ORDER.map((band) => {
    const cells = cohorts.filter((cohort) => cohort.age_band === band)
    const side = (sex: 'female' | 'male') =>
      CLASS_ORDER.map((socialClass) => ({
        socialClass,
        count: cells
          .filter((cell) => cell.sex === sex && cell.social_class === socialClass)
          .reduce((sum, cell) => sum + cell.count, 0),
      })).filter((part) => part.count > 0)
    return { band, male: side('male'), female: side('female') }
  })
  const widest = Math.max(
    1,
    ...rows.flatMap((row) => [
      row.male.reduce((sum, part) => sum + part.count, 0),
      row.female.reduce((sum, part) => sum + part.count, 0),
    ])
  )
  const half = (PYRAMID_WIDTH - PYRAMID_LABEL) / 2
  const centre = PYRAMID_WIDTH / 2
  const present = CLASS_ORDER.filter((socialClass) => cohorts.some((cohort) => cohort.social_class === socialClass))
  return (
    <div data-surface='PopulationPyramid' className='flex min-w-0 flex-col gap-2'>
      <svg
        viewBox={`0 0 ${PYRAMID_WIDTH} ${rows.length * PYRAMID_ROW + PYRAMID_ROW}`}
        className='w-full min-w-0'
        role='img'
        aria-label='Population by age, sex and class'
      >
        <text x={centre - PYRAMID_LABEL / 2 - 4} y={LABEL_SIZE + 2} textAnchor='end' fontSize={LABEL_SIZE} className='fill-muted-foreground'>
          Men
        </text>
        <text x={centre + PYRAMID_LABEL / 2 + 4} y={LABEL_SIZE + 2} fontSize={LABEL_SIZE} className='fill-muted-foreground'>
          Women
        </text>
        {rows.map((row, index) => {
          const y = PYRAMID_ROW + index * PYRAMID_ROW
          let leftEdge = centre - PYRAMID_LABEL / 2
          let rightEdge = centre + PYRAMID_LABEL / 2
          return (
            <g key={row.band}>
              {row.male.map((part) => {
                const width = (part.count / widest) * half
                leftEdge -= width
                return (
                  <rect key={`m-${part.socialClass}`} x={leftEdge} y={y} width={width} height={PYRAMID_BAR} fill={classColor(part.socialClass)}>
                    <title>{`${CLASS_SPEC[part.socialClass].label}: ${formatInteger(part.count)}`}</title>
                  </rect>
                )
              })}
              <text x={centre} y={y + PYRAMID_BAR / 2} textAnchor='middle' dominantBaseline='middle' fontSize={LABEL_SIZE} className='fill-foreground'>
                {AGE_SPEC[row.band].label}
              </text>
              {row.female.map((part) => {
                const width = (part.count / widest) * half
                const x = rightEdge
                rightEdge += width
                return (
                  <rect key={`f-${part.socialClass}`} x={x} y={y} width={width} height={PYRAMID_BAR} fill={classColor(part.socialClass)}>
                    <title>{`${CLASS_SPEC[part.socialClass].label}: ${formatInteger(part.count)}`}</title>
                  </rect>
                )
              })}
            </g>
          )
        })}
      </svg>
      <div className='flex min-w-0 flex-wrap gap-3'>
        {present.map((socialClass) => (
          <span key={socialClass} className='flex items-center gap-1'>
            <svg aria-hidden='true' viewBox={`0 0 ${LEGEND_DOT * 2} ${LEGEND_DOT * 2}`} className='size-icon-sm'>
              <circle cx={LEGEND_DOT} cy={LEGEND_DOT} r={LEGEND_DOT} fill={classColor(socialClass)} />
            </svg>
            <Muted variant='caption'>{CLASS_SPEC[socialClass].label}</Muted>
          </span>
        ))}
      </div>
    </div>
  )
}

function MoveCohort({ view, blocked }: { view: Demography; blocked: string | null }) {
  const [count, setCount] = useState('100')
  const [source, setSource] = useState<string>('farmer')
  const [target, setTarget] = useState<string>('serf_or_slave')
  const [band, setBand] = useState<string>(ANY)
  const move = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/cohort:move', {
          body: {
            community_id: view.entity_id,
            count: Math.max(1, Math.round(Number(count) || 1)),
            source: source as SocialClass,
            target: target as SocialClass,
            band: band === ANY ? null : (band as AgeBand),
          },
        })
      ),
  })
  const busy = blocked ?? (move.isPending ? WORKING : null)
  const classes = Object.fromEntries(
    CLASS_ORDER.map((item) => [item, CLASS_SPEC[item].label])
  )
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-3'>
      <div className='flex w-28 flex-col gap-1'>
        <Label>How many</Label>
        <Input
          type='number'
          min={1}
          value={count}
          aria-label='How many'
          onChange={(event) => setCount(event.target.value)}
        />
      </div>
      <div className='min-w-36 flex-1'>
        <MindPicker label='From' value={source} table={classes} blocked={busy} onPick={setSource} />
      </div>
      <div className='min-w-36 flex-1'>
        <MindPicker label='Into' value={target} table={classes} blocked={busy} onPick={setTarget} />
      </div>
      <div className='min-w-32 flex-1'>
        <MindPicker
          label='Of age'
          value={band}
          table={{ [ANY]: 'Any age', ...Object.fromEntries(AGE_ORDER.map((item) => [item, AGE_SPEC[item].label])) }}
          blocked={busy}
          onPick={setBand}
        />
      </div>
      <Button
        size='sm'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => move.mutate(undefined)}
      >
        <ArrowRightLeft />
        Move them
      </Button>
    </div>
  )
}

export function DemographySection({
  communityId,
  readOnlyReason,
}: {
  communityId: number
  readOnlyReason?: string | null
}) {
  const view = useDemography(communityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const total = view.data?.cohorts.reduce((sum, cohort) => sum + cohort.count, 0) ?? 0
  return (
    <Section
      id='section-demography'
      title='Population'
      description='Who lives here by age, sex, class and condition; how each class fares; and the pressures on them.'
      icon={Users}
    >
      {view.isPending && <Muted>Counting the people…</Muted>}
      {view.isError && (
        <EmptyState icon={TriangleAlert} title='The census failed' description={view.error.message} />
      )}
      {view.data && view.data.cohorts.length === 0 && (
        <EmptyState icon={Users} title='Not counted yet' description='The people are counted at the end of the next epoch.' />
      )}
      {view.data && view.data.cohorts.length > 0 && (
        <div data-surface='Demography' className='flex min-w-0 flex-col gap-5'>
          <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
            <KpiTile label='Counted' value={formatInteger(total)} icon={Users} />
            <KpiTile
              label='Inequality'
              value={String(view.data.inequality)}
              icon={Gauge}
              tone={view.data.inequality > PERCENT / 2 ? 'danger' : 'muted'}
              hint='The gap between the most and least content class'
            />
            <KpiTile
              label='Levy strength'
              value={`${view.data.mobilisation_pct}%`}
              icon={Gauge}
              hint='Martial value and cohesion against an ordinary people'
            />
            <KpiTile
              label='Bound'
              value={formatInteger(
                view.data.cohorts
                  .filter((cohort) => cohort.social_class === 'serf_or_slave')
                  .reduce((sum, cohort) => sum + cohort.count, 0)
              )}
              icon={Users}
              tone='warning'
            />
          </div>
          <Pyramid cohorts={view.data.cohorts} />
          {view.data.classes.length > 0 && (
            <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
              {view.data.classes
                .filter((item) => item.share > 0)
                .map((item) => (
                  <StatBar
                    key={item.social_class}
                    label={`${CLASS_SPEC[item.social_class].label} (${item.share.toFixed(1)}%)`}
                    icon={CLASS_SPEC[item.social_class].icon}
                    value={item.satisfaction}
                    max={PERCENT}
                    tone={item.satisfaction < 30 ? 'destructive' : item.satisfaction > 65 ? 'success' : 'default'}
                  />
                ))}
            </div>
          )}
          {view.data.pressures.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>Pressures</Label>
              <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-3'>
                {view.data.pressures.map((item) => (
                  <StatBar
                    key={item.kind}
                    label={words(item.kind)}
                    icon={Gauge}
                    value={item.value}
                    max={PERCENT}
                    tone={item.value > 60 ? 'destructive' : item.value > 30 ? 'warning' : 'success'}
                  />
                ))}
              </div>
            </div>
          )}
          <MoveCohort view={view.data} blocked={blocked} />
        </div>
      )}
    </Section>
  )
}

type Flow = components['schemas']['LabourFlowView']

function Sankey({ flows, output }: { flows: Flow[]; output: Record<string, number> }) {
  const classes = CLASS_ORDER.filter((item) => flows.some((flow) => flow.social_class === item))
  const jobs = (Object.keys(JOB_SPEC) as Job[]).filter((item) => flows.some((flow) => flow.job === item))
  const total = Math.max(1, flows.reduce((sum, flow) => sum + flow.workers, 0))
  const rows = Math.max(classes.length, jobs.length)
  const height = rows * (SANKEY_ROW + SANKEY_GAP)
  const usable = height - SANKEY_GAP * rows
  const layout = (keys: string[], weight: (key: string) => number) => {
    let cursor = 0
    return Object.fromEntries(
      keys.map((key) => {
        const size = Math.max(2, (weight(key) / total) * usable)
        const placed = { top: cursor, size }
        cursor += size + SANKEY_GAP
        return [key, placed]
      })
    )
  }
  const left = layout(classes, (key) => flows.filter((flow) => flow.social_class === key).reduce((sum, flow) => sum + flow.workers, 0))
  const right = layout(jobs, (key) => flows.filter((flow) => flow.job === key).reduce((sum, flow) => sum + flow.workers, 0))
  const leftUsed: Record<string, number> = {}
  const rightUsed: Record<string, number> = {}
  return (
    <svg
      data-surface='LabourSankey'
      viewBox={`0 0 ${SANKEY_WIDTH} ${height}`}
      className='w-full min-w-0'
      role='img'
      aria-label='Workers of each class flowing into each kind of work'
    >
      {flows.map((flow) => {
        const width = Math.max(1, (flow.workers / total) * usable)
        const start = left[flow.social_class]
        const end = right[flow.job]
        const y1 = start.top + (leftUsed[flow.social_class] ?? 0) + width / 2
        const y2 = end.top + (rightUsed[flow.job] ?? 0) + width / 2
        leftUsed[flow.social_class] = (leftUsed[flow.social_class] ?? 0) + width
        rightUsed[flow.job] = (rightUsed[flow.job] ?? 0) + width
        const mid = (SANKEY_LEFT + SANKEY_RIGHT) / 2
        return (
          <path
            key={`${flow.social_class}-${flow.job}`}
            d={`M${SANKEY_LEFT},${y1} C${mid},${y1} ${mid},${y2} ${SANKEY_RIGHT},${y2}`}
            fill='none'
            stroke={classColor(flow.social_class)}
            strokeOpacity={0.45}
            strokeWidth={width}
          >
            <title>{`${CLASS_SPEC[flow.social_class].label} → ${JOB_SPEC[flow.job].label}: ${formatInteger(flow.workers)}`}</title>
          </path>
        )
      })}
      {classes.map((item) => (
        <g key={item}>
          <rect x={SANKEY_LEFT - SANKEY_NODE} y={left[item].top} width={SANKEY_NODE} height={left[item].size} fill={classColor(item)} rx={2} />
          <text x={SANKEY_LEFT - SANKEY_NODE - 6} y={left[item].top + left[item].size / 2} textAnchor='end' dominantBaseline='middle' fontSize={LABEL_SIZE} className='fill-foreground'>
            {CLASS_SPEC[item].label}
          </text>
        </g>
      ))}
      {jobs.map((item) => (
        <g key={item}>
          <rect x={SANKEY_RIGHT} y={right[item].top} width={SANKEY_NODE} height={right[item].size} fill='var(--muted-foreground)' rx={2} />
          <text x={SANKEY_RIGHT + SANKEY_NODE + 6} y={right[item].top + right[item].size / 2} dominantBaseline='middle' fontSize={LABEL_SIZE} className='fill-foreground'>
            {`${JOB_SPEC[item].label} · ${output[item] ?? PERCENT}%`}
          </text>
        </g>
      ))}
    </svg>
  )
}

export function LabourSection({ communityId }: { communityId: number }) {
  const view = useDemography(communityId)
  if (!view.data || view.data.labour.length === 0) return null
  const output = Object.fromEntries(view.data.labour.map((row) => [row.job, row.output_pct]))
  return (
    <Section
      id='section-labour'
      title='Work'
      description='Which classes do which work, and how well: output against an ordinary worker, after satisfaction, bondage and seasonal sickness.'
      icon={Network}
    >
      <Sankey flows={view.data.flows} output={output} />
      <div className='grid min-w-0 grid-cols-2 gap-2 md:grid-cols-4'>
        {view.data.labour
          .filter((row) => row.workers > 0)
          .map((row) => {
            const Icon = JOB_SPEC[row.job].icon
            return (
              <div key={row.job} className='flex min-w-0 items-center gap-2 rounded-lg border bg-muted/30 p-2'>
                <Icon aria-hidden='true' className='size-icon-sm shrink-0 text-muted-foreground' />
                <Text className='min-w-0 flex-1' truncate>
                  {JOB_SPEC[row.job].label}
                </Text>
                <Muted variant='caption'>{`${formatInteger(row.workers)} · ${row.output_pct}%`}</Muted>
              </div>
            )
          })}
      </div>
    </Section>
  )
}

const BIOLOGY_FIELDS = [
  { key: 'maturity_years', label: 'Comes of age at' },
  { key: 'adult_years', label: 'Years of adulthood' },
  { key: 'elder_years', label: 'Years of old age' },
  { key: 'fertility_pct', label: 'Fertility (%)' },
] as const
const CULTURE_FIELDS = [
  { key: 'cohesion', label: 'Cohesion' },
  { key: 'literacy', label: 'Literacy' },
  { key: 'urbanisation', label: 'Urbanisation' },
] as const
const AESTHETICS = ['austere', 'ornate', 'geometric', 'natural', 'macabre', 'celestial'] as const
const MARTIAL = ['shieldwall', 'horse_archer', 'skirmisher', 'chariot', 'phalanx', 'berserker', 'naval_raider', 'siege_engineer', 'war_magic', 'beast_war'] as const
const MARRIAGE = ['monogamy', 'polygyny', 'polyandry', 'group'] as const
const INHERITANCE = ['primogeniture', 'gavelkind', 'elective', 'by_merit', 'matrilineal'] as const

function ProfileForm({ view, blocked }: { view: Demography; blocked: string | null }) {
  const biology = view.biology
  const culture = view.culture
  const [numbers, setNumbers] = useState<Record<string, string>>(() => ({
    ...Object.fromEntries(BIOLOGY_FIELDS.map((field) => [field.key, String(biology?.[field.key] ?? '')])),
    ...Object.fromEntries(CULTURE_FIELDS.map((field) => [field.key, String(culture?.[field.key] ?? '')])),
  }))
  const [picks, setPicks] = useState<Record<string, string>>(() => ({
    aesthetic: culture?.aesthetic ?? 'geometric',
    martial_style: culture?.martial_style ?? 'shieldwall',
    marriage: culture?.marriage ?? 'monogamy',
    inheritance: culture?.inheritance ?? 'gavelkind',
  }))
  const [flags, setFlags] = useState({ endogamous: culture?.endogamous ?? false, slavery_lawful: culture?.slavery_lawful ?? false })
  const locked = [...(biology?.locked ?? []), ...(culture?.locked ?? [])]
  const save = useGodAction({
    run: (release: string[]) =>
      unwrap(
        api.POST('/api/actions/people:edit', {
          body: {
            people_id: view.people_id ?? view.entity_id,
            values:
              release.length > 0
                ? {}
                : {
                    ...Object.fromEntries(Object.entries(numbers).map(([key, value]) => [key, Math.round(Number(value) || 0)])),
                    ...picks,
                    ...flags,
                  },
            release,
          },
        })
      ),
  })
  const busy = blocked ?? (save.isPending ? WORKING : null)
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        {[...BIOLOGY_FIELDS, ...CULTURE_FIELDS].map((field) => (
          <div key={field.key} className='flex min-w-0 flex-col gap-1'>
            <Label>{field.label}</Label>
            <Input
              type='number'
              min={0}
              value={numbers[field.key]}
              aria-label={field.label}
              onChange={(event) => setNumbers((current) => ({ ...current, [field.key]: event.target.value }))}
            />
          </div>
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-4'>
        <MindPicker label='Aesthetic' value={picks.aesthetic} table={choices(AESTHETICS)} blocked={busy} onPick={(value) => setPicks((current) => ({ ...current, aesthetic: value }))} />
        <MindPicker label='Way of war' value={picks.martial_style} table={choices(MARTIAL)} blocked={busy} onPick={(value) => setPicks((current) => ({ ...current, martial_style: value }))} />
        <MindPicker label='Marriage' value={picks.marriage} table={choices(MARRIAGE)} blocked={busy} onPick={(value) => setPicks((current) => ({ ...current, marriage: value }))} />
        <MindPicker label='Inheritance' value={picks.inheritance} table={choices(INHERITANCE)} blocked={busy} onPick={(value) => setPicks((current) => ({ ...current, inheritance: value }))} />
      </div>
      <div className='flex min-w-0 flex-wrap gap-4'>
        {(['endogamous', 'slavery_lawful'] as const).map((key) => (
          <label key={key} className='flex items-center gap-2'>
            <Switch checked={flags[key]} disabled={busy !== null} onCheckedChange={(value) => setFlags((current) => ({ ...current, [key]: value }))} aria-label={words(key)} />
            <Text as='span'>{key === 'endogamous' ? 'Marry only among themselves' : 'Slavery is lawful'}</Text>
          </label>
        ))}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button size='sm' disabled={busy !== null} disabledReason={busy ?? undefined} onClick={() => save.mutate([])}>
          <Save />
          Hold these customs
        </Button>
        {locked.length > 0 && (
          <Button size='sm' variant='outline' disabled={busy !== null} disabledReason={busy ?? undefined} onClick={() => save.mutate(locked)}>
            <Unlock />
            Let them drift again
          </Button>
        )}
        {locked.map((key) => (
          <Badge key={key} variant='outline'>{`held: ${words(key)}`}</Badge>
        ))}
      </div>
    </div>
  )
}

export function PeopleProfileSection({ peopleId, readOnlyReason }: { peopleId: number; readOnlyReason?: string | null }) {
  const view = useDemography(peopleId)
  const { reason } = useGodGate()
  const [neighbour, setNeighbour] = useState<string>('all')
  const axes = useMemo(() => {
    if (!view.data) return []
    const chosen = neighbour === 'all' ? view.data.neighbours : view.data.neighbours.filter((item) => String(item.entity_id) === neighbour)
    return view.data.values.map((point) => {
      const others = chosen.flatMap((item) => item.values.filter((value) => value.axis === point.axis).map((value) => value.value))
      return {
        key: point.axis,
        label: words(point.axis),
        value: point.value,
        reference: others.length > 0 ? others.reduce((sum, value) => sum + value, 0) / others.length : null,
      }
    })
  }, [view.data, neighbour])
  if (!view.data || (!view.data.biology && !view.data.culture)) return null
  const blocked = readOnlyReason ?? reason()
  const neighbours = {
    all: 'All neighbours',
    ...Object.fromEntries(view.data.neighbours.map((item) => [String(item.entity_id), item.name])),
  }
  return (
    <Section
      id='section-people-profile'
      title='Folk and customs'
      description='How this people lives, ages, marries, inherits, fights and sees beauty; its values against its neighbours.'
      icon={Fingerprint}
    >
      <div data-surface='PeopleProfile' className='flex min-w-0 flex-col gap-5'>
        <div className='flex min-w-0 flex-wrap gap-2'>
          {view.data.biology && (
            <>
              <Badge variant='info'>{`Acclimatised to ${words(view.data.biology.acclimatised)} lands`}</Badge>
              <Badge variant='outline'>{`Lives on ${words(view.data.biology.staple)}`}</Badge>
            </>
          )}
          {view.data.culture && (
            <>
              <Badge variant='outline'>{`Fights as ${words(view.data.culture.martial_style)}`}</Badge>
              <Badge variant='outline'>{`${words(view.data.culture.aesthetic)} art`}</Badge>
              {view.data.culture.slavery_lawful && <Badge variant='warning'>Keeps slaves</Badge>}
            </>
          )}
        </div>
        {axes.length >= 3 && (
          <div className='flex min-w-0 flex-col gap-2'>
            {view.data.neighbours.length > 0 && (
              <div className='max-w-64'>
                <MindPicker label='Compared with' value={neighbour} table={neighbours} blocked={null} onPick={setNeighbour} />
              </div>
            )}
            <ValueRadar axes={axes} label='Values' referenceLabel={view.data.neighbours.length > 0 ? 'Neighbours' : null} />
          </div>
        )}
        <ProfileForm
          key={JSON.stringify([view.data.biology, view.data.culture])}
          view={view.data}
          blocked={blocked}
        />
      </div>
    </Section>
  )
}
