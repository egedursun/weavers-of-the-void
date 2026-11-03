import { useMemo } from 'react'
import {
  ChartLine,
  Flame,
  type LucideIcon,
  ScrollText,
  Skull,
  Swords,
  Users,
  Shield,
  Footprints,
} from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ChangeChip,
  EmptyState,
  type KpiTone,
  Medallion,
  Section,
} from '@/components/domain'
import { type ChartSeries, LineChart } from '@/components/domain/LineChart'
import { Stat, Text } from '@/components/typography'
import { type EpochStatistics, useEpochStatistics } from './api'
import { HARMFUL_STATS, type NumericStat, STAT_LABEL } from './statFields'

const MIN_POINTS = 2
const CHART_COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
]
type ChartSpec = {
  id: string
  title: string
  fields: NumericStat[]
  icon: LucideIcon
  tone: KpiTone
}

const CHARTS: ChartSpec[] = [
  {
    id: 'chart-population',
    title: 'Population',
    fields: ['population'],
    icon: Users,
    tone: 'gold',
  },
  {
    id: 'chart-followers',
    title: 'Followers',
    fields: ['followers'],
    icon: Flame,
    tone: 'warning',
  },
  {
    id: 'knowledge',
    title: 'Records and knowledge',
    fields: ['entities', 'knowledge', 'languages'],
    icon: ScrollText,
    tone: 'verdigris',
  },
  {
    id: 'conflict',
    title: 'War and bonds',
    fields: ['wars', 'alliances', 'trade_routes'],
    icon: Swords,
    tone: 'danger',
  },
  {
    id: 'doom',
    title: 'Doom clock',
    fields: ['doom'],
    icon: Skull,
    tone: 'danger',
  },
  {
    id: 'chart-soldiers',
    title: 'Soldiers under arms',
    fields: ['soldiers'],
    icon: Shield,
    tone: 'danger',
  },
  {
    id: 'chart-travelling',
    title: 'On the road between worlds',
    fields: ['travelling'],
    icon: Footprints,
    tone: 'info',
  },
]

type Point = { epoch: number } & Partial<Record<NumericStat, number>>

function toPoints(series: EpochStatistics[]): Point[] {
  return [...series]
    .sort((left, right) => left.epoch - right.epoch)
    .map((item) => {
      const point: Point = { epoch: item.epoch }
      for (const spec of CHARTS)
        for (const field of spec.fields) point[field] = item.data[field]
      return point
    })
}

function SmallChart({ spec, points }: { spec: ChartSpec; points: Point[] }) {
  const series: ChartSeries[] = spec.fields.map((field, index) => ({
    key: field,
    label: STAT_LABEL[field],
    color: CHART_COLORS[index],
    points: points.flatMap((point) => {
      const value = point[field]
      return value === undefined ? [] : [{ x: point.epoch, y: value }]
    }),
  }))
  const first = series[0]?.points ?? []
  const last = first.length > 0 ? first[first.length - 1].y : null
  const before = first.length > 1 ? first[first.length - 2].y : null
  return (
    <div
      data-chart-card={spec.id}
      className='flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2'>
        <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
        <Text as='span' weight='semibold' className='flex-1'>
          {spec.title}
        </Text>
        {spec.fields.length === 1 && last !== null && (
          <span className='flex shrink-0 items-center gap-2'>
            <Stat value={last} />
            {before !== null && (
              <ChangeChip
                value={last - before}
                harmful={HARMFUL_STATS.has(spec.fields[0])}
              />
            )}
          </span>
        )}
      </div>
      <LineChart label={spec.title} series={series} bare />
    </div>
  )
}

type StatsChartsProps = {
  hasWorld: boolean
}

export function StatsCharts({ hasWorld }: StatsChartsProps) {
  const stats = useEpochStatistics(hasWorld)
  const points = useMemo(() => toPoints(stats.data ?? []), [stats.data])
  return (
    <Section
      title='Traces of the epochs'
      description='How the world has grown, believed and fought, epoch by epoch.'
      surface='card'
    >
      {stats.isPending && hasWorld && <Skeleton className='h-48 w-full' />}
      {stats.isError && <Text tone='destructive'>{stats.error.message}</Text>}
      {(!hasWorld || (stats.data && points.length < MIN_POINTS)) && (
        <EmptyState
          size='compact'
          icon={ChartLine}
          title='Not enough epochs yet'
          description='The traces appear once two epochs have been measured.'
        />
      )}
      {points.length >= MIN_POINTS && (
        <div className='grid min-w-0 grid-cols-1 gap-4 lg:grid-cols-2'>
          {CHARTS.map((spec) => (
            <SmallChart key={spec.id} spec={spec} points={points} />
          ))}
        </div>
      )}
    </Section>
  )
}
