import { useMemo, useState } from 'react'
import {
  ArrowRightLeft,
  BookOpen,
  Building,
  Fingerprint,
  Gauge,
  Hammer,
  Ban,
  Hourglass,
  Link,
  Network,
  Palette,
  Scale,
  Sprout,
  Swords,
  TriangleAlert,
  Users,
  Users2,
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
import { Progress } from '@/components/ui/progress'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  EmptyState,
  KpiTile,
  type KpiTone,
  LoadingBlock,
  Medallion,
  MiniStat,
  Paged,
  PagedList,
  Section,
  StatBar,
  ValueRadar,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { COMMODITY, type CommodityKind } from '../economy/labels'
import { BAND, named } from '../environment/labels'
import { PRESSURE_ICONS, VALUE_ICONS } from '../mind/labels'
import { MindPicker } from '../mind/parts'
import { FolkBody, FolkControls, FolkWays, FoundPeoplePanel } from './Folk'
import { LabourDepth } from './LabourDepth'
import { useDemography } from './api'
import { DormancyPanel, SetCohort, SickCohorts } from './cohortParts'
import { ForgeDisease } from './diseaseParts'
import {
  AESTHETIC_SPEC,
  AGE_ORDER,
  AGE_SPEC,
  CLASS_ORDER,
  CLASS_SPEC,
  CONDITION_SPEC,
  INHERITANCE_SPEC,
  JOB_ORDER,
  JOB_SPEC,
  MARRIAGE_SPEC,
  MARTIAL_SPEC,
  PRESSURE_HINT,
  SEX_SPEC,
  type AgeBand,
  type CohortCondition,
  type Job,
  type Sex,
  type SocialClass,
  type Spec,
  fieldLabel,
} from './labels'
import { AdjustPanel, IconPicker, Panel } from './parts'
import {
  METER_TONE,
  TONE_COLOR,
  WORKING,
  badTone,
  goodTone,
  useWidth,
} from './tones'

type Demography = components['schemas']['DemographyView']
type Cohort = components['schemas']['PopulationCohortView']
type Flow = components['schemas']['LabourFlowView']
type Labour = components['schemas']['LabourView']

const PERCENT = 100
const OUTPUT_MAX = 200
const ANY = 'any'
const KEEP = 'keep'
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
const SANKEY_ROW = 30
const SANKEY_GAP = 8
const SANKEY_NODE = 10
const SANKEY_MIN_NODE = 16
const SANKEY_ICON = 13
const SANKEY_MIN = 360
const SANKEY_SHARE = 0.4
const SANKEY_PAD = 16
const LABEL_SIZE = 12
const PYRAMID_MIN = 320
const PYRAMID_ROW = 34
const PYRAMID_GAP = 6
const PYRAMID_LABEL = 104
const PYRAMID_COUNT = 52
const PYRAMID_CHAR = 6.6
const CONDITIONS: CohortCondition[] = [
  'veteran',
  'sick',
  'maimed',
  'enslaved',
  'captive',
]

function classColor(socialClass: SocialClass): string {
  return PALETTE[CLASS_ORDER.indexOf(socialClass) % PALETTE.length]
}

function sum<T>(items: T[], value: (item: T) => number): number {
  return items.reduce((total, item) => total + value(item), 0)
}

function moodOf(satisfaction: number): { label: string; tone: KpiTone } {
  if (satisfaction >= 65) return { label: 'Content', tone: 'success' }
  if (satisfaction >= 50) return { label: 'Settled', tone: 'gold' }
  if (satisfaction >= 35) return { label: 'Uneasy', tone: 'warning' }
  return { label: 'Angry', tone: 'danger' }
}

function outputTone(pct: number): KpiTone {
  if (pct >= 110) return 'success'
  if (pct >= 90) return 'gold'
  if (pct >= 60) return 'warning'
  return 'danger'
}

const BADGE: Record<
  KpiTone,
  'success' | 'default' | 'warning' | 'destructive' | 'info' | 'secondary'
> = {
  success: 'success',
  gold: 'default',
  warning: 'warning',
  danger: 'destructive',
  info: 'info',
  verdigris: 'info',
  muted: 'secondary',
}

const TEXT_TONE: Record<KpiTone, string> = {
  gold: 'text-primary',
  verdigris: 'text-brand-verdigris',
  info: 'text-info',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-destructive',
  muted: 'text-muted-foreground',
}

function Swatch({ color }: { color: string }) {
  return (
    <svg
      aria-hidden='true'
      viewBox='0 0 10 10'
      className='size-icon-xs shrink-0'
    >
      <circle cx={5} cy={5} r={4} fill={color} />
    </svg>
  )
}

type Part = { socialClass: SocialClass; count: number }

function Pyramid({ cohorts }: { cohorts: Cohort[] }) {
  const [ref, measured] = useWidth()
  const width = Math.max(PYRAMID_MIN, measured)
  const rows = AGE_ORDER.map((band) => {
    const cells = cohorts.filter((cohort) => cohort.age_band === band)
    const side = (sex: Sex): Part[] =>
      CLASS_ORDER.map((socialClass) => ({
        socialClass,
        count: sum(
          cells.filter(
            (cell) => cell.sex === sex && cell.social_class === socialClass
          ),
          (cell) => cell.count
        ),
      })).filter((part) => part.count > 0)
    return { band, male: side('male'), female: side('female') }
  })
  const widest = Math.max(
    1,
    ...rows.flatMap((row) => [
      sum(row.male, (part) => part.count),
      sum(row.female, (part) => part.count),
    ])
  )
  const total = Math.max(
    1,
    sum(cohorts, (cohort) => cohort.count)
  )
  const present = CLASS_ORDER.map((socialClass) => ({
    socialClass,
    count: sum(
      cohorts.filter((cohort) => cohort.social_class === socialClass),
      (cohort) => cohort.count
    ),
  })).filter((item) => item.count > 0)
  const bySex = (sex: Sex) =>
    sum(
      cohorts.filter((cohort) => cohort.sex === sex),
      (cohort) => cohort.count
    )
  const centre = width / 2
  const half = centre - PYRAMID_LABEL / 2 - PYRAMID_COUNT
  const height = rows.length * (PYRAMID_ROW + PYRAMID_GAP) - PYRAMID_GAP
  const bar = (parts: Part[], sex: Sex, top: number) => {
    let cursor = 0
    return parts.map((part) => {
      const size = (part.count / widest) * half
      const x =
        sex === 'male'
          ? centre - PYRAMID_LABEL / 2 - cursor - size
          : centre + PYRAMID_LABEL / 2 + cursor
      cursor += size
      return (
        <rect
          key={`${sex}-${part.socialClass}`}
          x={x}
          y={top}
          width={Math.max(1, size - 1)}
          height={PYRAMID_ROW}
          rx={3}
          fill={classColor(part.socialClass)}
        >
          <title>{`${SEX_SPEC[sex].label}, ${CLASS_SPEC[part.socialClass].label.toLowerCase()}: ${formatInteger(part.count)}`}</title>
        </rect>
      )
    })
  }
  return (
    <div
      data-surface='PopulationPyramid'
      className='flex min-w-0 flex-col gap-3'
    >
      <div className='flex min-w-0 items-center justify-between gap-3'>
        {(['male', 'female'] as const).map((sex) => {
          const spec = SEX_SPEC[sex]
          return (
            <div
              key={sex}
              className={
                sex === 'male'
                  ? 'flex min-w-0 items-center gap-1.5'
                  : 'flex min-w-0 flex-row-reverse items-center gap-1.5'
              }
            >
              <spec.icon
                aria-hidden='true'
                className={`size-icon-sm shrink-0 ${TEXT_TONE[spec.tone ?? 'muted']}`}
              />
              <Text as='span' weight='medium'>
                {spec.label}
              </Text>
              <Muted as='span'>{formatInteger(bySex(sex))}</Muted>
            </div>
          )
        })}
      </div>
      <div ref={ref} className='min-w-0'>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width='100%'
          className='block min-w-0'
          role='img'
          aria-label='Population by age, sex and class'
        >
          {rows.map((row, index) => {
            const top = index * (PYRAMID_ROW + PYRAMID_GAP)
            const middle = top + PYRAMID_ROW / 2
            const spec = AGE_SPEC[row.band]
            const male = sum(row.male, (part) => part.count)
            const female = sum(row.female, (part) => part.count)
            const reach = (count: number) => (count / widest) * half
            const textWidth = spec.label.length * PYRAMID_CHAR
            return (
              <g key={row.band}>
                <rect
                  x={centre - PYRAMID_LABEL / 2 - half}
                  y={top}
                  width={half * 2 + PYRAMID_LABEL}
                  height={PYRAMID_ROW}
                  rx={4}
                  className='fill-muted/40'
                />
                {bar(row.male, 'male', top)}
                {bar(row.female, 'female', top)}
                <text
                  x={centre - PYRAMID_LABEL / 2 - reach(male) - 6}
                  y={middle}
                  textAnchor='end'
                  dominantBaseline='middle'
                  fontSize={LABEL_SIZE}
                  className='fill-foreground tabular-nums'
                >
                  {formatInteger(male)}
                </text>
                <text
                  x={centre + PYRAMID_LABEL / 2 + reach(female) + 6}
                  y={middle}
                  dominantBaseline='middle'
                  fontSize={LABEL_SIZE}
                  className='fill-foreground tabular-nums'
                >
                  {formatInteger(female)}
                </text>
                <spec.icon
                  x={centre - (textWidth + SANKEY_ICON + 4) / 2}
                  y={top + 3}
                  width={SANKEY_ICON}
                  height={SANKEY_ICON}
                  className={TEXT_TONE[spec.tone ?? 'muted']}
                  aria-hidden='true'
                />
                <text
                  x={
                    centre - (textWidth + SANKEY_ICON + 4) / 2 + SANKEY_ICON + 4
                  }
                  y={top + 3 + SANKEY_ICON / 2}
                  dominantBaseline='middle'
                  fontSize={LABEL_SIZE}
                  className='fill-foreground'
                >
                  {spec.label}
                </text>
                <text
                  x={centre}
                  y={top + PYRAMID_ROW - 3}
                  textAnchor='middle'
                  fontSize={LABEL_SIZE - 1}
                  className='fill-muted-foreground'
                >
                  {`${Math.round(((male + female) / total) * PERCENT)}% of all`}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
      <PagedList
        items={present}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap gap-x-3 gap-y-1.5 border-t pt-3'
        itemKey={(item) => item.socialClass}
      >
        {(item) => (
          <span
            key={item.socialClass}
            className='flex min-w-0 items-center gap-1.5'
          >
            <Swatch color={classColor(item.socialClass)} />
            <Muted as='span' variant='caption'>
              {`${CLASS_SPEC[item.socialClass].label} ${((item.count / total) * PERCENT).toFixed(1)}%`}
            </Muted>
          </span>
        )}
      </PagedList>
    </div>
  )
}

function ClassRow({ item }: { item: Demography['classes'][number] }) {
  const spec = CLASS_SPEC[item.social_class]
  const mood = moodOf(item.satisfaction)
  return (
    <div className='flex min-w-0 items-center gap-2.5'>
      <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <div className='flex min-w-0 items-center gap-2'>
          <Text as='span' weight='medium' truncate className='min-w-0 flex-1'>
            {spec.label}
          </Text>
          <Muted as='span' variant='caption'>
            {`${item.share.toFixed(1)}%`}
          </Muted>
          <Badge size='sm' variant={BADGE[mood.tone]}>
            {`${mood.label} ${item.satisfaction}`}
          </Badge>
        </div>
        <Progress
          value={item.satisfaction}
          size='sm'
          tone={METER_TONE[mood.tone]}
          aria-label={`${spec.label} satisfaction`}
        />
      </div>
    </div>
  )
}

function MoveCohort({
  view,
  blocked,
}: {
  view: Demography
  blocked: string | null
}) {
  const [count, setCount] = useState('100')
  const [source, setSource] = useState<string>('farmer')
  const [target, setTarget] = useState<string>('serf_or_slave')
  const [band, setBand] = useState<string>(ANY)
  const [condition, setCondition] = useState<string>(KEEP)
  const [from, setFrom] = useState<string>(ANY)
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
            condition:
              condition === KEEP ? null : (condition as CohortCondition),
            from_condition: from === ANY ? null : (from as CohortCondition),
          },
        })
      ),
  })
  const busy = blocked ?? (move.isPending ? WORKING : null)
  const ages: Record<string, Spec> = {
    [ANY]: { label: 'Any age', icon: Users2 },
    ...AGE_SPEC,
  }
  const states: Record<string, Spec> = {
    [KEEP]: { label: 'As they are', icon: Users },
    ...CONDITION_SPEC,
  }
  const sources: Record<string, Spec> = {
    [ANY]: { label: 'Any condition', icon: Users },
    ...CONDITION_SPEC,
  }
  const parsed = Number(count)
  const invalid = !Number.isInteger(parsed) || parsed < 1
  return (
    <Panel
      title='Move people between classes'
      icon={ArrowRightLeft}
      hint='Raise, lower or bind a share of the people; the largest groups move first.'
    >
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md:grid-cols-2 @xl:grid-cols-3'>
        <IconPicker
          label='From'
          value={source}
          table={CLASS_SPEC}
          blocked={busy}
          onPick={setSource}
        />
        <IconPicker
          label='Into'
          value={target}
          table={CLASS_SPEC}
          blocked={busy}
          onPick={setTarget}
        />
        <div className='flex min-w-0 flex-col gap-1.5'>
          <FieldLabel htmlFor={`move-count-${view.entity_id}`}>
            How many
          </FieldLabel>
          <Input
            id={`move-count-${view.entity_id}`}
            type='number'
            min={1}
            value={count}
            disabled={busy !== null}
            onChange={(event) => setCount(event.target.value)}
          />
        </div>
        <IconPicker
          label='Of age'
          value={band}
          table={ages}
          blocked={busy}
          onPick={setBand}
        />
        <IconPicker
          label='Who are'
          value={from}
          table={sources}
          blocked={busy}
          onPick={setFrom}
        />
        <IconPicker
          label='Mark them as'
          value={condition}
          table={states}
          blocked={busy}
          onPick={setCondition}
        />
        <div className='flex min-w-0 items-end'>
          <Button
            size='sm'
            className='w-full'
            disabled={
              busy !== null ||
              invalid ||
              (source === target && (condition === KEEP || condition === from))
            }
            disabledReason={
              busy ??
              (invalid
                ? 'Give a whole number of people.'
                : 'Choose a different class or condition.')
            }
            onClick={() => move.mutate(undefined)}
          >
            <ArrowRightLeft />
            Move them
          </Button>
        </div>
      </div>
    </Panel>
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
  const data = view.data
  const cohorts = data?.cohorts ?? []
  const total = sum(cohorts, (cohort) => cohort.count)
  const bound = sum(
    cohorts.filter(
      (cohort) =>
        cohort.social_class === 'serf_or_slave' ||
        cohort.condition === 'enslaved' ||
        cohort.condition === 'captive'
    ),
    (cohort) => cohort.count
  )
  const worst = [...(data?.pressures ?? [])].sort(
    (left, right) => right.value - left.value
  )[0]
  return (
    <Section
      id='section-demography'
      title='Population'
      description='Who lives here by age, sex, class and condition; how each class fares; and the pressures on them.'
      icon={Users}
    >
      {view.isPending && <LoadingBlock label='Counting the people' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The census failed'
          description={view.error.message}
        />
      )}
      {data && cohorts.length === 0 && (
        <EmptyState
          icon={Users}
          title='Not counted yet'
          description='The people are counted at the end of the next epoch.'
        />
      )}
      {data && cohorts.length > 0 && (
        <div
          data-surface='Demography'
          className='@container/demo flex min-w-0 flex-col gap-4'
        >
          <div className='grid min-w-0 grid-cols-2 gap-3 @xl/demo:grid-cols-4'>
            <KpiTile
              label='People'
              value={formatInteger(total)}
              icon={Users}
              tone='gold'
              hint={`${formatInteger(
                sum(
                  cohorts.filter((cohort) => cohort.age_band === 'child'),
                  (cohort) => cohort.count
                )
              )} children`}
            />
            <KpiTile
              label='Inequality'
              value={data.inequality}
              icon={Scale}
              tone={badTone(data.inequality)}
              hint='Gap between the happiest and the angriest class'
              meter={{
                value: data.inequality,
                max: PERCENT,
                label: 'Inequality',
              }}
            />
            <KpiTile
              label='Levy'
              value={`${data.mobilisation_pct}%`}
              icon={Swords}
              tone={data.mobilisation_pct >= PERCENT ? 'success' : 'warning'}
              change={
                data.mobilisation_pct === PERCENT
                  ? undefined
                  : data.mobilisation_pct - PERCENT
              }
              hint='Fighting strength against an ordinary people'
            />
            <KpiTile
              label='Bound'
              value={formatInteger(bound)}
              icon={Link}
              tone={bound > 0 ? 'warning' : 'muted'}
              hint={`${((bound / Math.max(1, total)) * PERCENT).toFixed(1)}% serfs, slaves or captives`}
              meter={{ value: bound, max: total, label: 'In bondage' }}
            />
          </div>
          <Panel
            title='Age and sex'
            icon={Users}
            hint='Each bar is split by class; hover a band to count it.'
          >
            <Pyramid cohorts={cohorts} />
            <div className='grid min-w-0 grid-cols-2 gap-2 @xl/demo:grid-cols-4'>
              {CONDITIONS.map((condition) => {
                const spec = CONDITION_SPEC[condition]
                const count = sum(
                  cohorts.filter((cohort) => cohort.condition === condition),
                  (cohort) => cohort.count
                )
                return (
                  <MiniStat
                    key={condition}
                    icon={spec.icon}
                    label={spec.label}
                    value={formatInteger(count)}
                    tone={count > 0 ? spec.tone : 'muted'}
                    hint={spec.hint}
                  />
                )
              })}
            </div>
          </Panel>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/demo:grid-cols-2'>
            {data.classes.length > 0 && (
              <Panel
                title='How each class fares'
                icon={Gauge}
                hint='Share of the people and how content they are'
              >
                <div className='flex min-w-0 flex-col gap-3'>
                  {data.classes
                    .filter((item) => item.share > 0)
                    .map((item) => (
                      <ClassRow key={item.social_class} item={item} />
                    ))}
                </div>
              </Panel>
            )}
            {data.pressures.length > 0 && (
              <Panel
                title='Pressures'
                icon={TriangleAlert}
                tone={
                  worst && worst.value > 0 ? badTone(worst.value) : 'success'
                }
                hint={
                  worst && worst.value > 0
                    ? `${named(PRESSURE_ICONS, worst.kind).label} weighs heaviest`
                    : 'Nothing presses on them'
                }
              >
                <div className='flex min-w-0 flex-col gap-3'>
                  <Paged items={data.pressures}>
                    {(item) => {
                      const spec = named(PRESSURE_ICONS, item.kind)
                      return (
                        <Tooltip key={item.kind}>
                          <TooltipTrigger asChild>
                            <div tabIndex={0} className='min-w-0'>
                              <StatBar
                                label={spec.label}
                                icon={spec.icon}
                                value={item.value}
                                max={PERCENT}
                                tone={METER_TONE[badTone(item.value)]}
                              />
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            {PRESSURE_HINT[item.kind] ?? spec.label}
                          </TooltipContent>
                        </Tooltip>
                      )
                    }}
                  </Paged>
                </div>
              </Panel>
            )}
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 @xl/demo:grid-cols-2'>
            <SickCohorts view={data} blocked={blocked} />
            <DormancyPanel view={data} blocked={blocked} />
          </div>
          <AdjustPanel
            title='Shape the people'
            note='Move people between classes and conditions, heal the sick, set any cohort to an exact headcount, or forge a sickness to loose on them. Every change goes into the ledger and can be undone.'
          >
            <MoveCohort view={data} blocked={blocked} />
            <SetCohort view={data} blocked={blocked} />
            <ForgeDisease
              anchorId={data.entity_id}
              targetId={data.entity_id}
              blocked={blocked}
            />
          </AdjustPanel>
        </div>
      )}
    </Section>
  )
}

function SankeyLabel({
  x,
  y,
  icon: Icon,
  text,
  align,
  color,
}: {
  x: number
  y: number
  icon: LucideIcon
  text: string
  align: 'start' | 'end'
  color: string
}) {
  const iconX = align === 'end' ? x - SANKEY_ICON : x
  const textX = align === 'end' ? x - SANKEY_ICON - 4 : x + SANKEY_ICON + 4
  return (
    <g>
      <Icon
        x={iconX}
        y={y - SANKEY_ICON / 2}
        width={SANKEY_ICON}
        height={SANKEY_ICON}
        color={color}
        aria-hidden='true'
      />
      <text
        x={textX}
        y={y}
        textAnchor={align}
        dominantBaseline='middle'
        fontSize={LABEL_SIZE}
        className='fill-foreground'
      >
        {text}
      </text>
    </g>
  )
}

function Sankey({ flows, output }: { flows: Flow[]; output: Labour[] }) {
  const [ref, measured] = useWidth()
  const width = Math.max(SANKEY_MIN, measured)
  const classes = CLASS_ORDER.filter((item) =>
    flows.some((flow) => flow.social_class === item)
  )
  const jobs = JOB_ORDER.filter((item) =>
    flows.some((flow) => flow.job === item)
  )
  const total = Math.max(
    1,
    sum(flows, (flow) => flow.workers)
  )
  const pct = Object.fromEntries(output.map((row) => [row.job, row.output_pct]))
  const jobText = (job: Job) =>
    job === 'idle'
      ? JOB_SPEC[job].label
      : `${JOB_SPEC[job].label} ${pct[job] ?? PERCENT}%`
  const reserve = (texts: string[]) =>
    Math.min(
      Math.round(width * SANKEY_SHARE),
      Math.max(0, ...texts.map((text) => text.length)) * PYRAMID_CHAR +
        SANKEY_ICON +
        SANKEY_NODE +
        SANKEY_PAD
    )
  const left = reserve(classes.map((item) => CLASS_SPEC[item].label))
  const right = width - reserve(jobs.map(jobText))
  const rows = Math.max(classes.length, jobs.length)
  const usable = rows * SANKEY_ROW
  const thickness = (value: number) => (value / total) * usable
  const need = (keys: string[], weight: (key: string) => number) =>
    sum(keys, (key) => Math.max(SANKEY_MIN_NODE, thickness(weight(key)))) +
    SANKEY_GAP * Math.max(0, keys.length - 1)
  const classWeight = (key: string) =>
    sum(
      flows.filter((flow) => flow.social_class === key),
      (flow) => flow.workers
    )
  const jobWeight = (key: string) =>
    sum(
      flows.filter((flow) => flow.job === key),
      (flow) => flow.workers
    )
  const height = Math.max(
    rows * (SANKEY_ROW + SANKEY_GAP),
    need(classes, classWeight),
    need(jobs, jobWeight)
  )
  const layout = (keys: string[], weight: (key: string) => number) => {
    let cursor = (height - need(keys, weight)) / 2
    return Object.fromEntries(
      keys.map((key) => {
        const band = thickness(weight(key))
        const size = Math.max(SANKEY_MIN_NODE, band)
        const placed = { top: cursor, size, pad: (size - band) / 2 }
        cursor += size + SANKEY_GAP
        return [key, placed]
      })
    )
  }
  const from = layout(classes, classWeight)
  const to = layout(jobs, jobWeight)
  const leftUsed: Record<string, number> = {}
  const rightUsed: Record<string, number> = {}
  const mid = (left + right) / 2
  return (
    <div ref={ref} className='min-w-0'>
      <svg
        data-surface='LabourSankey'
        viewBox={`0 0 ${width} ${height}`}
        width='100%'
        className='block min-w-0'
        role='img'
        aria-label='Workers of each class flowing into each kind of work'
      >
        {flows.map((flow) => {
          const thick = Math.max(1, thickness(flow.workers))
          const start = from[flow.social_class]
          const end = to[flow.job]
          const y1 =
            start.top +
            start.pad +
            (leftUsed[flow.social_class] ?? 0) +
            thick / 2
          const y2 = end.top + end.pad + (rightUsed[flow.job] ?? 0) + thick / 2
          leftUsed[flow.social_class] =
            (leftUsed[flow.social_class] ?? 0) + thick
          rightUsed[flow.job] = (rightUsed[flow.job] ?? 0) + thick
          return (
            <path
              key={`${flow.social_class}-${flow.job}`}
              d={`M${left},${y1} C${mid},${y1} ${mid},${y2} ${right},${y2}`}
              fill='none'
              stroke={classColor(flow.social_class)}
              strokeOpacity={0.4}
              strokeWidth={thick}
            >
              <title>{`${CLASS_SPEC[flow.social_class].label} → ${JOB_SPEC[flow.job].label}: ${formatInteger(flow.workers)}`}</title>
            </path>
          )
        })}
        {classes.map((item) => (
          <g key={item}>
            <rect
              x={left - SANKEY_NODE}
              y={from[item].top}
              width={SANKEY_NODE}
              height={from[item].size}
              fill={classColor(item)}
              rx={3}
            />
            <SankeyLabel
              x={left - SANKEY_NODE - 6}
              y={from[item].top + from[item].size / 2}
              icon={CLASS_SPEC[item].icon}
              text={CLASS_SPEC[item].label}
              align='end'
              color={classColor(item)}
            />
          </g>
        ))}
        <Paged items={jobs}>
          {(item) => {
            const tone =
              item === 'idle' ? 'muted' : outputTone(pct[item] ?? PERCENT)
            return (
              <g key={item}>
                <rect
                  x={right}
                  y={to[item].top}
                  width={SANKEY_NODE}
                  height={to[item].size}
                  fill={TONE_COLOR[tone]}
                  rx={3}
                />
                <SankeyLabel
                  x={right + SANKEY_NODE + 6}
                  y={to[item].top + to[item].size / 2}
                  icon={JOB_SPEC[item].icon}
                  text={jobText(item)}
                  align='start'
                  color={TONE_COLOR[tone]}
                />
              </g>
            )
          }}
        </Paged>
      </svg>
    </div>
  )
}

function JobTile({ row }: { row: Labour }) {
  const spec = JOB_SPEC[row.job]
  const tone = row.job === 'idle' ? 'muted' : outputTone(row.output_pct)
  return (
    <div className='flex h-full min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-2.5'>
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={spec.icon} tone={tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' weight='medium' truncate>
            {spec.label}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {`${formatInteger(row.workers)} workers`}
          </Muted>
        </div>
        <Stat value={`${row.output_pct}%`} />
      </div>
      <Progress
        value={Math.min(PERCENT, (row.output_pct / OUTPUT_MAX) * PERCENT)}
        size='sm'
        tone={METER_TONE[tone]}
        aria-label={`${spec.label} output`}
      />
    </div>
  )
}

export function LabourSection({ communityId }: { communityId: number }) {
  const view = useDemography(communityId)
  if (!view.data || view.data.labour.length === 0) return null
  const working = view.data.labour.filter(
    (row) => row.workers > 0 && row.job !== 'idle'
  )
  const ranked = [...working].sort(
    (left, right) => right.output_pct - left.output_pct
  )
  const best = ranked[0]
  const weakest = ranked[ranked.length - 1]
  const idle = sum(
    view.data.flows.filter((flow) => flow.job === 'idle'),
    (flow) => flow.workers
  )
  const workers = sum(working, (row) => row.workers)
  return (
    <Section
      id='section-labour'
      title='Work'
      description='Which classes do which work, and how well: output against an ordinary worker, after satisfaction, bondage and seasonal sickness.'
      icon={Network}
    >
      <div className='@container/work flex min-w-0 flex-col gap-4'>
        <div className='grid min-w-0 grid-cols-2 gap-3 @xl/work:grid-cols-4'>
          <KpiTile
            label='At work'
            value={formatInteger(workers)}
            icon={Hammer}
            tone='gold'
            hint={`Across ${working.length} trades`}
          />
          <KpiTile
            label='Idle hands'
            value={formatInteger(idle)}
            icon={Hourglass}
            tone={idle > 0 ? 'warning' : 'muted'}
            hint='Nobles, outcasts and others who do no work'
          />
          {best && (
            <KpiTile
              label='Best trade'
              value={`${best.output_pct}%`}
              icon={JOB_SPEC[best.job].icon}
              tone={outputTone(best.output_pct)}
              hint={JOB_SPEC[best.job].label}
            />
          )}
          {weakest && (
            <KpiTile
              label='Worst trade'
              value={`${weakest.output_pct}%`}
              icon={JOB_SPEC[weakest.job].icon}
              tone={outputTone(weakest.output_pct)}
              hint={JOB_SPEC[weakest.job].label}
            />
          )}
        </div>
        <Panel
          title='Who does what'
          icon={Network}
          hint='Bands run from each class into its work; the percent is output against an ordinary worker.'
        >
          <Sankey flows={view.data.flows} output={view.data.labour} />
        </Panel>
        <div className='grid min-w-0 grid-cols-2 gap-2 @3xl/work:grid-cols-3'>
          {view.data.labour
            .filter((row) => row.workers > 0)
            .map((row) => (
              <JobTile key={row.job} row={row} />
            ))}
        </div>
        <LabourDepth communityId={communityId} />
      </div>
    </Section>
  )
}

function LifeCourse({
  biology,
}: {
  biology: NonNullable<Demography['biology']>
}) {
  const stages = [
    {
      key: 'child',
      label: 'Childhood',
      years: biology.maturity_years,
      spec: AGE_SPEC.child,
    },
    {
      key: 'adult',
      label: 'Adulthood',
      years: biology.adult_years,
      spec: AGE_SPEC.adult,
    },
    {
      key: 'elder',
      label: 'Old age',
      years: biology.elder_years,
      spec: AGE_SPEC.elder,
    },
  ]
  const span = Math.max(
    1,
    sum(stages, (stage) => stage.years)
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <svg
        viewBox={`0 0 ${PERCENT} 4`}
        preserveAspectRatio='none'
        className='h-meter-md w-full min-w-0'
        role='img'
        aria-label={`Childhood ${biology.maturity_years} years, adulthood ${biology.adult_years}, old age ${biology.elder_years}`}
      >
        {stages.map((stage, index) => {
          const before = sum(stages.slice(0, index), (item) => item.years)
          return (
            <rect
              key={stage.key}
              x={(before / span) * PERCENT}
              y={0}
              width={Math.max(0, (stage.years / span) * PERCENT - 0.6)}
              height={4}
              fill={TONE_COLOR[stage.spec.tone ?? 'muted']}
            />
          )
        })}
      </svg>
      <div className='grid min-w-0 grid-cols-1 gap-2 @md/folk:grid-cols-3'>
        {stages.map((stage) => (
          <MiniStat
            key={stage.key}
            icon={stage.spec.icon}
            label={stage.label}
            value={`${formatInteger(stage.years)} years`}
            tone={stage.spec.tone}
          />
        ))}
      </div>
    </div>
  )
}

export function PeopleProfileSection({
  peopleId,
  readOnlyReason,
}: {
  peopleId: number
  readOnlyReason?: string | null
}) {
  const view = useDemography(peopleId)
  const { reason } = useGodGate()
  const [neighbour, setNeighbour] = useState<string>('all')
  const axes = useMemo(() => {
    if (!view.data) return []
    const chosen =
      neighbour === 'all'
        ? view.data.neighbours
        : view.data.neighbours.filter(
            (item) => String(item.entity_id) === neighbour
          )
    return view.data.values.map((point) => {
      const others = chosen.flatMap((item) =>
        item.values
          .filter((value) => value.axis === point.axis)
          .map((value) => value.value)
      )
      return {
        key: point.axis,
        label: named(VALUE_ICONS, point.axis).label,
        value: point.value,
        reference:
          others.length > 0
            ? others.reduce((total, value) => total + value, 0) / others.length
            : null,
      }
    })
  }, [view.data, neighbour])
  if (!view.data || (!view.data.biology && !view.data.culture)) return null
  const blocked = readOnlyReason ?? reason()
  const { biology, culture } = view.data
  const neighbours = {
    all: 'All neighbours',
    ...Object.fromEntries(
      view.data.neighbours.map((item) => [String(item.entity_id), item.name])
    ),
  }
  const strongest = [...view.data.values]
    .sort((left, right) => Math.abs(right.value) - Math.abs(left.value))
    .slice(0, 3)
  const band = biology ? named(BAND, biology.acclimatised) : null
  const staple = biology
    ? (COMMODITY[biology.staple as CommodityKind] ?? null)
    : null
  return (
    <Section
      id='section-people-profile'
      title='Folk and customs'
      description='How this people lives, ages, marries, inherits, fights and sees beauty; its values against its neighbours.'
      icon={Fingerprint}
    >
      <div
        data-surface='PeopleProfile'
        className='@container/folk flex min-w-0 flex-col gap-4'
      >
        <div className='grid min-w-0 grid-cols-2 gap-3 @xl/folk:grid-cols-3'>
          {biology && (
            <KpiTile
              label='Lifespan'
              value={`${formatInteger(biology.maturity_years + biology.adult_years + biology.elder_years)} years`}
              icon={Hourglass}
              tone='gold'
              hint={`Of age at ${biology.maturity_years}, old at ${biology.maturity_years + biology.adult_years}`}
            />
          )}
          {biology && (
            <KpiTile
              label='Fertility'
              value={`${biology.fertility_pct}%`}
              icon={Sprout}
              tone={biology.fertility_pct >= PERCENT ? 'success' : 'warning'}
              change={
                biology.fertility_pct === PERCENT
                  ? undefined
                  : biology.fertility_pct - PERCENT
              }
              hint='Births against an ordinary people'
            />
          )}
          {biology && (
            <KpiTile
              label='Lives on'
              value={staple?.label ?? fieldLabel(biology.staple)}
              icon={staple?.icon ?? Sprout}
              tone='success'
              hint={`Born to ${band?.label.toLowerCase() ?? 'any'} lands`}
            />
          )}
          {culture && (
            <KpiTile
              label='Cohesion'
              value={culture.cohesion}
              icon={Users2}
              tone={goodTone(culture.cohesion)}
              hint='How firmly they hold together'
              meter={{
                value: culture.cohesion,
                max: PERCENT,
                label: 'Cohesion',
              }}
            />
          )}
          {culture && (
            <KpiTile
              label='Literacy'
              value={culture.literacy}
              icon={BookOpen}
              tone='info'
              hint='How many read and write'
              meter={{
                value: culture.literacy,
                max: PERCENT,
                label: 'Literacy',
              }}
            />
          )}
          {culture && (
            <KpiTile
              label='Urbanisation'
              value={culture.urbanisation}
              icon={Building}
              tone='verdigris'
              hint='How many live in towns'
              meter={{
                value: culture.urbanisation,
                max: PERCENT,
                label: 'Urbanisation',
              }}
            />
          )}
        </div>
        <div className='flex min-w-0 flex-col gap-3'>
          {biology && (
            <Panel
              title='A life'
              icon={Hourglass}
              hint='How the years of one of them are spent'
              aside={
                band && (
                  <Badge size='sm' variant='secondary'>
                    <band.icon />
                    {band.label}
                  </Badge>
                )
              }
            >
              <LifeCourse biology={biology} />
            </Panel>
          )}
          {biology && <FolkBody biology={biology} />}
          {culture && <FolkWays culture={culture} />}
          {culture && (
            <Panel
              title='Customs'
              icon={Palette}
              hint='Their ways at home and war'
            >
              <div className='grid min-w-0 grid-cols-1 gap-2 @md/folk:grid-cols-2 @xl/folk:grid-cols-3'>
                {[
                  { label: 'Art', spec: AESTHETIC_SPEC[culture.aesthetic] },
                  {
                    label: 'Way of war',
                    spec: MARTIAL_SPEC[culture.martial_style],
                  },
                  { label: 'Marriage', spec: MARRIAGE_SPEC[culture.marriage] },
                  {
                    label: 'Inheritance',
                    spec: INHERITANCE_SPEC[culture.inheritance],
                  },
                  {
                    label: 'Spouses',
                    spec: culture.endogamous
                      ? {
                          label: 'Only their own',
                          icon: Fingerprint,
                          tone: 'verdigris' as const,
                        }
                      : {
                          label: 'From any people',
                          icon: Users2,
                          tone: 'muted' as const,
                        },
                  },
                  {
                    label: 'Slavery',
                    spec: culture.slavery_lawful
                      ? {
                          label: 'Lawful',
                          icon: Link,
                          tone: 'warning' as const,
                        }
                      : {
                          label: 'Forbidden',
                          icon: Ban,
                          tone: 'success' as const,
                        },
                  },
                ].map((item) => (
                  <MiniStat
                    key={item.label}
                    icon={item.spec.icon}
                    label={item.label}
                    value={item.spec.label}
                    tone={item.spec.tone}
                  />
                ))}
              </div>
            </Panel>
          )}
        </div>
        {axes.length >= 3 && (
          <Panel
            title='Values'
            icon={Scale}
            hint={
              view.data.neighbours.length > 0
                ? 'Gold is this people; grey is the neighbours you compare with.'
                : 'What this people holds dear and what it scorns.'
            }
          >
            <div className='grid min-w-0 grid-cols-1 items-center gap-4 @xl/folk:grid-cols-3'>
              <div className='min-w-0 @xl/folk:col-span-2'>
                <ValueRadar
                  axes={axes}
                  label='Values'
                  referenceLabel={
                    view.data.neighbours.length > 0 ? 'Neighbours' : null
                  }
                />
              </div>
              <div className='flex min-w-0 flex-col gap-3'>
                {view.data.neighbours.length > 0 && (
                  <MindPicker
                    label='Compared with'
                    value={neighbour}
                    table={neighbours}
                    blocked={null}
                    onPick={setNeighbour}
                  />
                )}
                <Label variant='overline'>Held most strongly</Label>
                <Paged items={strongest}>
                  {(point) => {
                    const spec = named(VALUE_ICONS, point.axis)
                    return (
                      <MiniStat
                        key={point.axis}
                        icon={spec.icon}
                        label={spec.label}
                        value={
                          point.value > 0 ? `+${point.value}` : point.value
                        }
                        tone={
                          point.value >= 0 ? (spec.tone ?? 'gold') : 'danger'
                        }
                      />
                    )
                  }}
                </Paged>
              </div>
            </div>
          </Panel>
        )}
        <FolkControls view={view.data} blocked={blocked} />
        <FoundPeoplePanel view={view.data} blocked={blocked} />
      </div>
    </Section>
  )
}
