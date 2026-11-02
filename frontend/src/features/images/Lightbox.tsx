import { type ReactNode, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Star, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { queryKeys } from '@/api/queryKeys'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { ConfirmDialog } from '@/components/domain'
import { Muted } from '@/components/typography'
import {
  type ImageRecord,
  deleteImage,
  imageKeys,
  setCaption,
  setCover,
} from './api'
import { mediaUrl } from './media'
import { CAPTION_MAX_LENGTH } from './useImageUpload'

type LightboxProps = {
  images: ImageRecord[]
  index: number | null
  onIndexChange: (index: number | null) => void
  title: string
  veiled?: boolean
  readOnlyReason?: string | null
  extra?: (image: ImageRecord) => ReactNode
}

function wrap(index: number, length: number): number {
  return ((index % length) + length) % length
}

function CaptionForm({
  image,
  blocked,
  onSave,
}: {
  image: ImageRecord
  blocked: string | null
  onSave: (caption: string | null) => void
}) {
  const [caption, setCaptionText] = useState(image.caption ?? '')
  return (
    <form
      className='flex min-w-0 flex-col gap-2 sm:flex-row'
      onSubmit={(event) => {
        event.preventDefault()
        const text = caption.trim()
        onSave(text ? text : null)
      }}
    >
      <Input
        aria-label='Caption'
        placeholder='Caption'
        maxLength={CAPTION_MAX_LENGTH}
        value={caption}
        disabled={blocked !== null}
        onChange={(event) => setCaptionText(event.target.value)}
      />
      <Button
        type='submit'
        variant='secondary'
        disabled={blocked !== null || caption === (image.caption ?? '')}
        disabledReason={blocked ?? 'The caption has not changed.'}
      >
        Save caption
      </Button>
    </form>
  )
}

export function Lightbox({
  images,
  index,
  onIndexChange,
  title,
  veiled = false,
  readOnlyReason = null,
  extra,
}: LightboxProps) {
  const queryClient = useQueryClient()
  const open = index !== null && images.length > 0
  const current = open ? images[wrap(index, images.length)] : null
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: imageKeys.all })
    void queryClient.invalidateQueries({ queryKey: queryKeys.world.all })
  }
  const run = async (work: () => Promise<unknown>, message: string) => {
    setBusy(true)
    try {
      await work()
      toast.success(message)
      refresh()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : String(error))
    } finally {
      setBusy(false)
    }
  }
  const step = (delta: number) => {
    if (index === null || images.length < 2) return
    onIndexChange(wrap(index + delta, images.length))
  }
  const blocked = readOnlyReason ?? (busy ? 'Working on it.' : null)
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onIndexChange(null)}>
      <DialogContent
        className='sm:max-w-3xl'
        onKeyDown={(event) => {
          if (event.target instanceof HTMLInputElement) return
          if (event.key === 'ArrowRight') step(1)
          if (event.key === 'ArrowLeft') step(-1)
        }}
      >
        <DialogHeader>
          <DialogTitle className='truncate'>{title}</DialogTitle>
          <DialogDescription>
            {current
              ? `${formatInteger(wrap(index ?? 0, images.length) + 1)} of ${formatInteger(images.length)}${current.origin === 'generated' ? ' · generated' : ' · uploaded'}`
              : ''}
          </DialogDescription>
        </DialogHeader>
        {current && (
          <div className='flex min-w-0 flex-col gap-4'>
            <div className='relative flex min-w-0 items-center justify-center overflow-hidden rounded-md bg-muted'>
              <img
                src={mediaUrl(current.file_name)}
                alt={current.caption ?? title}
                className={cn(
                  'max-h-96 w-auto max-w-full object-contain sm:max-h-128',
                  veiled && 'blur-xl'
                )}
              />
              {current.is_cover && (
                <Badge size='sm' className='absolute top-2 left-2'>
                  <Star />
                  Cover
                </Badge>
              )}
            </div>
            <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
              <Button
                variant='outline'
                size='icon'
                aria-label='Previous image'
                disabled={images.length < 2}
                disabledReason='There is only one image.'
                onClick={() => step(-1)}
              >
                <ChevronLeft />
              </Button>
              <div className='flex min-w-0 flex-1 flex-wrap items-center justify-center gap-2'>
                <Button
                  variant='outline'
                  disabled={current.is_cover || blocked !== null}
                  disabledReason={
                    current.is_cover
                      ? 'This is already the cover.'
                      : (blocked ?? undefined)
                  }
                  onClick={() =>
                    void run(() => setCover(current.id), 'Cover set')
                  }
                >
                  <Star />
                  Make cover
                </Button>
                <Button
                  variant='destructive'
                  disabled={blocked !== null}
                  disabledReason={blocked ?? undefined}
                  onClick={() => setConfirming(true)}
                >
                  <Trash2 />
                  Delete
                </Button>
              </div>
              <Button
                variant='outline'
                size='icon'
                aria-label='Next image'
                disabled={images.length < 2}
                disabledReason='There is only one image.'
                onClick={() => step(1)}
              >
                <ChevronRight />
              </Button>
            </div>
            <CaptionForm
              key={`${current.id}-${current.caption ?? ''}`}
              image={current}
              blocked={blocked}
              onSave={(text) =>
                void run(() => setCaption(current.id, text), 'Caption saved')
              }
            />
            {extra?.(current)}
            {current.prompt && (
              <Muted variant='caption' truncate={3}>
                {current.prompt}
              </Muted>
            )}
          </div>
        )}
        <ConfirmDialog
          open={confirming}
          onOpenChange={setConfirming}
          title='Delete this image?'
          desc='The image file is removed from this record for good.'
          destructive
          confirmText='Delete'
          isLoading={busy}
          handleConfirm={() => {
            setConfirming(false)
            if (!current) return
            void run(() => deleteImage(current.id), 'Image deleted').then(() =>
              images.length <= 1 ? onIndexChange(null) : step(0)
            )
          }}
        />
      </DialogContent>
    </Dialog>
  )
}
