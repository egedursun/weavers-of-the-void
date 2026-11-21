import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { INTERWORLD } from './families'

export function InterworldSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={INTERWORLD} />
}
