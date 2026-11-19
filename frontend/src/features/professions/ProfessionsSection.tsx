import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { PROFESSIONS } from './families'

export function ProfessionsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={PROFESSIONS} />
}
