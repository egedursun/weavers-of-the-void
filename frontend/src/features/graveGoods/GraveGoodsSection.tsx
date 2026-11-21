import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { GRAVE_GOODS } from './families'

export function GraveGoodsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={GRAVE_GOODS} />
}
