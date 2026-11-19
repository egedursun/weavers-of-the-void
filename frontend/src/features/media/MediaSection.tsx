import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { MEDIA } from './families'

export function MediaSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={MEDIA} />
}
