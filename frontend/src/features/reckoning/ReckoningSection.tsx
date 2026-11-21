import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { RECKONING } from './families'

export function ReckoningSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={RECKONING} />
}
