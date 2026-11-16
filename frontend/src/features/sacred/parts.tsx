import { Badge } from '@/components/ui/badge'
import { PagedList } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { SPAN } from './model'

export type BarSegment = { value: number; fill: string }

export type BarRow = {
  key: string | number
  caption: string
  segments: BarSegment[]
  mark?: number
}

export type LegendItem = {
  text: string
  variant: 'success' | 'destructive' | 'outline' | 'secondary' | 'warning'
}

export function Bars({
  chart,
  title,
  legend,
  rows,
  max,
  noun,
  empty,
}: {
  chart: string
  title: string
  legend: LegendItem[]
  rows: BarRow[]
  max?: number
  noun: [string, string]
  empty: string
}) {
  const widest = Math.max(
    1,
    max ?? 0,
    ...rows.map((row) =>
      Math.max(
        row.segments.reduce((sum, item) => sum + item.value, 0),
        row.mark ?? 0
      )
    )
  )
  const width = (value: number) => (Math.max(0, value) * SPAN) / widest
  return (
    <div
      data-chart={chart}
      className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <Label variant='overline'>{title}</Label>
      <PagedList
        items={legend}
        initial={4}
        noun={['key', 'keys']}
        as='div'
        className='flex min-w-0 flex-wrap items-center gap-1.5'
        itemKey={(item) => item.text}
      >
        {(item) => (
          <Badge key={item.text} size='sm' variant={item.variant}>
            {item.text}
          </Badge>
        )}
      </PagedList>
      {rows.length === 0 ? (
        <Muted variant='caption'>{empty}</Muted>
      ) : (
        <PagedList
          items={rows}
          initial={8}
          noun={noun}
          as='ul'
          className='flex min-w-0 flex-col gap-1.5'
          itemKey={(item) => item.key}
        >
          {(item) => {
            const starts = item.segments.map((_, index) =>
              item.segments
                .slice(0, index)
                .reduce((sum, part) => sum + width(part.value), 0)
            )
            return (
              <li key={item.key} className='flex min-w-0 flex-col gap-0.5'>
                <Muted as='span' variant='caption'>
                  {item.caption}
                </Muted>
                <svg
                  viewBox='0 0 100 6'
                  preserveAspectRatio='none'
                  className='h-icon-sm w-full'
                  role='img'
                  aria-label={item.caption}
                >
                  <rect
                    x='0'
                    y='1'
                    width='100'
                    height='4'
                    className='fill-muted'
                  />
                  {item.segments.map((part, index) => (
                    <rect
                      key={part.fill + String(index)}
                      x={starts[index]}
                      y='1'
                      width={width(part.value)}
                      height='4'
                      className={part.fill}
                    />
                  ))}
                  {item.mark !== undefined && (
                    <line
                      x1={width(item.mark)}
                      x2={width(item.mark)}
                      y1='0'
                      y2='6'
                      className='stroke-primary'
                      strokeWidth='0.8'
                    />
                  )}
                </svg>
              </li>
            )
          }}
        </PagedList>
      )}
    </div>
  )
}
