import { ArcanaSection } from '@/features/arcana/ArcanaSection'
import { MythicSection } from '@/features/arcana/MythicSection'
import { DominionSection } from '@/features/dominion/DominionSection'
import { GatheringsSection } from '@/features/gatherings/GatheringsSection'
import { HistoriesSection } from '@/features/gatherings/HistoriesSection'
import { AffairsSection } from './AffairsSection'
import { AspirationsSection } from './AspirationsSection'
import { BondsSection } from './BondsSection'
import { CorrespondenceSection } from './CorrespondenceSection'
import { EntityMechanics } from './EntityMechanics'
import { EstatesSection } from './EstatesSection'
import { EthicsSection } from './EthicsSection'
import { FeelingsSection } from './FeelingsSection'
import { FinanceSection } from './FinanceSection'
import { HomeSection } from './HomeSection'
import { IntrigueSection } from './IntrigueSection'
import { JusticeSection } from './JusticeSection'
import { LineageSection } from './LineageSection'
import { MindSplitSection } from './MindSplitSection'
import { NameSection } from './NameSection'
import { RecordRowsSection } from './RecordRowsSection'
import { RenownSection } from './RenownSection'
import { StatecraftSection } from './StatecraftSection'
import { TastesSection } from './TastesSection'
import { TitlesSection } from './TitlesSection'
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
      <NameSection nodeId={nodeId} />
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
      <IntrigueSection nodeId={nodeId} />
      <CorrespondenceSection nodeId={nodeId} />
      <TitlesSection nodeId={nodeId} />
      <EstatesSection nodeId={nodeId} />
      <JusticeSection nodeId={nodeId} />
      <StatecraftSection nodeId={nodeId} />
      <AffairsSection nodeId={nodeId} />
      <GatheringsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <HistoriesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <DominionSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <ArcanaSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <MythicSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <RecordRowsSection nodeId={nodeId} />
    </>
  )
}
