import { ChevronDown } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'

export function ServerShowMore({
  shown,
  total,
  more,
  loading,
  onMore,
}: {
  shown: number
  total: number
  more: boolean
  loading: boolean
  onMore: () => void
}) {
  if (total <= shown && !more) return null
  return (
    <div className='flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-md px-3 py-1.5 sealed-well'>
      <Muted as='span' variant='caption' role='status'>
        {`Showing ${formatInteger(shown)} of ${formatInteger(total)}`}
      </Muted>
      {more && (
        <Button
          type='button'
          variant='ghost'
          size='sm'
          disabled={loading}
          disabledReason='More is loading.'
          onClick={onMore}
        >
          <ChevronDown />
          Show more
        </Button>
      )}
    </div>
  )
}
