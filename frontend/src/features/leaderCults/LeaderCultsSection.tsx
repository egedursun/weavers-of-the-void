import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { LEADER_CULTS } from './families'

export function LeaderCultsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={LEADER_CULTS} />
}
