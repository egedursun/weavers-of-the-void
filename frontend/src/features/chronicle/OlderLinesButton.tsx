import { ChevronDown } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { type OlderLines } from './api'

export function OlderLinesButton({ older }: { older: OlderLines }) {
  if (older.remaining === 0) return null
  return (
    <div className='flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-md px-3 py-1.5 sealed-well'>
      <Muted as='span' variant='caption'>
        {older.failed
          ? 'The older entries could not be read. Try again.'
          : `${formatInteger(older.remaining)} older ${older.remaining === 1 ? 'entry is' : 'entries are'} kept in the chronicle`}
      </Muted>
      <Button
        variant='ghost'
        size='sm'
        onClick={older.loadOlder}
        disabled={older.loading}
        disabledReason='The older entries are being read.'
        aria-busy={older.loading}
      >
        <ChevronDown />
        {older.loading ? 'Reading older entries' : 'Load older entries'}
      </Button>
    </div>
  )
}
