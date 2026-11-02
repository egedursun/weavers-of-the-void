import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { RecordGallery } from '@/features/pantheon/RecordGallery'
import { type ImageRecord, type SonRecord } from '@/features/pantheon/api'

export function SonImages({
  son,
  images,
}: {
  son: SonRecord
  images: ImageRecord[]
}) {
  return (
    <RecordGallery
      key={son.image_prompt ?? ''}
      title='Images'
      nodeId={son.id}
      name={son.name}
      images={images}
      prompt={son.image_prompt}
      onSavePrompt={(prompt) =>
        unwrap(
          api.PUT('/api/sons/{son_id}/image-prompt', {
            params: { path: { son_id: son.id } },
            body: { image_prompt: prompt },
          })
        )
      }
    />
  )
}
