import { navItem } from '@/config/navigation'
import { PageHeader } from '@/components/domain'
import { CompareSons } from '@/features/pantheon/CompareSons'
import { GoalsBlock } from './GoalsBlock'

const ITEM = navItem('goals')

export function GoalsScreen() {
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
      />
      <GoalsBlock achievementsOpen />
      <CompareSons />
    </div>
  )
}
