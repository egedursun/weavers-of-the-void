import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { SECURITIES } from './families'

export function SecuritiesSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={SECURITIES} />
}
