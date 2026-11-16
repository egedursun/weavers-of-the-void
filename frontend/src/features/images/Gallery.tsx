import { useState } from 'react'
import { Star, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ConfirmDialog, Paged, Picture } from '@/components/domain'
import { type ImageRecord, deleteImage, setCover, useImageAction } from './api'
import { mediaUrl } from './media'

type GalleryProps = {
  images: ImageRecord[]
  title: string
  veiled?: boolean
  veiledOf?: (image: ImageRecord) => boolean
  captionOf?: (image: ImageRecord) => string | null
  onOpen: (index: number) => void
  manage?: boolean
  readOnlyReason?: string | null
}

export function Gallery({
  images,
  title,
  veiled = false,
  veiledOf,
  captionOf,
  onOpen,
  manage = true,
  readOnlyReason = null,
}: GalleryProps) {
  const [doomed, setDoomed] = useState<ImageRecord | null>(null)
  const remove = useImageAction(deleteImage, 'Image deleted')
  const cover = useImageAction(setCover, 'Cover set')
  const busy = remove.isPending || cover.isPending
  const blocked = readOnlyReason ?? (busy ? 'Working on it.' : null)
  if (images.length === 0) return null
  return (
    <>
      <ul
        data-domain='image-gallery'
        className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'
      >
        <Paged items={images} as='li'>
          {(image, index) => (
            <li
              key={image.id}
              className='group relative min-w-0 overflow-hidden rounded-md border surface-well border-gild/45 bg-muted/70'
            >
              <a
                href={mediaUrl(image.file_name) ?? undefined}
                onClick={(event) => {
                  event.preventDefault()
                  onOpen(index)
                }}
                aria-label={
                  captionOf?.(image) ??
                  image.caption ??
                  `${title}, image ${index + 1}`
                }
                className='block outline-none focus-visible:ring-2 focus-visible:ring-ring'
              >
                <Picture
                  src={mediaUrl(image.file_name, 320)}
                  alt={image.caption ?? title}
                  loading='lazy'
                  className={cn(
                    'aspect-square w-full object-cover transition-transform group-hover:scale-105',
                    (veiled || veiledOf?.(image)) && 'blur-lg'
                  )}
                />
              </a>
              {image.is_cover && (
                <Badge
                  size='sm'
                  className='pointer-events-none absolute top-2 left-2'
                >
                  <Star />
                  Cover
                </Badge>
              )}
              {manage && (
                <div className='absolute right-2 bottom-2 flex gap-1 transition-opacity pointer-fine:opacity-0 pointer-fine:group-hover:opacity-100 pointer-fine:focus-within:opacity-100'>
                  {!image.is_cover && (
                    <Button
                      variant='secondary'
                      size='icon-sm'
                      aria-label='Make this the cover'
                      title='Make this the cover'
                      disabled={blocked !== null}
                      disabledReason={blocked ?? undefined}
                      onClick={() => cover.mutate(image.id)}
                    >
                      <Star />
                    </Button>
                  )}
                  <Button
                    variant='secondary'
                    size='icon-sm'
                    className='hover:bg-destructive hover:text-destructive-foreground'
                    aria-label='Delete this image'
                    title='Delete this image'
                    disabled={blocked !== null}
                    disabledReason={blocked ?? undefined}
                    onClick={() => setDoomed(image)}
                  >
                    <Trash2 />
                  </Button>
                </div>
              )}
            </li>
          )}
        </Paged>
      </ul>
      <ConfirmDialog
        open={doomed !== null}
        onOpenChange={(open) => !open && setDoomed(null)}
        title='Delete this image?'
        desc='The image file is removed from this record for good.'
        destructive
        confirmText='Delete'
        isLoading={remove.isPending}
        handleConfirm={() => {
          if (doomed) remove.mutate(doomed.id)
          setDoomed(null)
        }}
      />
    </>
  )
}
