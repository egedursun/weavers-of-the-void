import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { UNIONS_AND_BIRTH } from './families'

export function UnionsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={UNIONS_AND_BIRTH} />
}
