import { ArcanaSection } from '@/features/arcana/ArcanaSection'
import { MythicSection } from '@/features/arcana/MythicSection'
import { CollectiveSection } from '@/features/collective/CollectiveSection'
import { CyclesSection } from '@/features/cycles/CyclesSection'
import { DominionSection } from '@/features/dominion/DominionSection'
import { EvolutionSection } from '@/features/evolution/EvolutionSection'
import { GatheringsSection } from '@/features/gatherings/GatheringsSection'
import { HistoriesSection } from '@/features/gatherings/HistoriesSection'
import { LawDepthSection } from '@/features/lawDepth/LawDepthSection'
import { RegimeSection } from '@/features/regime/RegimeSection'
import { TonguesSection } from '@/features/tongues/TonguesSection'
import { UrbanSection } from '@/features/urban/UrbanSection'
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
      <TonguesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <EvolutionSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <UrbanSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <LawDepthSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <CollectiveSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <CyclesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <RegimeSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <RecordRowsSection nodeId={nodeId} />
    </>
  )
}
