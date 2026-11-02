import { useMemo } from 'react'
import { ChartLine } from 'lucide-react'
import { EmptyState, EntityLink, Section } from '@/components/domain'
import { type ChartSeries, LineChart } from '@/components/domain/LineChart'
import { SectionTitle } from '@/components/typography'
import { type SonPublic } from '@/features/entity/api/types'
import { type EpochStatistics } from './api'

const MIN_POINTS = 2
const EXISTENCE_MAX = 100
const COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
]

type Trace = {
  key: 'population' | 'followers' | 'words' | 'entities'
  title: string
}

const TRACES: Trace[] = [
  { key: 'population', title: 'Population' },
  { key: 'followers', title: 'Disciples' },
  { key: 'words', title: 'Words in the lexicons' },
  { key: 'entities', title: 'Records in canon' },
]

type Point = Record<string, number>

function TraceChart({
  title,
  points,
  series,
  max,
}: {
  title: string
  points: Point[]
  series: { key: string; label: string; color: string }[]
  max?: number
}) {
  const lines: ChartSeries[] = series.map((item) => ({
    ...item,
    points: points.flatMap((point) => {
      const value = point[item.key]
      return value === undefined ? [] : [{ x: point.epoch, y: value }]
    }),
  }))
  return <LineChart title={title} series={lines} max={max} />
}

export function EpochTraces({
  stats,
  sons,
}: {
  stats: EpochStatistics[]
  sons: SonPublic[]
}) {
  const sorted = useMemo(
    () => [...stats].sort((left, right) => left.epoch - right.epoch),
    [stats]
  )
  const points = useMemo(
    () =>
      sorted.map((item) => {
        const point: Point = { epoch: item.epoch }
        for (const trace of TRACES) point[trace.key] = item.data[trace.key]
        for (const [id, son] of Object.entries(item.data.sons ?? {})) {
          point[`faith_${id}`] = son.faith
          point[`existence_${id}`] = son.existence
        }
        return point
      }),
    [sorted]
  )
  const faithMax = Math.max(
    1,
    ...points.flatMap((point) =>
      Object.entries(point)
        .filter(([key]) => key.startsWith('faith_'))
        .map(([, value]) => value)
    )
  )
  const tracked = sons.filter((view) =>
    points.some((point) => point[`faith_${view.son.id}`] !== undefined)
  )
  return (
    <Section
      id='chronicle-traces'
      title='Traces of the epochs'
      description='How the world grew, one snapshot per closed epoch.'
      level={3}
    >
      {points.length < MIN_POINTS ? (
        <EmptyState
          size='compact'
          icon={ChartLine}
          title='Not enough epochs yet'
          description='The traces appear once two epochs have closed.'
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-6'>
          <div className='grid min-w-0 grid-cols-1 gap-6 md:grid-cols-2'>
            {TRACES.map((trace) => (
              <TraceChart
                key={trace.key}
                title={trace.title}
                points={points}
                series={[
                  { key: trace.key, label: trace.title, color: COLORS[0] },
                ]}
              />
            ))}
          </div>
          {tracked.length > 0 && (
            <div className='flex min-w-0 flex-col gap-4'>
              <SectionTitle level={3}>Sons through the epochs</SectionTitle>
              <div className='grid min-w-0 grid-cols-1 gap-6 md:grid-cols-2'>
                {tracked.map((view) => (
                  <div
                    key={view.son.id}
                    className='flex min-w-0 flex-col gap-2 rounded-lg border p-3'
                  >
                    <EntityLink
                      kind='son'
                      id={String(view.son.id)}
                      rarity={view.son.rarity}
                    >
                      {view.son.name}
                    </EntityLink>
                    <TraceChart
                      title='Faith'
                      points={points}
                      max={faithMax}
                      series={[
                        {
                          key: `faith_${view.son.id}`,
                          label: 'Faith',
                          color: COLORS[1],
                        },
                      ]}
                    />
                    <TraceChart
                      title='Existence'
                      points={points}
                      max={EXISTENCE_MAX}
                      series={[
                        {
                          key: `existence_${view.son.id}`,
                          label: 'Existence',
                          color: COLORS[2],
                        },
                      ]}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Section>
  )
}
