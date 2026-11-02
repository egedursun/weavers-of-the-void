import { ChronicleList } from '@/features/pantheon/ChronicleList'
import { type ChronicleLine } from '@/features/pantheon/api'

export function CreatorTraces({ traces }: { traces: ChronicleLine[] }) {
  return (
    <ChronicleList
      title='Traces of the god'
      description='Chronicle entries where the Creator acted, newest first.'
      lines={traces}
      emptyTitle='No trace yet'
      emptyText='Your deeds are written here as the chronicle records them.'
    />
  )
}
