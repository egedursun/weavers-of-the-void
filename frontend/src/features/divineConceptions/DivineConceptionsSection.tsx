import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { DIVINE_CONCEPTIONS } from './families'

export function DivineConceptionsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={DIVINE_CONCEPTIONS} />
}
