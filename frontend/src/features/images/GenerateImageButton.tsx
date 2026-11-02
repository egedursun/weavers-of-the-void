import { ImagePlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Muted } from '@/components/typography'
import { percentOf, stageText, useNodeImageState } from './imageGenState'
import { useGenerateImage } from './useGenerateImage'

type GenerateImageButtonProps = {
  nodeId: number
  hasImages: boolean
  readOnlyReason?: string | null
}

export function GenerateImageButton({
  nodeId,
  hasImages,
  readOnlyReason = null,
}: GenerateImageButtonProps) {
  const state = useNodeImageState(nodeId)
  const generate = useGenerateImage(nodeId)
  const label = hasImages ? 'Generate one more' : 'Generate image'
  const reason =
    readOnlyReason ??
    (state.phase === 'disabled'
      ? state.reason
      : state.phase === 'queued'
        ? `Queued; ${state.ahead} ahead.`
        : state.phase === 'running'
          ? 'It is being painted now.'
          : generate.isPending
            ? 'Working on it.'
            : null)
  return (
    <div data-domain='generate-image' className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          variant='outline'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
          aria-busy={
            state.phase === 'running' || generate.isPending || undefined
          }
          onClick={() => generate.mutate()}
        >
          <ImagePlus />
          {label}
        </Button>
        {state.phase === 'queued' && (
          <Muted variant='caption'>{`Queued · ${state.ahead} ahead`}</Muted>
        )}
      </div>
      {state.phase === 'running' && (
        <div className='flex min-w-0 flex-col gap-1'>
          <Progress
            value={percentOf(state)}
            size='sm'
            aria-label='Image generation'
          />
          <Muted variant='caption'>
            {`${stageText(state.stage)} · ${Math.round(percentOf(state))}%`}
          </Muted>
        </div>
      )}
    </div>
  )
}
