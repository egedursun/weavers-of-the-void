import { Muted } from '@/components/typography'
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
      <MaintenanceTasksPanel />
    </div>
  )
}
