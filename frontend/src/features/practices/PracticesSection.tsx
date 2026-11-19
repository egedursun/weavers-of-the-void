import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { PRACTICES } from './families'

export function PracticesSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={PRACTICES} />
}
