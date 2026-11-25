import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  ImageOff,
  ImagePlus,
  ListOrdered,
  Paintbrush,
  PenLine,
  Square,
} from 'lucide-react'
import { toast } from 'sonner'
import { useMutation } from '@/api/mutation'
import { queryKeys } from '@/api/queryKeys'
import { formatDateTime, formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ConfirmDialog,
  JobProgress,
  MiniStat,
  Paged,
  Section,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useJob } from '@/features/entity/api/mutations'
import { useNames, useWorldState } from '@/features/entity/api/queries'
import { type WriteTarget } from '@/features/team/writeGate'
import { ImageGenFeedLines } from './ImageGenFeedLines'
import {
  type QueueStatus,
  imageKeys,
  startBulk,
  stopBulk,
  useHealth,
  useImageGenStatus,
  writeMissingPrompts,
} from './api'
import { WORKER_OFF_REASON, useImageGenEvents } from './imageGenState'

const PERCENT = 100
const READ_ONLY = 'A guest world is open read-only.'
const NO_LLM = 'The language model is not connected; this needs it.'

function useImageMutation<T>(
  writes: readonly WriteTarget[],
  run: () => Promise<T>,
  onDone: (result: T) => void
) {
  const queryClient = useQueryClient()
  return useMutation({
    writes,
    mutationFn: run,
    onSuccess: (result) => {
      onDone(result)
      void queryClient.invalidateQueries({ queryKey: imageKeys.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
    },
    onError: (error) =>
      toast.error(error instanceof Error ? error.message : String(error)),
  })
}

const QUEUE_SHOWN = 5

const IMAGE_CLASS_LABEL: Record<
  QueueStatus['queue'][number]['image_class'],
  string
> = {
  manual: 'Asked by you',
  bulk: 'Bulk run',
  auto: 'After the epoch',
  restyle: 'Repaint',
}

function bulkTitle(bulk: QueueStatus['bulk']): string {
  if (!bulk.running) return 'Last bulk run'
  if (bulk.stop_requested) return 'Stopping after the current image'
  if (bulk.restyle) return 'Repainting images in the world style'
  if (bulk.rerun_requested)
    return 'Painting missing images; another pass follows for the new epoch'
  return bulk.auto
    ? 'Painting missing images after the epoch'
    : 'Painting missing images'
}

export function BulkImageGenPanel() {
  useImageGenEvents()
  const status = useImageGenStatus()
  const health = useHealth()
  const state = useWorldState()
  const names = useNames()
  const [confirming, setConfirming] = useState(false)
  const [promptJob, setPromptJob] = useState<string | null>(null)
  const job = useJob(promptJob)
  const start = useImageMutation(
    [{ method: 'POST', path: '/api/image-gen/batch/start' }],
    startBulk,
    () => toast.success('Bulk generation started')
  )
  const stop = useImageMutation(
    [{ method: 'POST', path: '/api/image-gen/batch/stop' }],
    stopBulk,
    () => toast.success('Bulk generation stops after the current image')
  )
  const prompts = useImageMutation(
    [{ method: 'POST', path: '/api/entities/prompts/write-missing' }],
    writeMissingPrompts,
    (accepted) => {
      setPromptJob(accepted.job_id)
      toast.success('Writing image prompts')
    }
  )
  return (
    <Section
      title='Image generation'
      description='Portraits and scenes for every record that has none. Images are only ever added, never replaced.'
      surface='card'
      level={3}
      id='image-generation'
    >
      {status.isPending && (
        <div className='flex flex-col gap-3'>
          <Skeleton className='h-control-md w-1/2' />
          <Skeleton className='h-textarea w-full' />
        </div>
      )}
      {status.isError && <Text tone='destructive'>{status.error.message}</Text>}
      {status.isSuccess &&
        (() => {
          const queue = status.data.status
          const bulk = queue.bulk
          const configured = health.data?.image_worker_configured ?? true
          const offReason = !configured
            ? WORKER_OFF_REASON
            : !queue.available
              ? (queue.reason ?? 'The image worker is not available right now.')
              : null
          const readOnly = state.data?.read_only ? READ_ONLY : null
          const missing = status.data.missing
          const promptless = state.data?.promptless_count ?? 0
          const finished = bulk.done + bulk.failed + bulk.skipped
          const percent = bulk.total > 0 ? (finished / bulk.total) * PERCENT : 0
          const nameOf = (nodeId: number) =>
            names.data?.find((entry) => entry.id === nodeId)?.name ??
            `Record ${nodeId}`
          const startReason =
            readOnly ??
            offReason ??
            (bulk.running ? 'A bulk run is already going.' : null) ??
            (missing === 0
              ? 'Every important record already has an image.'
              : null) ??
            (start.isPending ? 'Working on it.' : null)
          const promptReason =
            readOnly ??
            (state.data && !state.data.llm_enabled ? NO_LLM : null) ??
            (promptless === 0
              ? 'Every record already has an image prompt.'
              : null) ??
            (prompts.isPending ? 'Working on it.' : null)
          return (
            <div className='flex min-w-0 flex-col gap-4'>
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Badge variant={offReason ? 'warning' : 'success'}>
                  {offReason ? 'Image worker off' : 'Image worker ready'}
                </Badge>
                {!offReason && (
                  <Muted variant='caption'>
                    {`${queue.width} × ${queue.height} · ${plural(queue.steps, 'step', 'steps')}`}
                  </Muted>
                )}
              </div>
              {offReason && <Muted>{offReason}</Muted>}
              <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
                <MiniStat
                  icon={ImageOff}
                  label='Missing images'
                  value={missing}
                  tone={missing > 0 ? 'warning' : 'success'}
                />
                <MiniStat
                  icon={PenLine}
                  label='Without a prompt'
                  value={promptless}
                  tone={promptless > 0 ? 'info' : 'success'}
                />
                <MiniStat
                  icon={ListOrdered}
                  label='Waiting in queue'
                  value={queue.queue.length}
                  tone='muted'
                />
                <MiniStat
                  icon={Paintbrush}
                  label='Painting now'
                  value={
                    queue.current ? nameOf(queue.current.node_id) : 'Nothing'
                  }
                  tone={queue.current ? 'gold' : 'muted'}
                  hint={
                    queue.current
                      ? `${IMAGE_CLASS_LABEL[queue.current.image_class]}${queue.current.queued_at ? ` · queued ${formatDateTime(queue.current.queued_at)}` : ''}`
                      : undefined
                  }
                />
              </div>
              {queue.queue.length > 0 && (
                <ul className='flex min-w-0 flex-col gap-1'>
                  <Paged
                    items={queue.queue}
                    initial={QUEUE_SHOWN}
                    noun={['image', 'images']}
                    as='li'
                  >
                    {(item, index) => (
                      <li
                        key={`${item.node_id}-${item.queued_at}`}
                        className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 px-2 py-1'
                      >
                        <Badge size='sm' variant='outline'>
                          {formatInteger(index + 1)}
                        </Badge>
                        <Text as='span' truncate className='min-w-0 flex-1'>
                          {nameOf(item.node_id)}
                        </Text>
                        <Badge size='sm' variant='secondary'>
                          {IMAGE_CLASS_LABEL[item.image_class]}
                        </Badge>
                        <Muted as='span' variant='caption'>
                          {item.queued_at ? formatDateTime(item.queued_at) : ''}
                        </Muted>
                      </li>
                    )}
                  </Paged>
                </ul>
              )}
              {(bulk.running || bulk.total > 0) && (
                <div className='flex min-w-0 flex-col gap-2'>
                  <div className='flex min-w-0 flex-wrap items-center gap-2'>
                    <Text as='span' weight='medium' className='min-w-0 flex-1'>
                      {bulkTitle(bulk)}
                    </Text>
                    <Muted variant='caption'>
                      {`${formatInteger(bulk.done)} done · ${formatInteger(bulk.failed)} failed · ${formatInteger(bulk.skipped)} skipped of ${formatInteger(bulk.total)}`}
                    </Muted>
                  </div>
                  <Progress
                    value={percent}
                    tone={bulk.failed > 0 ? 'warning' : 'default'}
                    aria-label='Bulk image generation'
                  />
                </div>
              )}
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Button
                  act={start}
                  disabled={startReason !== null}
                  disabledReason={startReason ?? undefined}
                  onClick={() => setConfirming(true)}
                >
                  <ImagePlus />
                  {`Generate ${formatInteger(missing)} missing images`}
                </Button>
                <Button
                  act={stop}
                  variant='outline'
                  disabled={
                    !bulk.running || bulk.stop_requested || stop.isPending
                  }
                  disabledReason={
                    bulk.running
                      ? 'It already stops after the current image.'
                      : 'No bulk run is going.'
                  }
                  onClick={() => stop.mutate()}
                >
                  <Square />
                  Stop
                </Button>
                <Button
                  act={prompts}
                  variant='outline'
                  disabled={promptReason !== null}
                  disabledReason={promptReason ?? undefined}
                  onClick={() => prompts.mutate()}
                >
                  <PenLine />
                  Write missing prompts
                </Button>
              </div>
              {job.data && (
                <JobProgress job={job.data} title='Writing image prompts' />
              )}
              <ImageGenFeedLines log={queue.log} />
              <ConfirmDialog
                act={start}
                open={confirming}
                onOpenChange={setConfirming}
                title={`Generate ${plural(missing, 'image', 'images')}?`}
                desc='The worker paints one image at a time; your own requests still go first. You can stop at any time.'
                confirmText='Start'
                isLoading={start.isPending}
                handleConfirm={() => {
                  setConfirming(false)
                  start.mutate()
                }}
              />
            </div>
          )
        })()}
    </Section>
  )
}
