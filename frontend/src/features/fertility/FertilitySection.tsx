import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { FERTILITY } from './families'

export function FertilitySection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={FERTILITY} />
}
