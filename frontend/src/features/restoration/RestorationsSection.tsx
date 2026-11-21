import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { RESTORATIONS } from './families'

export function RestorationsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={RESTORATIONS} />
}
