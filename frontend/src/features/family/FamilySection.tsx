import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { FAMILY } from './families'

export function FamilySection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={FAMILY} />
}
