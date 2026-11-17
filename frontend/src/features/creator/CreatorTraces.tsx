import { useOlderLines } from '@/features/chronicle/api'
import { ChronicleList } from '@/features/pantheon/ChronicleList'
import { type ChronicleLine } from '@/features/pantheon/api'

export function CreatorTraces({
  traces,
  total,
}: {
  traces: ChronicleLine[]
  total: number
}) {
  const older = useOlderLines('creator', null, traces.length, total)
  return (
    <ChronicleList
      title='Traces of the god'
      description='Chronicle entries where the Creator acted, newest first.'
      lines={traces}
      older={older}
      emptyTitle='No trace yet'
      emptyText='Your deeds are written here as the chronicle records them.'
    />
  )
}
