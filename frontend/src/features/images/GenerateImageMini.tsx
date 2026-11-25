import { ImagePlus, LoaderCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { stageText, useNodeImageState } from './imageGenState'
import { useGenerateImage } from './useGenerateImage'

type GenerateImageMiniProps = {
  nodeId: number
  name: string
}

export function GenerateImageMini({ nodeId, name }: GenerateImageMiniProps) {
  const state = useNodeImageState(nodeId)
  const generate = useGenerateImage(nodeId)
  const working = state.phase === 'running' || state.phase === 'queued'
  const reason =
    state.phase === 'disabled'
      ? state.reason
      : state.phase === 'queued'
        ? `Queued; ${state.ahead} ahead.`
        : state.phase === 'running'
          ? `${stageText(state.stage)} · ${Math.round(state.percent)}%`
          : generate.isPending
            ? 'Working on it.'
            : null
  return (
    <Button
      act={generate}
      variant='ghost'
      size='icon-sm'
      aria-label={`Generate an image of ${name}`}
      title={reason ?? `Generate an image of ${name}`}
      disabled={reason !== null}
      disabledReason={reason ?? undefined}
      onClick={(event) => {
        event.stopPropagation()
        generate.mutate()
      }}
    >
      {working ? <LoaderCircle className='animate-spin' /> : <ImagePlus />}
    </Button>
  )
}
