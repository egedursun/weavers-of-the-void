import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  type ImageListView,
  deleteImage,
  useImageAction,
} from '@/features/images/api'
import { mediaUrl } from '@/features/images/media'
import {
  CATEGORY_ICON,
  FALLBACK_ICON,
  categoryLabel,
  categoryOf,
} from './galleryModel'

export type GalleryDensity = 'roomy' | 'dense'

const TILE_WIDTH = { roomy: 640, dense: 320 } as const

function Tile({
  item,
  index,
  density,
  veiled,
  worldName,
  onOpen,
  onDelete,
  deleteBlocked,
}: {
  item: ImageListView
  index: number
  density: GalleryDensity
  veiled: boolean
  worldName: string | null
  onOpen: (index: number) => void
  onDelete: () => void
  deleteBlocked: string | null
}) {
  const category = categoryOf(item)
  const Icon = CATEGORY_ICON[category] ?? FALLBACK_ICON
  const name = item.target_name ?? 'Unknown record'
  return (
    <li className='group relative min-w-0 overflow-hidden rounded-xl border bg-muted'>
      <a
        href={mediaUrl(item.image.file_name)}
        aria-label={`${name}, ${categoryLabel(category)}`}
        onClick={(event) => {
          event.preventDefault()
          onOpen(index)
        }}
        className='block outline-none focus-visible:ring-2 focus-visible:ring-ring'
      >
        <img
          src={mediaUrl(item.image.file_name, TILE_WIDTH[density])}
          alt={item.image.caption ?? name}
          loading='lazy'
          decoding='async'
          className={cn(
            'aspect-square w-full object-cover transition-transform duration-300 group-hover:scale-105',
            veiled && 'blur-lg'
          )}
        />
        <span className='pointer-events-none absolute inset-x-0 bottom-0 flex min-w-0 flex-col gap-0.5 bg-linear-to-t from-background via-background/80 to-transparent p-2.5 pt-8'>
          <Text as='span' weight='semibold' truncate>
            {name}
          </Text>
          {density === 'roomy' && (
            <Muted as='span' variant='caption' truncate>
              {worldName
                ? `${categoryLabel(category)} · ${worldName}`
                : categoryLabel(category)}
            </Muted>
          )}
        </span>
        <span className='pointer-events-none absolute top-2 left-2'>
          <Badge size='sm' variant='secondary'>
            <Icon />
            {density === 'roomy' ? categoryLabel(category) : null}
          </Badge>
        </span>
      </a>
      <span className='absolute top-2 right-2 transition-opacity pointer-fine:opacity-0 pointer-fine:group-hover:opacity-100 pointer-fine:focus-within:opacity-100'>
        <Button
          variant='secondary'
          size='icon-sm'
          className='hover:bg-destructive hover:text-destructive-foreground'
          aria-label={`Delete this image of ${name}`}
          title='Delete this image'
          disabled={deleteBlocked !== null}
          disabledReason={deleteBlocked ?? undefined}
          onClick={onDelete}
        >
          <Trash2 />
        </Button>
      </span>
    </li>
  )
}

export function GalleryGrid({
  items,
  density,
  veiledOf,
  worldOf,
  onOpen,
  readOnlyReason = null,
}: {
  items: ImageListView[]
  density: GalleryDensity
  veiledOf: (item: ImageListView) => boolean
  worldOf: (item: ImageListView) => string | null
  onOpen: (index: number) => void
  readOnlyReason?: string | null
}) {
  const [doomed, setDoomed] = useState<ImageListView | null>(null)
  const remove = useImageAction(deleteImage, 'Image deleted')
  const blocked = readOnlyReason ?? (remove.isPending ? 'Working on it.' : null)
  return (
    <>
      <ul
        data-domain='image-gallery'
        className={cn(
          'grid min-w-0 gap-3',
          density === 'roomy'
            ? 'grid-cols-2 md:grid-cols-3 xl:grid-cols-4'
            : 'grid-cols-3 sm:grid-cols-4 md:grid-cols-6 xl:grid-cols-8'
        )}
      >
        {items.map((item, index) => (
          <Tile
            key={item.image.id}
            item={item}
            index={index}
            density={density}
            veiled={veiledOf(item)}
            worldName={worldOf(item)}
            onOpen={onOpen}
            onDelete={() => setDoomed(item)}
            deleteBlocked={blocked}
          />
        ))}
      </ul>
      <ConfirmDialog
        open={doomed !== null}
        onOpenChange={(open) => !open && setDoomed(null)}
        title={`Delete this image of ${doomed?.target_name ?? 'the record'}?`}
        desc='The image file is removed from its record for good.'
        destructive
        confirmText='Delete'
        isLoading={remove.isPending}
        handleConfirm={() => {
          if (doomed) remove.mutate(doomed.image.id)
          setDoomed(null)
        }}
      />
    </>
  )
}
