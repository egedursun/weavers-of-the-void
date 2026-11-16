import { ChevronDown, ChevronUp, ChevronsDown } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { type ShowMoreState } from './useShowMore'

type ShowMoreProps<T> = {
  state: ShowMoreState<T>
  noun?: [string, string]
  onCollapse?: () => void
}

function counted(count: number, noun: [string, string]): string {
  return `${formatInteger(count)} ${count === 1 ? noun[0] : noun[1]}`
}

export function ShowMore<T>({
  state,
  noun = ['item', 'items'],
  onCollapse,
}: ShowMoreProps<T>) {
  if (state.total <= state.initial) return null
  const shown = state.total - state.hidden
  const next = Math.min(state.step, state.hidden)
  return (
    <div
      data-domain='show-more'
      className='flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-md px-3 py-1.5 sealed-well'
    >
      <Muted as='span' variant='caption'>
        {`Showing ${formatInteger(shown)} of ${counted(state.total, noun)}`}
      </Muted>
      <div className='flex shrink-0 flex-wrap items-center gap-1'>
        {state.hidden > 0 && (
          <Button variant='ghost' size='sm' onClick={state.more}>
            <ChevronDown />
            {`Show ${formatInteger(next)} more`}
          </Button>
        )}
        {state.hidden > next && (
          <Button variant='ghost' size='sm' onClick={state.all}>
            <ChevronsDown />
            {`Show all ${formatInteger(state.total)}`}
          </Button>
        )}
        {state.expanded && (
          <Button
            variant='ghost'
            size='sm'
            onClick={() => {
              state.less()
              onCollapse?.()
            }}
          >
            <ChevronUp />
            Show less
          </Button>
        )}
      </div>
    </div>
  )
}
