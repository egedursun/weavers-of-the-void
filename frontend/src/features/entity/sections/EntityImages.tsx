import { PenLine } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { JobProgress, Section } from '@/components/domain'
import { Gallery } from '@/features/images/Gallery'
import { GenerateImageButton } from '@/features/images/GenerateImageButton'
import { ImageUploadZone } from '@/features/images/ImageUploadZone'
import { PromptBox } from '@/features/images/PromptBox'
import { useLoreGate } from '../actions/gate'
import { useJob, useLoreMutation, useRunningJob } from '../api/mutations'
import { type EntityDetail } from '../api/types'

type EntityImagesProps = {
  detail: EntityDetail
  onOpen: (index: number) => void
  readOnlyReason: string | null
}

export function EntityImages({
  detail,
  onOpen,
  readOnlyReason,
}: EntityImagesProps) {
  const entity = detail.entity
  const gate = useLoreGate()
  const writing = useRunningJob('content', 'entity_id', entity.id)
  const savePrompt = useLoreMutation({
    run: (prompt: string | null) =>
      unwrap(
        api.PATCH('/api/entities/{entity_id}', {
          params: { path: { entity_id: entity.id } },
          body: { image_prompt: prompt },
        })
      ),
    success: 'Image prompt saved',
  })
  const writePrompt = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/entities/{entity_id}/image-prompt', {
          params: { path: { entity_id: entity.id } },
        })
      ),
    success: 'Writing the prompt…',
  })
  const job = useJob(writePrompt.data?.job_id ?? null)
  const writeReason =
    gate.reason({ llm: true }) ??
    (writing ? 'A writing job for this record is under way.' : null) ??
    (writePrompt.isPending ? 'Working on it.' : null)
  const veiled = entity.entity_type === 'outer_being'
  const count = detail.images.length
  return (
    <Section
      id='section-images'
      title={count ? `Images ${formatInteger(count)}` : 'Images'}
      description={
        veiled ? 'An outer thing: its likeness stays veiled.' : undefined
      }
    >
      <Gallery
        images={detail.images}
        title={entity.name}
        veiled={veiled}
        onOpen={onOpen}
        readOnlyReason={readOnlyReason}
      />
      <div className='flex min-w-0 flex-wrap items-start gap-3'>
        <GenerateImageButton
          nodeId={entity.id}
          hasImages={count > 0}
          readOnlyReason={readOnlyReason}
        />
      </div>
      <ImageUploadZone
        nodeId={entity.id}
        label={`Upload images of ${entity.name}`}
        disabledReason={readOnlyReason}
      />
      <PromptBox
        key={entity.image_prompt ?? ''}
        prompt={entity.image_prompt}
        onSave={(prompt) => savePrompt.mutate(prompt)}
        saving={savePrompt.isPending}
        readOnlyReason={readOnlyReason}
      />
      <Button
        variant='outline'
        className='self-start'
        disabled={writeReason !== null}
        disabledReason={writeReason ?? undefined}
        onClick={() => writePrompt.mutate()}
      >
        <PenLine />
        {entity.image_prompt ? 'Rewrite the prompt' : 'Write the prompt'}
      </Button>
      {job.data && (
        <JobProgress job={job.data} title={`Image prompt of ${entity.name}`} />
      )}
    </Section>
  )
}
