import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { PLANT_BODIES } from './families'

export function PlantBodiesSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={PLANT_BODIES} />
}
