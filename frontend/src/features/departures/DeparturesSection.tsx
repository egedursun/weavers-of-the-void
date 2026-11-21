import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { DEPARTURES } from './families'

export function DeparturesSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={DEPARTURES} />
}
