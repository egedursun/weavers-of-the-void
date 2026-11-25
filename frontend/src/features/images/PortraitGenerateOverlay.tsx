import { type KeyboardEvent, type ReactNode } from 'react'
import { ImagePlus } from 'lucide-react'
import { type Rarity } from '@/constants/rarity'
import { Progress } from '@/components/ui/progress'
import { Portrait } from '@/components/domain'
import { Muted } from '@/components/typography'
import { useGalleryStore } from './galleryStore'
import { percentOf, stageText, useNodeImageState } from './imageGenState'
import { mediaUrl } from './media'
import { useGenerateImage } from './useGenerateImage'

type PortraitGenerateOverlayProps = {
  nodeId: number
  name: string
  cover: string | null
  veiled?: boolean
  rarity?: Rarity
  placeholder?: ReactNode
  onOpen?: () => void
  readOnlyReason?: string | null
}

function activate(event: KeyboardEvent, run: () => void) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    run()
  }
}

const FRAME =
  'relative flex shrink-0 cursor-pointer flex-col items-center gap-1 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring'

export function PortraitGenerateOverlay({
  nodeId,
  name,
  cover,
  veiled = false,
  rarity,
  placeholder,
  onOpen,
  readOnlyReason = null,
}: PortraitGenerateOverlayProps) {
  const state = useNodeImageState(nodeId)
  const openGallery = useGalleryStore((store) => store.open)
  const generate = useGenerateImage(nodeId)
  if (veiled)
    return (
      <div
        role='img'
        aria-label='A shape that is not named'
        className='size-portrait-xl shrink-0 rounded-lg bg-muted blur-sm'
      />
    )
  const openImages = onOpen ?? (() => openGallery(nodeId, 0))
  if (cover)
    return (
      <a
        href={mediaUrl(cover)}
        className={FRAME}
        aria-label={`Open the images of ${name}`}
        onClick={(event) => {
          event.preventDefault()
          openImages()
        }}
      >
        <Portrait
          name={name}
          src={mediaUrl(cover, 320)}
          size='xl'
          shape='square'
          rarity={rarity}
        />
      </a>
    )
  const reason =
    generate.blockedReason ??
    readOnlyReason ??
    (state.phase === 'disabled' ? state.reason : null) ??
    (state.phase === 'queued' ? `Queued; ${state.ahead} ahead.` : null)
  const working = state.phase === 'running' || state.phase === 'queued'
  const run = () => {
    if (reason === null && !working && !generate.isPending) generate.mutate()
  }
  return (
    <div className='flex shrink-0 flex-col items-center gap-2'>
      <a
        role='button'
        tabIndex={0}
        aria-disabled={
          generate.blockedReason !== null ||
          reason !== null ||
          working ||
          undefined
        }
        aria-label={reason ?? `Generate an image of ${name}`}
        title={reason ?? `Generate an image of ${name}`}
        className={FRAME}
        onClick={run}
        onKeyDown={(event) => activate(event, run)}
      >
        {placeholder ?? (
          <Portrait name={name} size='xl' shape='square' rarity={rarity} />
        )}
        {reason === null && !working && (
          <span className='absolute right-1 bottom-1 flex size-control-sm items-center justify-center rounded-full bg-background/90 text-primary shadow-xs'>
            <ImagePlus aria-hidden='true' className='size-icon-sm' />
          </span>
        )}
      </a>
      {state.phase === 'running' && (
        <div className='flex w-full flex-col gap-1'>
          <Progress
            value={percentOf(state)}
            size='sm'
            aria-label='Image generation'
          />
          <Muted variant='caption' truncate>
            {stageText(state.stage)}
          </Muted>
        </div>
      )}
    </div>
  )
}
