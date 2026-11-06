import { AspirationsSection } from './AspirationsSection'
import { EntityMechanics } from './EntityMechanics'
import { EthicsSection } from './EthicsSection'
import { FeelingsSection } from './FeelingsSection'
import { MindSplitSection } from './MindSplitSection'
import { RecordRowsSection } from './RecordRowsSection'
import { TastesSection } from './TastesSection'

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
      <TastesSection nodeId={nodeId} />
      <EthicsSection nodeId={nodeId} />
      <AspirationsSection nodeId={nodeId} />
      <RecordRowsSection nodeId={nodeId} />
    </>
  )
}
