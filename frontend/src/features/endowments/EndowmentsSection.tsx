import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { ENDOWMENTS } from './families'

export function EndowmentsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={ENDOWMENTS} />
}
