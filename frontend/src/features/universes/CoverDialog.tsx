import { useEffect, useMemo, useState } from 'react'
import {
  Brush,
  Check,
  ImageOff,
  ImageUp,
  Images,
  LoaderCircle,
  Sparkles,
  Undo2,
} from 'lucide-react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  FormRow,
  LoadingBlock,
  Medallion,
  Picture,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { FilePicker } from '@/components/domain/FilePicker'
import { Label, Muted } from '@/components/typography'
import { type ActDialogProps, ActHeader } from './ActHeader'
import { UniverseCover } from './UniverseCrest'
import {
  universeMediaUrl,
  useClearCover,
  useCoverFromMedia,
  useCoverPrompt,
  usePaintCover,
  useUniverseImageModel,
  useSetCover,
  useUniverseImages,
} from './api'

const IMAGE_ACCEPT = 'image/png,image/jpeg,image/webp'
const IMAGES_SHOWN = 12

type Source = 'upload' | 'images' | 'paint'

const SOURCES: readonly Source[] = ['upload', 'images', 'paint']
const PROMPT_MAX = 2000

function OwnImages({
  universeId,
  chosen,
  onChoose,
}: {
  universeId: string
  chosen: string | null
  onChoose: (fileName: string) => void
}) {
  const images = useUniverseImages(universeId)
  const page = useShowMore(images.data ?? [], IMAGES_SHOWN)
  if (images.isPending) return <LoadingBlock label='Reading its images' />
  if (images.isError)
    return (
      <EmptyState
        size='compact'
        icon={ImageOff}
        title='Its images could not be read'
        description={images.error.message}
      />
    )
  if (page.total === 0)
    return (
      <EmptyState
        size='compact'
        icon={ImageOff}
        title='No images yet'
        description='Images made or uploaded inside this universe can become its cover.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ul
        aria-label='Images of this universe'
        className='grid min-w-0 grid-cols-3 gap-2 sm:grid-cols-4'
      >
        {page.visible.map((item) => {
          const picked = chosen === item.image.file_name
          const name = item.target_name ?? item.image.caption ?? 'An image'
          return (
            <li key={item.image.id} className='min-w-0'>
              <Button
                type='button'
                variant='outline'
                size='figure'
                aria-pressed={picked}
                aria-label={`Use the image of ${name}`}
                onClick={() => onChoose(item.image.file_name)}
                className={cn('relative w-full', picked && 'border-primary')}
              >
                <span className='aspect-square w-full overflow-hidden rounded-md surface-well'>
                  <Picture
                    src={universeMediaUrl(universeId, item.image.file_name)}
                    alt={name}
                    loading='lazy'
                    compact
                    className='size-full object-cover'
                  />
                </span>
                {picked && (
                  <Check
                    aria-hidden='true'
                    className='absolute end-2 top-2 size-icon-md text-primary'
                  />
                )}
              </Button>
            </li>
          )
        })}
      </ul>
      <ShowMore state={page} noun={['image', 'images']} />
    </div>
  )
}

function PaintPanel({
  universeId,
  painting,
  onPaint,
}: {
  universeId: string
  painting: boolean
  onPaint: (prompt: string) => void
}) {
  const offered = useCoverPrompt(universeId)
  const model = useUniverseImageModel(universeId)
  const [draft, setDraft] = useState<string | null>(null)
  const seed = offered.data?.prompt ?? ''
  const prompt = draft ?? seed
  const blocked = model.data
    ? model.data.status.available
      ? null
      : (model.data.status.reason ?? 'The image model is not available.')
    : model.isError
      ? model.error.message
      : 'Asking the image model whether it is ready.'
  const empty = prompt.trim().length === 0
  if (offered.isPending)
    return <LoadingBlock label='Reading the seed of the universe' />
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <FormRow
        label='What the cover shows'
        description={`Starts from the seed of the universe. Write anything; the image model paints it in this universe's own image style. ${prompt.length}/${PROMPT_MAX}`}
      >
        {(id) => (
          <Textarea
            id={id}
            value={prompt}
            maxLength={PROMPT_MAX}
            disabled={painting}
            onChange={(event) => setDraft(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-2'>
        <Button
          type='button'
          size='sm'
          variant='ghost'
          disabled={painting || draft === null || draft === seed}
          disabledReason={
            painting
              ? 'The cover is being painted.'
              : 'The prompt is already the seed.'
          }
          onClick={() => setDraft(null)}
        >
          <Undo2 />
          Back to the seed
        </Button>
        <Button
          type='button'
          disabled={blocked !== null || empty || painting}
          disabledReason={
            blocked ??
            (empty
              ? 'Write what the cover shows first.'
              : 'The cover is being painted.')
          }
          onClick={() => onPaint(prompt.trim())}
        >
          {painting ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <Sparkles />
          )}
          {painting ? 'Painting' : 'Paint it'}
        </Button>
      </div>
      {painting && (
        <div
          role='status'
          className='flex min-w-0 items-center gap-3 rounded-md surface-sheen p-3'
        >
          <Medallion icon={Brush} tone='gold' size='sm' />
          <Muted as='span' variant='caption'>
            The image model is painting the cover. It takes about a minute; the
            new cover shows above when it is done.
          </Muted>
        </div>
      )}
    </div>
  )
}

export function CoverDialog({ universe, onClose }: ActDialogProps) {
  const [source, setSource] = useState<Source>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [painted, setPainted] = useState<File | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const setCover = useSetCover()
  const paint = usePaintCover()
  const fromMedia = useCoverFromMedia()
  const clear = useClearCover()
  const working = setCover.isPending || fromMedia.isPending || clear.isPending
  const local = source === 'paint' ? painted : source === 'upload' ? file : null
  const preview = useMemo(
    () => (local ? URL.createObjectURL(local) : null),
    [local]
  )
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview)
    },
    [preview]
  )
  const startPaint = (prompt: string) =>
    paint.mutate(
      { id: universe.id, prompt },
      {
        onSuccess: (image) => {
          setPainted(image)
          toast.success('The cover is painted; set it when you like it.')
        },
        onError: (error: Error) => toast.error(error.message),
      }
    )
  const done = (message: string) => ({
    onSuccess: () => {
      toast.success(message)
      onClose()
    },
    onError: (error: Error) => toast.error(error.message),
  })
  const save = () => {
    if (local)
      setCover.mutate(
        { id: universe.id, file: local },
        done(`${universe.name} has a new cover`)
      )
    if (source === 'images' && fileName)
      fromMedia.mutate(
        { id: universe.id, fileName },
        done(`${universe.name} has a new cover`)
      )
  }
  const ready = source === 'images' ? fileName !== null : local !== null
  const newCover =
    source === 'images'
      ? fileName && universeMediaUrl(universe.id, fileName)
      : preview
  return (
    <>
      <ActHeader icon={ImageUp} title={`The cover of ${universe.name}`}>
        Choose an image for the book on the shelf: one from your device, one of
        its own images, or a new one painted by its image model. Without one the
        book shows a crest made from its name.
      </ActHeader>
      <div className='grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label>Now</Label>
          <div className='aspect-video min-w-0 overflow-hidden rounded-md surface-well'>
            <UniverseCover universe={universe} />
          </div>
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label>New cover</Label>
          <div className='aspect-video min-w-0 overflow-hidden rounded-md surface-well'>
            {newCover ? (
              <Picture
                src={newCover}
                alt='The chosen cover'
                className='size-full object-cover'
              />
            ) : (
              <span className='flex size-full flex-col items-center justify-center gap-2 p-4 text-center sealed-well'>
                <ImageUp
                  aria-hidden='true'
                  className='size-icon-lg text-muted-foreground'
                />
                <Muted as='span' variant='caption'>
                  Drop an image, pick one of its own or paint a new one.
                </Muted>
              </span>
            )}
          </div>
        </div>
      </div>
      <Tabs
        value={source}
        onValueChange={(value) =>
          setSource(SOURCES.find((item) => item === value) ?? 'upload')
        }
      >
        <TabsList aria-label='Where the cover comes from'>
          <TabsTrigger value='upload'>
            <ImageUp />
            From this device
          </TabsTrigger>
          <TabsTrigger value='images'>
            <Images />
            From its images
          </TabsTrigger>
          <TabsTrigger value='paint'>
            <Brush />
            Paint it
          </TabsTrigger>
        </TabsList>
        <TabsContent value='upload'>
          <FilePicker
            file={file}
            onChange={setFile}
            accept={IMAGE_ACCEPT}
            label='Drop a PNG, JPEG or WebP image here'
          />
        </TabsContent>
        <TabsContent value='images'>
          <OwnImages
            universeId={universe.id}
            chosen={fileName}
            onChoose={setFileName}
          />
        </TabsContent>
        <TabsContent value='paint'>
          <PaintPanel
            universeId={universe.id}
            painting={paint.isPending}
            onPaint={startPaint}
          />
        </TabsContent>
      </Tabs>
      <DialogFooter>
        <Button
          type='button'
          variant='ghost'
          className='text-destructive'
          disabled={!universe.cover_path || working}
          disabledReason={
            universe.cover_path
              ? 'The cover is being changed.'
              : 'It already shows the crest of its name.'
          }
          onClick={() =>
            clear.mutate(
              universe.id,
              done(`${universe.name} shows its crest again`)
            )
          }
        >
          <ImageOff />
          Remove the cover
        </Button>
        <Button type='button' variant='outline' onClick={onClose}>
          Cancel
        </Button>
        <Button
          type='button'
          disabled={!ready || working}
          disabledReason={
            ready
              ? 'The cover is being changed.'
              : source === 'upload'
                ? 'Choose an image first.'
                : source === 'images'
                  ? 'Pick one of its images first.'
                  : 'Paint the cover first.'
          }
          onClick={save}
        >
          {working ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <ImageUp />
          )}
          Set the cover
        </Button>
      </DialogFooter>
    </>
  )
}
