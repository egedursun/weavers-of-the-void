import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { NUMBERS } from './families'

export function NumbersSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={NUMBERS} />
}
