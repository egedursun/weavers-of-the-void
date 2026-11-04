import { type ReactNode } from 'react'
import { ShowMore } from './ShowMore'
import { useShowMore } from './useShowMore'

export const LIST_SHOWN = 8

type PagedProps<T> = {
  items: readonly T[]
  initial?: number
  step?: number
  noun?: [string, string]
  as?: 'div' | 'li'
  children: (item: T, index: number) => ReactNode
}

export function Paged<T>({
  items,
  initial = LIST_SHOWN,
  step,
  noun,
  as = 'div',
  children,
}: PagedProps<T>) {
  const page = useShowMore(items, initial, step)
  const Wrapper = as
  return (
    <>
      {page.visible.map((item, index) => children(item, index))}
      {page.total > page.initial && (
        <Wrapper
          data-domain='paged'
          className='col-span-full w-full basis-full list-none'
        >
          <ShowMore state={page} noun={noun} />
        </Wrapper>
      )}
    </>
  )
}
