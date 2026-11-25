import { useState } from 'react'
import { CircleStop, Download, FileUp, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { formatBytes } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { DialogFooter } from '@/components/ui/dialog'
import { EmptyState, LoadingBlock } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { type ActDialogProps, ActHeader } from './ActHeader'
import { LibraryJobProgress } from './LibraryJobProgress'
import {
  exportFileUrl,
  jobSettled,
  useLibraryJob,
  useLibraryJobs,
  useStartExport,
  useStopJob,
} from './api'

export function ExportDialog({ universe, onClose }: ActDialogProps) {
  const start = useStartExport()
  const stop = useStopJob()
  const jobs = useLibraryJobs()
  const held = (jobs.data ?? []).find(
    (item) =>
      item.kind === 'export' &&
      item.universe_id === universe.id &&
      item.status !== 'cancelled'
  )
  const [started, setStarted] = useState<string | null>(null)
  const jobId = started ?? held?.id ?? null
  const job = useLibraryJob('exports', jobId)
  const current = job.data ?? held
  const settled = jobSettled(current)
  const ready = current?.status === 'done'
  const running = current !== undefined && !settled
  const begin = () =>
    start.mutate(universe.id, {
      onSuccess: (created) => setStarted(created.id),
      onError: (error) => toast.error(error.message),
    })
  const halt = () => {
    if (!current) return
    stop.mutate(current, {
      onSuccess: () => {
        toast.success(
          ready ? 'The packed file is discarded' : 'The export is stopped'
        )
        setStarted(null)
      },
      onError: (error) => toast.error(error.message),
    })
  }
  return (
    <>
      <ActHeader icon={FileUp} title={`Export ${universe.name}`}>
        The whole universe, its records and its images, packed into one .aerona
        file you can keep or give to someone to import.
      </ActHeader>
      {current ? (
        <LibraryJobProgress job={current} title='Packing the universe' />
      ) : jobId !== null && job.isError ? (
        <Text tone='destructive'>{job.error.message}</Text>
      ) : jobId !== null ? (
        <LoadingBlock label='Starting the export' />
      ) : (
        <EmptyState
          size='compact'
          icon={FileUp}
          title='Ready to pack'
          description={`${universe.name} is about ${formatBytes(universe.size_bytes)} on disk.`}
        />
      )}
      {current && ready && current.file_name && (
        <Muted variant='caption'>
          {`${current.file_name} · ${formatBytes(current.size_bytes)}`}
        </Muted>
      )}
      <DialogFooter>
        {current && !settled ? (
          <Button
            act={stop}
            type='button'
            variant='ghost'
            className='text-destructive'
            disabled={stop.isPending}
            disabledReason='The export is being stopped.'
            onClick={halt}
          >
            <CircleStop />
            Stop the export
          </Button>
        ) : ready ? (
          <Button
            act={stop}
            type='button'
            variant='ghost'
            className='text-destructive'
            disabled={stop.isPending}
            disabledReason='The file is being discarded.'
            onClick={halt}
          >
            <Trash2 />
            Discard the file
          </Button>
        ) : null}
        <Button type='button' variant='outline' onClick={onClose}>
          {running ? 'Keep it running and close' : 'Close'}
        </Button>
        {current && ready ? (
          <Button asChild>
            <a href={exportFileUrl(current.id)} download>
              <Download />
              Download the file
            </a>
          </Button>
        ) : (
          <Button
            act={start}
            type='button'
            disabled={start.isPending || running}
            disabledReason='The universe is being packed.'
            onClick={begin}
          >
            <FileUp />
            {settled ? 'Pack it again' : 'Start the export'}
          </Button>
        )}
      </DialogFooter>
    </>
  )
}
