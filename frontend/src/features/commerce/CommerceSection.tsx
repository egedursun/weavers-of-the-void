import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { COMMERCE } from './families'

export function CommerceSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={COMMERCE} />
}
