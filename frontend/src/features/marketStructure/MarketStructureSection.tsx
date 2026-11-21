import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { MARKET_STRUCTURE } from './families'

export function MarketStructureSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={MARKET_STRUCTURE} />
}
