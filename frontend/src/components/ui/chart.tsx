import * as React from 'react'
import * as RechartsPrimitive from 'recharts'
import { cn } from '@/lib/utils'

const THEMES = { light: '', dark: '.dark' } as const

export type ChartConfig = {
  [key: string]: {
    label?: React.ReactNode
    icon?: React.ComponentType
  } & (
    | { color?: string; theme?: never }
    | { color?: never; theme: Record<keyof typeof THEMES, string> }
  )
}

type ChartContextProps = {
  config: ChartConfig
}

const ChartContext = React.createContext<ChartContextProps | null>(null)

function useChart() {
  const context = React.useContext(ChartContext)
  if (!context)
    throw new Error('useChart must be used within a <ChartContainer />')
  return context
}

function ChartContainer({
  id,
  className,
  children,
  config,
  ...props
}: React.ComponentProps<'div'> & {
  config: ChartConfig
  children: React.ComponentProps<
    typeof RechartsPrimitive.ResponsiveContainer
  >['children']
}) {
  const uniqueId = React.useId()
  const chartId = `chart-${id ?? uniqueId.replace(/:/g, '')}`
  return (
    <ChartContext.Provider value={{ config }}>
      <div
        data-slot='chart'
        data-chart={chartId}
        className={cn(
          "flex aspect-video min-w-0 justify-center text-caption [&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground [&_.recharts-cartesian-grid_line[stroke='#ccc']]:stroke-gild/15 [&_.recharts-curve.recharts-tooltip-cursor]:stroke-gild/60 [&_.recharts-dot[stroke='#fff']]:stroke-transparent [&_.recharts-layer]:outline-hidden [&_.recharts-polar-grid_[stroke='#ccc']]:stroke-gild/25 [&_.recharts-radial-bar-background-sector]:fill-muted [&_.recharts-rectangle.recharts-tooltip-cursor]:fill-muted [&_.recharts-reference-line_[stroke='#ccc']]:stroke-border [&_.recharts-sector]:outline-hidden [&_.recharts-sector[stroke='#fff']]:stroke-transparent [&_.recharts-surface]:outline-hidden",
          className
        )}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        <RechartsPrimitive.ResponsiveContainer>
          {children}
        </RechartsPrimitive.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  )
}

function ChartStyle({ id, config }: { id: string; config: ChartConfig }) {
  const colorConfig = Object.entries(config).filter(
    ([, item]) => item.theme ?? item.color
  )
  if (!colorConfig.length) return null
  return (
    <style
      dangerouslySetInnerHTML={{
        __html: Object.entries(THEMES)
          .map(
            ([theme, prefix]) => `
${prefix} [data-chart=${id}] {
${colorConfig
  .map(([key, itemConfig]) => {
    const color =
      itemConfig.theme?.[theme as keyof typeof itemConfig.theme] ??
      itemConfig.color
    return color ? `  --color-${key}: ${color};` : null
  })
  .filter(Boolean)
  .join('\n')}
}
`
          )
          .join('\n'),
      }}
    />
  )
}

const ChartTooltip = RechartsPrimitive.Tooltip

type ChartPayloadItem = {
  dataKey?: unknown
  name?: unknown
  value?: unknown
  color?: string
  payload?: unknown
}

type ChartTooltipContentProps = {
  active?: boolean
  payload?: ReadonlyArray<ChartPayloadItem>
  label?: React.ReactNode
  className?: string
  hideLabel?: boolean
  labelFormatter?: (label: React.ReactNode) => React.ReactNode
  valueFormatter?: (value: number) => React.ReactNode
}

function keyOf(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number'
    ? String(value)
    : ''
}

function ChartTooltipContent({
  active,
  payload,
  label,
  className,
  hideLabel = false,
  labelFormatter,
  valueFormatter,
}: ChartTooltipContentProps) {
  const { config } = useChart()
  if (!active || !payload?.length) return null
  return (
    <div
      data-slot='chart-tooltip'
      className={cn(
        'grid min-w-32 items-start gap-1.5 rounded-md surface-ornate px-2.5 py-1.5 text-caption',
        className
      )}
    >
      {!hideLabel && label !== undefined && (
        <div className='font-medium'>
          {labelFormatter ? labelFormatter(label) : label}
        </div>
      )}
      <div className='grid gap-1.5'>
        {payload.map((item) => {
          const key = keyOf(item.dataKey) || keyOf(item.name)
          const itemConfig = config[key]
          const value = typeof item.value === 'number' ? item.value : null
          return (
            <div key={key} className='flex w-full items-center gap-2'>
              <span
                className='size-2.5 shrink-0 rounded-sm bg-(--color-bg)'
                style={
                  {
                    '--color-bg': item.color ?? `var(--color-${key})`,
                  } as React.CSSProperties
                }
              />
              <span className='flex-1 text-muted-foreground'>
                {itemConfig?.label ?? key}
              </span>
              {value !== null && (
                <span className='font-medium text-foreground tabular-nums'>
                  {valueFormatter
                    ? valueFormatter(value)
                    : value.toLocaleString('en-US')}
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const ChartLegend = RechartsPrimitive.Legend

type ChartLegendContentProps = {
  payload?: ReadonlyArray<ChartPayloadItem>
  className?: string
}

function ChartLegendContent({ payload, className }: ChartLegendContentProps) {
  const { config } = useChart()
  if (!payload?.length) return null
  return (
    <div
      data-slot='chart-legend'
      className={cn(
        'flex flex-wrap items-center justify-center gap-4 pt-3',
        className
      )}
    >
      {payload.map((item) => {
        const key = keyOf(item.dataKey) || keyOf(item.value)
        const itemConfig = config[key]
        return (
          <div
            key={key}
            className='flex items-center gap-1.5 text-muted-foreground'
          >
            <span
              className='size-2 shrink-0 rounded-sm bg-(--color-bg)'
              style={
                {
                  '--color-bg': item.color ?? `var(--color-${key})`,
                } as React.CSSProperties
              }
            />
            {itemConfig?.label ?? key}
          </div>
        )
      })}
    </div>
  )
}

export {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  ChartStyle,
}
