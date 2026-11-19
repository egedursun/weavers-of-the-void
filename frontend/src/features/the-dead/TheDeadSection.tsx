import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { THE_DEAD } from './families'

export function TheDeadSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={THE_DEAD} />
}
