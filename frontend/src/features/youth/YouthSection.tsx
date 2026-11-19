import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { YOUTH } from './families'

export function YouthSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={YOUTH} />
}
