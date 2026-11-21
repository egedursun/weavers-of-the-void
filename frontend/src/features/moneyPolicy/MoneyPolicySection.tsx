import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { MONEY_POLICY } from './families'

export function MoneyPolicySection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={MONEY_POLICY} />
}
