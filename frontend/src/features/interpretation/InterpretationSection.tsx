import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { INTERPRETATION } from './families'

export function InterpretationSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={INTERPRETATION} />
}
