import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { CHILDHOOD } from './families'

export function ChildhoodSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={CHILDHOOD} />
}
