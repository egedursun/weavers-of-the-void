import {
  Fragment,
  type HTMLAttributes,
  type Key,
  type ReactNode,
  createElement,
} from 'react'
import { ShowMore } from './ShowMore'
import { useShowMore } from './useShowMore'

type PagedListProps<T> = {
  items: readonly T[]
  initial: number
  step?: number
  noun?: [string, string]
  as?: 'ul' | 'ol' | 'div' | 'nav'
  className?: string
  listProps?: HTMLAttributes<HTMLElement> & { 'data-surface'?: string }
  itemKey: (item: T, index: number) => Key
  children: (item: T, index: number) => ReactNode
}

export function PagedList<T>({
  items,
  initial,
  step,
  noun,
  as = 'ul',
  className,
  listProps,
  itemKey,
  children,
}: PagedListProps<T>) {
  const page = useShowMore(items, initial, step)
  return (
    <div data-domain='paged-list' className='flex min-w-0 flex-col gap-3'>
      {createElement(
        as,
        { ...listProps, className },
        page.visible.map((item, index) => (
          <Fragment key={itemKey(item, index)}>
            {children(item, index)}
          </Fragment>
        ))
      )}
      <ShowMore state={page} noun={noun} />
    </div>
  )
}
