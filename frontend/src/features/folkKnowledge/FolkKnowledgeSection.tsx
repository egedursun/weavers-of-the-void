import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { FOLK_KNOWLEDGE } from './families'

export function FolkKnowledgeSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={FOLK_KNOWLEDGE} />
}
