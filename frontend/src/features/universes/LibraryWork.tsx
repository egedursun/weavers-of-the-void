import {
  BookOpen,
  CircleStop,
  Download,
  PackageOpen,
  Trash2,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock, Paged } from '@/components/domain'
import { LibraryJobProgress } from './LibraryJobProgress'
import { exportFileUrl, jobSettled, useLibraryJobs, useStopJob } from './api'
import { type LibraryJob, type UniverseOrigin } from './types'
import { useEnterUniverse } from './useEnterUniverse'

const KIND_TITLE: Record<LibraryJob['kind'], string> = {
  export: 'Export',
  import: 'Import',
}

const IMPORTED: UniverseOrigin = 'imported'

function WorkRow({ job }: { job: LibraryJob }) {
  const stop = useStopJob()
  const { enter, opening } = useEnterUniverse()
  const settled = jobSettled(job)
  const halt = (message: string) =>
    stop.mutate(job, {
      onSuccess: () => toast.success(message),
      onError: (error) => toast.error(error.message),
    })
  return (
    <li className='flex min-w-0 flex-col gap-2'>
      <LibraryJobProgress
        job={job}
        title={`${KIND_TITLE[job.kind]} · ${job.universe_name || job.file_name || 'A universe file'}`}
      />
      <div className='flex min-w-0 flex-wrap justify-end gap-1'>
        {job.kind === 'export' && job.status === 'done' && (
          <>
            <Button asChild size='sm' variant='outline'>
              <a href={exportFileUrl(job.id)} download>
                <Download />
                Download
              </a>
            </Button>
            <Button
              act={stop}
              type='button'
              size='sm'
              variant='ghost'
              className='text-destructive'
              disabled={stop.isPending}
              disabledReason='The file is being discarded.'
              onClick={() => halt('The packed file is discarded')}
            >
              <Trash2 />
              Discard
            </Button>
          </>
        )}
        {job.kind === 'import' &&
          job.status === 'done' &&
          job.universe_id !== null && (
            <Button
              type='button'
              size='sm'
              disabled={opening !== null}
              disabledReason='The universe is being opened.'
              onClick={() => {
                if (job.universe_id === null) return
                enter({
                  id: job.universe_id,
                  name: job.universe_name,
                  origin: IMPORTED,
                })
              }}
            >
              <BookOpen />
              Open it
            </Button>
          )}
        {settled && !(job.kind === 'export' && job.status === 'done') && (
          <Button
            act={stop}
            type='button'
            size='sm'
            variant='ghost'
            disabled={stop.isPending}
            disabledReason='It is being cleared.'
            onClick={() => halt('Cleared from the work in hand')}
          >
            <X />
            Clear
          </Button>
        )}
        {!settled && (
          <Button
            act={stop}
            type='button'
            size='sm'
            variant='ghost'
            className='text-destructive'
            disabled={stop.isPending}
            disabledReason='The work is being stopped.'
            onClick={() =>
              halt(
                job.kind === 'export'
                  ? 'The export is stopped'
                  : 'The import is cancelled and its upload removed'
              )
            }
          >
            <CircleStop />
            {job.kind === 'export' ? 'Stop' : 'Cancel the import'}
          </Button>
        )}
      </div>
    </li>
  )
}

export function LibraryWork() {
  const jobs = useLibraryJobs()
  if (jobs.isPending) return <LoadingBlock label='Reading the work in hand' />
  if (jobs.isError)
    return (
      <EmptyState
        size='compact'
        icon={PackageOpen}
        title='The work in hand could not be read'
        description={jobs.error.message}
        action={
          <Button
            type='button'
            variant='outline'
            onClick={() => void jobs.refetch()}
          >
            Try again
          </Button>
        }
      />
    )
  const held = jobs.data
  if (held.length === 0)
    return (
      <EmptyState
        size='inline'
        icon={PackageOpen}
        title='Nothing in hand'
        description='Exports being packed and imports being checked show here.'
      />
    )
  return (
    <ul aria-label='Work in hand' className='flex min-w-0 flex-col gap-3'>
      <Paged items={held} initial={4} as='li' noun={['job', 'jobs']}>
        {(job) => <WorkRow key={job.id} job={job} />}
      </Paged>
    </ul>
  )
}
