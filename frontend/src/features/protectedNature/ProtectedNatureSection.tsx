import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { PROTECTED_NATURE } from './families'

export function ProtectedNatureSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={PROTECTED_NATURE} />
}
