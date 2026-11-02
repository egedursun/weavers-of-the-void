import { Waypoints } from 'lucide-react'
import { Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { NetworkHealthPanel } from '@/features/graph/NetworkHealthPanel'
import { MaintenanceTasksPanel } from './MaintenanceTasksPanel'
import { MissingContentPanel } from './MissingContentPanel'
import { WritingJobsPanel } from './WritingJobsPanel'

export function MaintenancePage() {
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <Muted>
        The housekeeping of the world. Everything here also runs by itself; run
        it by hand when you want it now. Backups are verified from the Data tab.
      </Muted>
      <MissingContentPanel />
      <WritingJobsPanel />
      <Section
        title='Knowledge network'
        description='Repair loose ends of the link graph, or let Fate propose, name and review links across the whole network.'
        surface='card'
        level={3}
        icon={Waypoints}
        tone='verdigris'
      >
        <NetworkHealthPanel intro />
      </Section>
      <MaintenanceTasksPanel />
    </div>
  )
}
