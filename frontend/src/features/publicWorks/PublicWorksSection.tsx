import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { PUBLIC_WORKS } from './families'

export function PublicWorksSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={PUBLIC_WORKS} />
}
