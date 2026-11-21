import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { CONDITION_KINDS } from './families'

export function ConditionKindsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={CONDITION_KINDS} />
}
