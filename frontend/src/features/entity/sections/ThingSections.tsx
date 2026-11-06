import { EntityMechanics } from './EntityMechanics'
import { FeelingsSection } from './FeelingsSection'
import { MindSplitSection } from './MindSplitSection'
import { RecordRowsSection } from './RecordRowsSection'

export function ThingSections({
  nodeId,
  statKeys = [],
  readOnlyReason = null,
}: {
  nodeId: number
  statKeys?: string[]
  readOnlyReason?: string | null
}) {
  return (
    <>
      <EntityMechanics
        nodeId={nodeId}
        statKeys={statKeys}
        readOnlyReason={readOnlyReason}
      />
      <MindSplitSection nodeId={nodeId} />
      <FeelingsSection nodeId={nodeId} />
      <RecordRowsSection nodeId={nodeId} />
    </>
  )
}
