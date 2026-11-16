import { useState } from 'react'
import { Wrench } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Paged, Section } from '@/components/domain'
import { Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { JobRunRow } from './JobRunRow'
import {
  type MaintenanceTaskId,
  type MaintenanceTaskInfo,
  useMaintenanceTasks,
  useRunMaintenanceTask,
} from './api'

const CONFIRMED_TASKS: ReadonlySet<MaintenanceTaskId> = new Set(['prune'])
const ALREADY_RUNNING = 'This task is already running.'

type TaskJobs = Partial<Record<MaintenanceTaskId, string>>
type TaskErrors = Partial<Record<MaintenanceTaskId, string>>

function TaskBadges({ task }: { task: MaintenanceTaskInfo }) {
  return (
    <>
      {task.running && (
        <Badge size='sm' variant='default'>
          Running
        </Badge>
      )}
      {task.ledgered && (
        <Badge size='sm' variant='outline'>
          Undoable
        </Badge>
      )}
      {task.needs_llm && (
        <Badge size='sm' variant='secondary'>
          Needs the model
        </Badge>
      )}
    </>
  )
}

export function MaintenanceTasksPanel() {
  const tasks = useMaintenanceTasks()
  const run = useRunMaintenanceTask()
  const { reason } = useGodGate()
  const [jobs, setJobs] = useState<TaskJobs>({})
  const [errors, setErrors] = useState<TaskErrors>({})

  const start = (task: MaintenanceTaskInfo) => {
    setErrors((current) => ({ ...current, [task.task]: undefined }))
    run.mutate(task.task, {
      onSuccess: (accepted) =>
        setJobs((current) => ({ ...current, [task.task]: accepted.job_id })),
      onError: (error) =>
        setErrors((current) => ({ ...current, [task.task]: error.message })),
    })
  }

  const blockedFor = (task: MaintenanceTaskInfo): string | null =>
    reason({ llm: task.needs_llm, world: task.task !== 'completion' }) ??
    (task.running && !jobs[task.task] ? ALREADY_RUNNING : null)

  return (
    <Section
      title='Maintenance tasks'
      description='The world runs each of these by itself. Run one now for a fresh pass; undoable ones land in the ledger.'
      surface='card'
      level={3}
      icon={Wrench}
    >
      {tasks.isPending && <Skeleton className='h-textarea w-full' />}
      {tasks.isError && <Text tone='destructive'>{tasks.error.message}</Text>}
      {tasks.data && tasks.data.length === 0 && (
        <EmptyState
          size='compact'
          icon={Wrench}
          title='No maintenance tasks'
          description='The server offers no task to run by hand.'
        />
      )}
      {tasks.data && tasks.data.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={tasks.data} as='li' noun={['task', 'tasks']}>
            {(task) => (
              <JobRunRow
                key={task.task}
                id={task.task}
                title={task.title}
                description={task.description}
                note={`Runs by itself: ${task.automatic.toLowerCase()}.`}
                badges={<TaskBadges task={task} />}
                label='Run now'
                icon={Wrench}
                blocked={blockedFor(task)}
                pending={run.isPending && run.variables === task.task}
                error={errors[task.task] ?? null}
                jobId={jobs[task.task] ?? null}
                confirm={
                  CONFIRMED_TASKS.has(task.task)
                    ? {
                        title: `${task.title}?`,
                        description: `${task.description} This cannot be undone.`,
                        confirmLabel: 'Run now',
                      }
                    : undefined
                }
                onRun={() => start(task)}
                onDismiss={() =>
                  setJobs((current) => ({ ...current, [task.task]: undefined }))
                }
              />
            )}
          </Paged>
        </ul>
      )}
    </Section>
  )
}
