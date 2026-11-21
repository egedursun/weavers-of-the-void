import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { ARSENAL } from './families'

export function ArsenalSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={ARSENAL} />
}
