import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { LABOUR } from './families'

export function LabourSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={LABOUR} />
}
