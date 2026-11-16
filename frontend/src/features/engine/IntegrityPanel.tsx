import { useState } from 'react'
import { Database, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ConfirmDialog, Medallion, Paged, Section } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { type IntegrityTask, useIntegrityTasks, useRunIntegrity } from './api'

type IntegrityPanelProps = {
  readOnlyReason: string | null
}

export function IntegrityPanel({ readOnlyReason }: IntegrityPanelProps) {
  const tasks = useIntegrityTasks()
  const run = useRunIntegrity()
  const [pending, setPending] = useState<IntegrityTask | null>(null)
  const execute = (task: IntegrityTask) => {
    run.mutate(task.task, {
      onSuccess: (result) => toast.success(result.message),
      onError: (error) => toast.error(error.message),
      onSettled: () => setPending(null),
    })
  }
  return (
    <Section
      title='Integrity'
      description='These run by themselves at startup and after every death. Run them here whenever you want a fresh pass.'
      surface='card'
      level={3}
      icon={ShieldCheck}
      tone='info'
    >
      {tasks.isPending && <Skeleton className='h-control-lg w-full' />}
      {tasks.isError && <Text tone='destructive'>{tasks.error.message}</Text>}
      {tasks.data && (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={tasks.data.tasks} as='li'>
            {(task) => (
              <li
                key={task.task}
                data-integrity={task.task}
                className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
              >
                <Medallion
                  icon={task.changes_world ? ShieldCheck : Database}
                  tone={task.changes_world ? 'warning' : 'info'}
                  size='sm'
                />
                <div className='flex min-w-0 flex-1 basis-60 flex-col gap-0.5'>
                  <Text weight='medium'>{task.title}</Text>
                  <Muted variant='caption'>{task.description}</Muted>
                </div>
                <Button
                  variant='outline'
                  size='sm'
                  disabled={run.isPending || readOnlyReason !== null}
                  disabledReason={readOnlyReason ?? 'Working'}
                  onClick={() =>
                    task.changes_world ? setPending(task) : execute(task)
                  }
                >
                  {task.changes_world ? <ShieldCheck /> : <Database />}
                  Run now
                </Button>
              </li>
            )}
          </Paged>
        </ul>
      )}
      <ConfirmDialog
        open={pending !== null}
        onOpenChange={(open) => !open && setPending(null)}
        title={pending ? `Run ${pending.title.toLowerCase()}?` : ''}
        desc={pending?.description ?? ''}
        confirmText='Run now'
        isLoading={run.isPending}
        handleConfirm={() => pending && execute(pending)}
      />
    </Section>
  )
}
