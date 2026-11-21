import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { CREATURE_GROUPS } from './families'

export function CreatureGroupsSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={CREATURE_GROUPS} />
}
