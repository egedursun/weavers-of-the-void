import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { BODY_SYSTEMS } from './families'

export function BodySystemsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={BODY_SYSTEMS} />
}
