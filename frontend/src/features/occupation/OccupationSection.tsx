import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { OCCUPATION } from './families'

export function OccupationSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={OCCUPATION} />
}
