import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { REFERENDUMS } from './families'

export function ReferendumsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={REFERENDUMS} />
}
