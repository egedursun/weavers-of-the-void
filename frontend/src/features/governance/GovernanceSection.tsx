import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { GOVERNANCE } from './families'

export function GovernanceSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={GOVERNANCE} />
}
