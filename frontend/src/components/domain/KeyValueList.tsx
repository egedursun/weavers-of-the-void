import { Fragment, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Label, Text } from '@/components/typography'

export type KeyValueItem = {
  key?: string
  label: string
  value: ReactNode
}

type KeyValueListProps = {
  items: KeyValueItem[]
  layout?: 'columns' | 'stacked'
}

export function KeyValueList({ items, layout = 'columns' }: KeyValueListProps) {
  return (
    <dl
      data-domain='key-value-list'
      className={cn(
        'grid min-w-0 gap-x-4',
        layout === 'columns'
          ? 'grid-cols-1 gap-y-1 sm:grid-cols-label-track sm:items-baseline sm:gap-y-3'
          : 'grid-cols-1 gap-y-1'
      )}
    >
      {items.map((item, index) => (
        <Fragment key={item.key ?? `${item.label}-${index}`}>
          <Label
            as='dt'
            truncate
            className={cn(
              index > 0 && (layout === 'columns' ? 'pt-2 sm:pt-0' : 'pt-2')
            )}
          >
            {item.label}
          </Label>
          <Text as='dd' className='min-w-0'>
            {item.value}
          </Text>
        </Fragment>
      ))}
    </dl>
  )
}
