import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { KIN } from './families'

export function KinSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={KIN} />
}
