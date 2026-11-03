import { CalendarRange } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { type ChronicleLine } from '@/features/entity/api/types'

type YearStripProps = {
  lines: ChronicleLine[]
  selected: number | null
  onSelect: (year: number | null) => void
}

export function yearCounts(lines: ChronicleLine[]): Map<number, number> {
  const counts = new Map<number, number>()
  for (const line of lines) {
    if (line.year === null || line.year === undefined) continue
    counts.set(line.year, (counts.get(line.year) ?? 0) + 1)
  }
  return new Map([...counts].sort((left, right) => left[0] - right[0]))
}

export function YearStrip({ lines, selected, onSelect }: YearStripProps) {
  const counts = yearCounts(lines)
  if (counts.size < 2) return null
  return (
    <nav
      data-surface='YearStrip'
      aria-label='Years of the epoch'
      className='flex min-w-0 flex-col gap-1'
    >
      <Muted variant='caption'>
        <CalendarRange className='inline size-icon-xs' aria-hidden='true' />{' '}
        Pick a year to read only what happened in it.
      </Muted>
      <div className='flex min-w-0 flex-wrap items-center gap-1'>
        <Button
          size='sm'
          variant={selected === null ? 'default' : 'outline'}
          aria-pressed={selected === null}
          onClick={() => onSelect(null)}
        >
          Every year
        </Button>
        {[...counts].map(([year, count]) => (
          <Button
            key={year}
            size='sm'
            variant={selected === year ? 'default' : 'outline'}
            aria-pressed={selected === year}
            aria-label={`Year ${year}, ${count} ${count === 1 ? 'record' : 'records'}`}
            onClick={() => onSelect(selected === year ? null : year)}
          >
            {`${year} · ${count}`}
          </Button>
        ))}
      </div>
    </nav>
  )
}
