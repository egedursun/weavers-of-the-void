import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { SEA_WAVES } from './families'

export function SeaWavesSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={SEA_WAVES} />
}
