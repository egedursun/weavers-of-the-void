import { Lightbulb } from 'lucide-react'
import { Text } from '@/components/typography'
import { type Opportunity } from './opportunities'

export function OpportunityList({
  items,
  quietWhenServerLines = false,
}: {
  items: Opportunity[]
  quietWhenServerLines?: boolean
}) {
  if (items.length === 0 && quietWhenServerLines) return null
  if (items.length === 0)
    return <Text tone='muted'>No notable tension in the world right now.</Text>
  return (
    <ul className='flex min-w-0 flex-col gap-2'>
      {items.map((item) => (
        <li key={item.key} className='flex min-w-0 items-start gap-2'>
          <Lightbulb
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-primary'
          />
          <Text>
            <Text as='strong' weight='semibold'>{`${item.title}: `}</Text>
            {item.body}
          </Text>
        </li>
      ))}
    </ul>
  )
}
