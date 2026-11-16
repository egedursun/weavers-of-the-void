import { LayoutGrid } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Medallion, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type GoalCategory } from './api'
import { CATEGORY_ICON, CATEGORY_TONE } from './goalIcons'

export type CategoryCount = {
  category: GoalCategory
  label: string
  done: number
  total: number
}

export function CategoryFilter({
  title,
  counts,
  value,
  onChange,
}: {
  title: string
  counts: CategoryCount[]
  value: GoalCategory | null
  onChange: (category: GoalCategory | null) => void
}) {
  const done = counts.reduce((sum, item) => sum + item.done, 0)
  const total = counts.reduce((sum, item) => sum + item.total, 0)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{title}</Label>
      <ul className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6'>
        <li className='min-w-0'>
          <Button
            variant='outline'
            size='tile'
            aria-pressed={value === null}
            onClick={() => onChange(null)}
            className={cn(value === null && 'border-primary/50 bg-primary/10')}
          >
            <Medallion icon={LayoutGrid} tone='gold' size='sm' />
            <span className='flex min-w-0 flex-1 flex-col'>
              <Text as='span' weight='semibold' truncate>
                Every field
              </Text>
              <Muted as='span' variant='caption'>{`${done}/${total}`}</Muted>
            </span>
          </Button>
        </li>
        <Paged items={counts.filter((item) => item.total > 0)} as='li'>
          {(item) => {
            const active = value === item.category
            return (
              <li key={item.category} className='min-w-0'>
                <Button
                  variant='outline'
                  size='tile'
                  aria-pressed={active}
                  onClick={() => onChange(item.category)}
                  className={cn(active && 'border-primary/50 bg-primary/10')}
                >
                  <Medallion
                    icon={CATEGORY_ICON[item.category]}
                    tone={
                      item.done > 0 ? CATEGORY_TONE[item.category] : 'muted'
                    }
                    size='sm'
                  />
                  <span className='flex min-w-0 flex-1 flex-col'>
                    <Text as='span' weight='semibold' truncate>
                      {item.label}
                    </Text>
                    <Muted
                      as='span'
                      variant='caption'
                    >{`${item.done}/${item.total}`}</Muted>
                  </span>
                </Button>
              </li>
            )
          }}
        </Paged>
      </ul>
    </div>
  )
}
