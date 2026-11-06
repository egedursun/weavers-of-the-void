import { EntityMechanics } from './EntityMechanics'
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
      <RecordRowsSection nodeId={nodeId} />
    </>
  )
}
