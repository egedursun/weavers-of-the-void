import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { PERSON_HONOURS } from './families'

export function PersonHonoursSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={PERSON_HONOURS} />
}
