import { useEffect, useId, useState } from 'react'
import { ImagePlus, Wand2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { EmptyState, Section, FieldTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { Gallery } from '@/features/images/Gallery'
import { Lightbox } from '@/features/images/Lightbox'
import { useGalleryStore } from '@/features/images/galleryStore'
import { ActionButton } from './ActionButton'
import { ActionJob } from './ActionJob'
import { type ImageRecord } from './api'
import { useGodGate } from './gate'
import { useGodAction } from './godAction'

type RecordGalleryProps = {
  sectionId: string
  title: string
  nodeId: number
  name: string
  images: ImageRecord[]
  prompt: string | null
  promptLabel?: string
  onSavePrompt?: (prompt: string) => Promise<unknown>
  emptyText?: string
}

export function RecordGallery({
  sectionId,
  title,
  nodeId,
  name,
  images,
  prompt,
  promptLabel = 'Portrait prompt',
  onSavePrompt,
  emptyText = 'No image yet. Generate one from the prompt or upload your own.',
}: RecordGalleryProps) {
  const promptId = useId()
  const open = useGalleryStore((store) =>
    store.nodeId === nodeId ? store.index : null
  )
  const openAt = useGalleryStore((store) => store.open)
  const close = useGalleryStore((store) => store.close)
  const setOpen = (index: number | null) =>
    index === null ? close() : openAt(nodeId, index)
  useEffect(
    () => () => {
      if (useGalleryStore.getState().nodeId === nodeId)
        useGalleryStore.getState().close()
    },
    [nodeId]
  )
  const uploadId = useId()
  const [draft, setDraft] = useState(prompt ?? '')
  const { reason, state } = useGodGate()
  const imageGen = state.data?.image_gen
  const generateBlocked =
    reason() ??
    (imageGen && !imageGen.available
      ? (imageGen.reason ?? 'Image generation is not available.')
      : null)
  const generate = useGodAction({
    run: () =>
      unwrap(api.POST('/api/image-gen', { body: { node_id: nodeId } })),
    success: 'The image is queued',
  })
  const upload = useGodAction({
    run: (file: File) =>
      unwrap(
        api.POST('/api/images', {
          params: { query: { node_id: nodeId } },
          body: file as unknown as string,
          bodySerializer: (body: unknown) => body as BodyInit,
          headers: { 'Content-Type': file.type },
        })
      ),
    success: 'Image added',
  })
  const savePrompt = useGodAction({
    run: (text: string) =>
      onSavePrompt ? onSavePrompt(text) : Promise.resolve(null),
    success: 'Prompt saved',
  })
  return (
    <Section id={sectionId} title={title} level={3}>
      {images.length === 0 ? (
        <EmptyState
          icon={ImagePlus}
          size='compact'
          title={`No image of ${name}`}
          description={emptyText}
        />
      ) : (
        <Gallery
          images={images}
          title={name}
          onOpen={setOpen}
          readOnlyReason={reason()}
        />
      )}
      <Lightbox
        images={images}
        index={open}
        onIndexChange={setOpen}
        title={name}
        readOnlyReason={reason()}
      />
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <ActionButton
          label='Generate image'
          icon={Wand2}
          blocked={generateBlocked}
          pending={generate.isPending}
          onRun={() => generate.mutate()}
        />
        <FieldLabel htmlFor={uploadId} className='sr-only'>
          Upload an image
        </FieldLabel>
        <Input
          id={uploadId}
          type='file'
          accept='image/png,image/jpeg,image/webp'
          className='max-w-xs'
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) upload.mutate(file)
            event.target.value = ''
          }}
        />
      </div>
      <ActionJob
        jobId={generate.jobId}
        title='Image'
        onDismiss={generate.clearJob}
      />
      {onSavePrompt && (
        <div className='flex min-w-0 flex-col gap-2'>
          <FieldTile id={promptId} label={promptLabel}>
            <Textarea
              id={promptId}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
          </FieldTile>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <ActionButton
              label='Save prompt'
              blocked={
                reason() ??
                (draft === (prompt ?? '') ? 'Nothing changed.' : null)
              }
              pending={savePrompt.isPending}
              onRun={() => savePrompt.mutate(draft)}
            />
            <Muted variant='caption'>
              Generated images use this description.
            </Muted>
          </div>
        </div>
      )}
    </Section>
  )
}
