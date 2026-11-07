import { AspirationsSection } from './AspirationsSection'
import { BondsSection } from './BondsSection'
import { EntityMechanics } from './EntityMechanics'
import { EthicsSection } from './EthicsSection'
import { FeelingsSection } from './FeelingsSection'
import { FinanceSection } from './FinanceSection'
import { HomeSection } from './HomeSection'
import { LineageSection } from './LineageSection'
import { MindSplitSection } from './MindSplitSection'
import { RecordRowsSection } from './RecordRowsSection'
import { RenownSection } from './RenownSection'
import { TastesSection } from './TastesSection'
import { WorksSection } from './WorksSection'

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
      <BondsSection nodeId={nodeId} />
      <RenownSection nodeId={nodeId} />
      <WorksSection nodeId={nodeId} />
      <FinanceSection nodeId={nodeId} />
      <LineageSection nodeId={nodeId} />
      <HomeSection nodeId={nodeId} />
      <RecordRowsSection nodeId={nodeId} />
    </>
  )
}
