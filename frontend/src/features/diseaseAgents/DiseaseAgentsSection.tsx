import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { DISEASE_AGENTS } from './families'

export function DiseaseAgentsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={DISEASE_AGENTS} />
}
