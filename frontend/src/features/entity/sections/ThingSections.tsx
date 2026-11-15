import { Muted } from '@/components/typography'
import { AgrarianSection } from '@/features/agrarian/AgrarianSection'
import { ArcanaSection } from '@/features/arcana/ArcanaSection'
import { MythicSection } from '@/features/arcana/MythicSection'
import { BelongingSection } from '@/features/belonging/BelongingSection'
import { BiologySection } from '@/features/biology/BiologySection'
import { ClimesSection } from '@/features/climes/ClimesSection'
import { CollectiveSection } from '@/features/collective/CollectiveSection'
import { CraftsSection } from '@/features/crafts/CraftsSection'
import { CustomsSection } from '@/features/customs/CustomsSection'
import { CyclesSection } from '@/features/cycles/CyclesSection'
import { DominionSection } from '@/features/dominion/DominionSection'
import { TechErasSection } from '@/features/eras/TechErasSection'
import { EvolutionSection } from '@/features/evolution/EvolutionSection'
import { FolkwaysSection } from '@/features/folkways/FolkwaysSection'
import { GatheringsSection } from '@/features/gatherings/GatheringsSection'
import { HistoriesSection } from '@/features/gatherings/HistoriesSection'
import { HonoursSection } from '@/features/honours/HonoursSection'
import { LawDepthSection } from '@/features/lawDepth/LawDepthSection'
import { FossilSection } from '@/features/lifecycle/FossilSection'
import { GroundsSection } from '@/features/lifecycle/GroundsSection'
import { LifecycleSection } from '@/features/lifecycle/LifecycleSection'
import { WorldEndSection } from '@/features/lifecycle/WorldEndSection'
import { MadeKindsSection } from '@/features/madeKinds/MadeKindsSection'
import { MeansSection } from '@/features/means/MeansSection'
import { NatureSection } from '@/features/nature/NatureSection'
import { OperationsSection } from '@/features/operations/OperationsSection'
import { OrdersSection } from '@/features/orders/OrdersSection'
import { PrehistorySection } from '@/features/prehistory/PrehistorySection'
import { PursuitsSection } from '@/features/pursuits/PursuitsSection'
import { RegimeSection } from '@/features/regime/RegimeSection'
import { SacredSection } from '@/features/sacred/SacredSection'
import { TalesSection } from '@/features/tales/TalesSection'
import { TonguesSection } from '@/features/tongues/TonguesSection'
import { TransformSection } from '@/features/transform/TransformSection'
import { UrbanSection } from '@/features/urban/UrbanSection'
import { WorldViewSection } from '@/features/worldview/WorldViewSection'
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
import { type ThingScope } from './thingScope'

export function ThingSections({
  nodeId,
  statKeys = [],
  readOnlyReason = null,
  scope = 'every',
}: {
  nodeId: number
  statKeys?: string[]
  readOnlyReason?: string | null
  scope?: ThingScope
}) {
  if (scope === 'made')
    return (
      <>
        <Muted variant='caption'>
          A made type is a design its makers draw, cook, forge, field or build.
          It has no mind, household, purse, lands, offices, rule, magic or
          tongue of its own, so those sections stay with the beings who make and
          use it. Every record tied to it is still listed and editable under
          Every record.
        </Muted>
        <EntityMechanics
          nodeId={nodeId}
          statKeys={statKeys}
          readOnlyReason={readOnlyReason}
        />
        <NameSection nodeId={nodeId} />
        <BondsSection nodeId={nodeId} />
        <RenownSection nodeId={nodeId} />
        <HistoriesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
        <MythicSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
        <RecordRowsSection nodeId={nodeId} />
      </>
    )
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
      <AgrarianSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <OperationsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <SacredSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <PursuitsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <TalesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <FolkwaysSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <CustomsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <CraftsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <ClimesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <BelongingSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <TechErasSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <NatureSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <MeansSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <OrdersSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <HonoursSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <WorldViewSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <BiologySection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <LifecycleSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <WorldEndSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <PrehistorySection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <TransformSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <FossilSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <GroundsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <MadeKindsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <RecordRowsSection nodeId={nodeId} />
    </>
  )
}
