import { navItem } from '@/config/navigation'
import { PageHeader } from '@/components/domain'
import { CouncilRulingsPanel } from '@/features/divine/CouncilRulingsPanel'
import { CouncilBlock } from './CouncilBlock'

const ITEM = navItem('council')

export function CouncilScreen() {
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <PageHeader
        title={ITEM.title}
        description={ITEM.description}
        icon={ITEM.icon}
      />
      <CouncilBlock showAll />
      <CouncilRulingsPanel />
    </div>
  )
}
