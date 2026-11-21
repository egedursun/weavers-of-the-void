import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { MOOD } from './families'

export function MoodSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={MOOD} />
}
