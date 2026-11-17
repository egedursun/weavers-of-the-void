import { useOlderLines } from '@/features/chronicle/api'
import { ChronicleList } from '@/features/pantheon/ChronicleList'
import { type ChronicleLine } from '@/features/pantheon/api'

export function ForeignGodChronicle({
  godId,
  lines,
  total,
}: {
  godId: number
  lines: ChronicleLine[]
  total: number
}) {
  const older = useOlderLines('foreign_god', godId, lines.length, total)
  return (
    <ChronicleList
      title='In the chronicle'
      description='Records about this god and their world, newest first.'
      lines={lines}
      older={older}
      emptyTitle='Not in the chronicle yet'
      emptyText='The name does not appear in the chronicle yet.'
    />
  )
}
