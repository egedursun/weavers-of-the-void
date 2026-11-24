import { Skeleton } from '@/components/ui/skeleton'
import { RecordGallery } from '@/features/pantheon/RecordGallery'
import { type ImageRecord, useWorldState } from '@/features/pantheon/api'
import { useNodeImages } from './images'

type CreatorGalleriesProps = {
  creatorId: number | null
  name: string
  images: ImageRecord[] | null
  prompt: string | null
  onSavePrompt?: (prompt: string) => Promise<unknown>
}

export function CreatorGalleries({
  creatorId,
  name,
  images,
  prompt,
  onSavePrompt,
}: CreatorGalleriesProps) {
  const state = useWorldState()
  const worldId =
    state.data?.world?.primary_world_id ?? state.data?.worlds[0]?.id ?? null
  const world = state.data?.worlds.find((item) => item.id === worldId)
  const own = useNodeImages(images === null ? creatorId : null)
  const worldImages = useNodeImages(worldId)
  const creatorImages = images ?? own.data ?? null
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      {creatorId !== null && creatorImages !== null ? (
        <RecordGallery
          sectionId='section-creator-images'
          title="The god's images"
          nodeId={creatorId}
          name={name}
          images={creatorImages}
          prompt={prompt}
          onSavePrompt={onSavePrompt}
        />
      ) : (
        creatorId !== null && <Skeleton className='h-textarea w-full' />
      )}
      {worldId !== null && world && (
        <RecordGallery
          sectionId='section-creator-world-images'
          title={`${world.name}: map background, landscape and cover`}
          nodeId={worldId}
          name={world.name}
          images={worldImages.data ?? []}
          prompt={null}
          emptyText='Upload or generate a landscape for this world.'
        />
      )}
    </div>
  )
}
