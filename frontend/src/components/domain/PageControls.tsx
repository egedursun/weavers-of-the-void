import { ChevronLeft, ChevronRight } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'

type PageControlsProps = {
  offset: number
  limit: number
  total: number
  onChange: (offset: number) => void
  label?: string
  busy?: boolean
}

function pageRange(offset: number, limit: number, total: number) {
  if (total === 0) return { first: 0, last: 0 }
  return { first: offset + 1, last: Math.min(total, offset + limit) }
}

export function PageControls({
  offset,
  limit,
  total,
  onChange,
  label = 'Pages',
  busy = false,
}: PageControlsProps) {
  if (total <= limit && offset === 0) return null
  const { first, last } = pageRange(offset, limit, total)
  const atStart = offset <= 0
  const atEnd = offset + limit >= total
  return (
    <nav
      aria-label={label}
      data-domain='page-controls'
      className='flex min-w-0 flex-wrap items-center justify-between gap-2'
    >
      <Muted variant='caption'>
        {`${formatInteger(first)}–${formatInteger(last)} of ${formatInteger(total)}`}
      </Muted>
      <div className='flex items-center gap-2'>
        <Button
          variant='outline'
          size='sm'
          disabled={atStart || busy}
          disabledReason={atStart ? 'This is the first page.' : 'Loading.'}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          <ChevronLeft />
          Previous
        </Button>
        <Button
          variant='outline'
          size='sm'
          disabled={atEnd || busy}
          disabledReason={atEnd ? 'This is the last page.' : 'Loading.'}
          onClick={() => onChange(offset + limit)}
        >
          Next
          <ChevronRight />
        </Button>
      </div>
    </nav>
  )
}
