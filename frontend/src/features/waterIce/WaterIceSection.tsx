import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { WATER_AND_ICE } from './families'

export function WaterIceSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={WATER_AND_ICE} />
}
