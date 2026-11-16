import {
  type PointerEvent,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react'
import { formatCompact, formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Label, Muted, SectionTitle, Stat } from '@/components/typography'
import {
  type ChartSeries,
  chartFrame,
  directLabelOffsets,
  nearestIndex,
  shortLabel,
  xDomain,
  xLabelIndices,
  xScale,
  yCeiling,
  gridFractions,
  yScale,
} from './lineChartModel'

export type { ChartPoint, ChartSeries } from './lineChartModel'

const FALLBACK_WIDTH = 280
const END_DOT_RADIUS = 4
const END_DOT_RING = 2
const LINE_WIDTH = 2.25
const GRID_DASH = '2 5'
const TICK_OFFSET = 6
const LABEL_BASELINE = 4
const DIRECT_LABEL_OFFSET = 8
const TOOLTIP_OFFSET = 12

type LineChartProps = {
  series: ChartSeries[]
  title?: string
  label?: string
  max?: number
  height?: number
  xLabel?: (x: number) => string
  tooltipLabel?: (x: number) => string
  format?: (value: number) => string
  axisFormat?: (value: number) => string
  className?: string
  bare?: boolean
}

function useWidth() {
  const ref = useRef<HTMLDivElement | null>(null)
  const [width, setWidth] = useState(FALLBACK_WIDTH)
  useEffect(() => {
    const element = ref.current
    if (!element) return
    const measure = () =>
      setWidth(Math.max(1, Math.round(element.clientWidth)) || FALLBACK_WIDTH)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return { ref, width }
}

function Swatch({ color }: { color: string }) {
  return (
    <svg aria-hidden='true' viewBox='0 0 8 8' className='size-icon-xs shrink-0'>
      <circle cx='4' cy='4' r='4' fill={color} />
    </svg>
  )
}

export function LineChart({
  series,
  title,
  label,
  max,
  height,
  xLabel = (x) => `E${x}`,
  tooltipLabel = (x) => `Epoch ${x}`,
  format = formatInteger,
  axisFormat = formatCompact,
  className,
  bare = false,
}: LineChartProps) {
  const { ref, width } = useWidth()
  const areaId = `area-${useId().replace(/:/g, '')}`
  const [hover, setHover] = useState<number | null>(null)
  const shown = useMemo(
    () => series.filter((item) => item.points.length > 0),
    [series]
  )
  const xs = useMemo(() => xDomain(shown), [shown])
  const frame = chartFrame(width, 1, height)
  const ceiling = yCeiling(shown, max)
  const toX = xScale(frame, xs)
  const toY = yScale(frame, ceiling)
  const labelIndices = xLabelIndices(xs, toX)
  const direct = false
  const ends = shown.map((item) => toY(item.points[item.points.length - 1].y))
  const labelYs = directLabelOffsets(ends)
  const single = shown.length === 1 ? shown[0] : null
  const lastValue = single ? single.points[single.points.length - 1].y : null
  const hoverX = hover === null ? null : xs[hover]
  const onMove = (event: PointerEvent<SVGRectElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(nearestIndex(xs, toX, event.clientX - box.left + frame.left))
  }
  const name = label ?? title ?? 'Chart'
  return (
    <figure
      data-domain='line-chart'
      className={cn('flex min-w-0 flex-col gap-2', className)}
    >
      {!bare && (title || lastValue !== null) && (
        <div className='flex min-w-0 items-baseline justify-between gap-2'>
          {title && (
            <SectionTitle level={4} truncate>
              {title}
            </SectionTitle>
          )}
          {lastValue !== null && <Stat value={format(lastValue)} />}
        </div>
      )}
      <div ref={ref} className='relative w-full min-w-0'>
        {xs.length === 0 ? (
          <Muted variant='caption'>No values yet.</Muted>
        ) : (
          <svg
            role='img'
            aria-label={name}
            width={frame.width}
            height={frame.height}
            className='block overflow-visible text-caption tabular-nums'
          >
            {gridFractions(frame.height - frame.top - frame.bottom).map(
              (fraction) => {
                const y = toY(ceiling * fraction)
                return (
                  <g key={fraction}>
                    <line
                      x1={frame.left}
                      x2={frame.width - frame.right}
                      y1={y}
                      y2={y}
                      strokeDasharray={fraction === 0 ? undefined : GRID_DASH}
                      className={
                        fraction === 0 ? 'stroke-gild/60' : 'stroke-gild/15'
                      }
                    />
                    <text
                      x={frame.left - TICK_OFFSET}
                      y={y + LABEL_BASELINE}
                      textAnchor='end'
                      className='fill-muted-foreground'
                    >
                      {axisFormat(ceiling * fraction)}
                    </text>
                  </g>
                )
              }
            )}
            {labelIndices.map((index) => (
              <line
                key={`grid-${xs[index]}`}
                data-chart-vgrid
                x1={toX(xs[index])}
                x2={toX(xs[index])}
                y1={frame.top}
                y2={frame.height - frame.bottom}
                strokeDasharray={GRID_DASH}
                className='stroke-gild/10'
              />
            ))}
            {single && (
              <defs>
                <linearGradient id={areaId} x1='0' y1='0' x2='0' y2='1'>
                  <stop
                    offset='0'
                    stopColor={single.color}
                    stopOpacity={0.42}
                  />
                  <stop offset='1' stopColor={single.color} stopOpacity={0} />
                </linearGradient>
              </defs>
            )}
            {single && (
              <polygon
                data-chart-area
                points={[
                  `${toX(single.points[0].x)},${toY(0)}`,
                  ...single.points.map(
                    (point) => `${toX(point.x)},${toY(point.y)}`
                  ),
                  `${toX(single.points[single.points.length - 1].x)},${toY(0)}`,
                ].join(' ')}
                fill={`url(#${areaId})`}
              />
            )}
            {labelIndices.map((index) => (
              <text
                key={xs[index]}
                x={toX(xs[index])}
                y={frame.height - LABEL_BASELINE}
                textAnchor={
                  index === xs.length - 1 && xs.length > 1 ? 'end' : 'middle'
                }
                className='fill-muted-foreground'
              >
                {xLabel(xs[index])}
              </text>
            ))}
            {hoverX !== null && hoverX !== undefined && (
              <line
                data-chart-guide
                x1={toX(hoverX)}
                x2={toX(hoverX)}
                y1={frame.top}
                y2={frame.height - frame.bottom}
                strokeDasharray={GRID_DASH}
                className='stroke-gild/70'
              />
            )}
            {shown.map((item) => (
              <polyline
                key={item.key}
                data-series={item.key}
                fill='none'
                stroke={item.color}
                strokeWidth={LINE_WIDTH}
                strokeLinejoin='round'
                strokeLinecap='round'
                className='chart-glow'
                points={item.points
                  .map((point) => `${toX(point.x)},${toY(point.y)}`)
                  .join(' ')}
              />
            ))}
            {shown.map((item) => {
              const last = item.points[item.points.length - 1]
              return (
                <circle
                  key={item.key}
                  cx={toX(last.x)}
                  cy={toY(last.y)}
                  r={END_DOT_RADIUS}
                  fill={item.color}
                  strokeWidth={END_DOT_RING}
                  className='chart-glow stroke-gild-hi'
                />
              )
            })}
            {direct &&
              shown.map((item, index) => (
                <text
                  key={item.key}
                  data-direct-label={item.key}
                  x={frame.width - frame.right + DIRECT_LABEL_OFFSET}
                  y={labelYs[index] + LABEL_BASELINE}
                  className='fill-foreground'
                >
                  {shortLabel(item.label)}
                </text>
              ))}
            <rect
              data-chart-hit
              x={frame.left}
              y={frame.top}
              width={Math.max(1, frame.width - frame.left - frame.right)}
              height={Math.max(1, frame.height - frame.top - frame.bottom)}
              fill='transparent'
              onPointerMove={onMove}
              onPointerLeave={() => setHover(null)}
            />
          </svg>
        )}
        {hoverX !== null && hoverX !== undefined && (
          <div
            role='tooltip'
            className={cn(
              'pointer-events-none absolute top-0 flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-gild/60 bg-card px-2 py-1 text-popover-foreground',
              toX(hoverX) > frame.width / 2 && '-translate-x-full'
            )}
            style={{
              left:
                toX(hoverX) > frame.width / 2
                  ? toX(hoverX) - TOOLTIP_OFFSET
                  : toX(hoverX) + TOOLTIP_OFFSET,
            }}
          >
            <Label>{tooltipLabel(hoverX)}</Label>
            {shown.map((item) => {
              const point = item.points.find((entry) => entry.x === hoverX)
              if (!point) return null
              return (
                <span
                  key={item.key}
                  className='flex items-center gap-2 whitespace-nowrap'
                >
                  <Swatch color={item.color} />
                  <Muted as='span' variant='caption'>
                    {item.label}
                  </Muted>
                  <Stat value={format(point.y)} />
                </span>
              )
            })}
          </div>
        )}
      </div>
      {shown.length > 1 && (
        <ul
          aria-label={`${name} legend`}
          className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1'
        >
          {shown.map((item) => (
            <li key={item.key} className='flex min-w-0 items-center gap-1'>
              <Swatch color={item.color} />
              <Label truncate>{item.label}</Label>
            </li>
          ))}
        </ul>
      )}
    </figure>
  )
}
