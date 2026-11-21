import { IntroNote } from '@/components/domain'
import { AgrarianSection } from '@/features/agrarian/AgrarianSection'
import { ArcanaSection } from '@/features/arcana/ArcanaSection'
import { MythicSection } from '@/features/arcana/MythicSection'
import { ArsenalSection } from '@/features/arsenal/ArsenalSection'
import { SourceTrustSection } from '@/features/beliefTrust/SourceTrustSection'
import { BelongingSection } from '@/features/belonging/BelongingSection'
import { BiologySection } from '@/features/biology/BiologySection'
import { BodySystemsSection } from '@/features/bodySystems/BodySystemsSection'
import { ChildhoodSection } from '@/features/childhood/ChildhoodSection'
import { CityRulesSection } from '@/features/cityRules/CityRulesSection'
import { ClimesSection } from '@/features/climes/ClimesSection'
import { CollectiveSection } from '@/features/collective/CollectiveSection'
import { CommerceSection } from '@/features/commerce/CommerceSection'
import { ConditionKindsSection } from '@/features/conditionKinds/ConditionKindsSection'
import { CouplingsSection } from '@/features/couplings/CouplingsSection'
import { CraftsSection } from '@/features/crafts/CraftsSection'
import { CreatorBondsSection } from '@/features/creatorBonds/CreatorBondsSection'
import { CreatureGroupsSection } from '@/features/creatureGroups/CreatureGroupsSection'
import { CustomsSection } from '@/features/customs/CustomsSection'
import { CyclesSection } from '@/features/cycles/CyclesSection'
import { DailyLifeSection } from '@/features/daily/DailyLifeSection'
import { DeparturesSection } from '@/features/departures/DeparturesSection'
import { DiseaseAgentsSection } from '@/features/diseaseAgents/DiseaseAgentsSection'
import { GodCouncilSection } from '@/features/divine/CouncilOrderPanel'
import { DivineConceptionsSection } from '@/features/divineConceptions/DivineConceptionsSection'
import { DivinePowersSection } from '@/features/divinePowers/DivinePowersSection'
import { DominionSection } from '@/features/dominion/DominionSection'
import { EndowmentsSection } from '@/features/endowments/EndowmentsSection'
import { TechErasSection } from '@/features/eras/TechErasSection'
import { EvolutionSection } from '@/features/evolution/EvolutionSection'
import { FamilySection } from '@/features/family/FamilySection'
import { FertilitySection } from '@/features/fertility/FertilitySection'
import { FolkKnowledgeSection } from '@/features/folkKnowledge/FolkKnowledgeSection'
import { FolkwaysSection } from '@/features/folkways/FolkwaysSection'
import { ForecastingSection } from '@/features/forecasting/ForecastingSection'
import { FortuneSection } from '@/features/fortune/FortuneSection'
import { GatheringsSection } from '@/features/gatherings/GatheringsSection'
import { HistoriesSection } from '@/features/gatherings/HistoriesSection'
import { GovernanceSection } from '@/features/governance/GovernanceSection'
import { GraveGoodsSection } from '@/features/graveGoods/GraveGoodsSection'
import { HonoursSection } from '@/features/honours/HonoursSection'
import { InterpretationSection } from '@/features/interpretation/InterpretationSection'
import { InterworldSection } from '@/features/interworld/InterworldSection'
import { KinSection } from '@/features/kin/KinSection'
import { WaysOfLifeSection } from '@/features/kinds/WaysOfLifeSection'
import { LabourSection } from '@/features/labour/LabourSection'
import { LawDepthSection } from '@/features/lawDepth/LawDepthSection'
import { LeaderCultsSection } from '@/features/leaderCults/LeaderCultsSection'
import { LeaguesSection } from '@/features/leagues/LeaguesSection'
import { FossilSection } from '@/features/lifecycle/FossilSection'
import { GroundsSection } from '@/features/lifecycle/GroundsSection'
import { LifecycleSection } from '@/features/lifecycle/LifecycleSection'
import { WorldEndSection } from '@/features/lifecycle/WorldEndSection'
import { LivingSection } from '@/features/living/LivingSection'
import { MadeKindsSection } from '@/features/madeKinds/MadeKindsSection'
import { MarketStructureSection } from '@/features/marketStructure/MarketStructureSection'
import { MeansSection } from '@/features/means/MeansSection'
import { MediaSection } from '@/features/media/MediaSection'
import { AugmentsSection } from '@/features/minds/AugmentsSection'
import { MadeWorldSection } from '@/features/minds/MadeWorldSection'
import { MindSeatSection } from '@/features/minds/MindSeatSection'
import { NetworkSection } from '@/features/minds/NetworkSection'
import { MoneyPolicySection } from '@/features/moneyPolicy/MoneyPolicySection'
import { MoodSection } from '@/features/mood/MoodSection'
import { NatureSection } from '@/features/nature/NatureSection'
import { NumbersSection } from '@/features/numbers/NumbersSection'
import { OccupationSection } from '@/features/occupation/OccupationSection'
import { OperationsSection } from '@/features/operations/OperationsSection'
import { OrdersSection } from '@/features/orders/OrdersSection'
import { PantheonSection } from '@/features/pantheonLife/PantheonSection'
import { PersonHonoursSection } from '@/features/personHonours/PersonHonoursSection'
import { PlantBodiesSection } from '@/features/plantBodies/PlantBodiesSection'
import { HiddenTruthsSection } from '@/features/powers/HiddenTruthsSection'
import { MagicSystemsSection } from '@/features/powers/MagicSystemsSection'
import { PowersSection } from '@/features/powers/PowersSection'
import { SourcesSection } from '@/features/powers/SourcesSection'
import { PracticesSection } from '@/features/practices/PracticesSection'
import { PrehistorySection } from '@/features/prehistory/PrehistorySection'
import { ProfessionsSection } from '@/features/professions/ProfessionsSection'
import { ProtectedNatureSection } from '@/features/protectedNature/ProtectedNatureSection'
import { PublicWorksSection } from '@/features/publicWorks/PublicWorksSection'
import { PursuitsSection } from '@/features/pursuits/PursuitsSection'
import { ReckoningSection } from '@/features/reckoning/ReckoningSection'
import { HistorySection } from '@/features/records/HistorySection'
import { ReferendumsSection } from '@/features/referendums/ReferendumsSection'
import { RegimeSection } from '@/features/regime/RegimeSection'
import { RestorationsSection } from '@/features/restoration/RestorationsSection'
import { SacredSection } from '@/features/sacred/SacredSection'
import { SeaWavesSection } from '@/features/seaWaves/SeaWavesSection'
import { SecuritiesSection } from '@/features/securities/SecuritiesSection'
import { SpaceWeatherSection } from '@/features/spaceWeather/SpaceWeatherSection'
import { SpeechSection } from '@/features/speech/SpeechSection'
import { TalesSection } from '@/features/tales/TalesSection'
import { TechnologySection } from '@/features/technology/TechnologySection'
import { TheDeadSection } from '@/features/the-dead/TheDeadSection'
import { TonguesSection } from '@/features/tongues/TonguesSection'
import { TransformSection } from '@/features/transform/TransformSection'
import { TypedModelsSection } from '@/features/typedModels/TypedModelsSection'
import { UnionsSection } from '@/features/unions/UnionsSection'
import { UrbanSection } from '@/features/urban/UrbanSection'
import { WaterIceSection } from '@/features/waterIce/WaterIceSection'
import { WorldViewSection } from '@/features/worldview/WorldViewSection'
import { YouthSection } from '@/features/youth/YouthSection'
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
        <IntroNote>
          A made type is a design its makers draw, cook, forge, field or build.
          It has no mind, augments, networks, household, purse, lands, offices,
          rule, magic or tongue of its own, so those sections stay with the
          beings and things who make and use it. Every record tied to it is
          still listed and editable under Every record.
        </IntroNote>
        <EntityMechanics
          nodeId={nodeId}
          statKeys={statKeys}
          readOnlyReason={readOnlyReason}
        />
        <NameSection nodeId={nodeId} />
        <BondsSection nodeId={nodeId} />
        <RenownSection nodeId={nodeId} />
        <HistoriesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
        <HistorySection nodeId={nodeId} readOnlyReason={readOnlyReason} />
        <MythicSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
        <CouplingsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
        <WaysOfLifeSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
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
      <MindSeatSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <AugmentsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <NetworkSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <MadeWorldSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <PowersSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <SourcesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <MagicSystemsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <HiddenTruthsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <LivingSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <FortuneSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <TechnologySection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <DivinePowersSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <CreatorBondsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <PantheonSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <WaysOfLifeSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <TypedModelsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <SourceTrustSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <GodCouncilSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
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
      <HistorySection nodeId={nodeId} readOnlyReason={readOnlyReason} />
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
      <DailyLifeSection nodeId={nodeId} />
      <KinSection nodeId={nodeId} />
      <ChildhoodSection nodeId={nodeId} />
      <UnionsSection nodeId={nodeId} />
      <YouthSection nodeId={nodeId} />
      <NumbersSection nodeId={nodeId} />
      <CommerceSection nodeId={nodeId} />
      <PublicWorksSection nodeId={nodeId} />
      <MediaSection nodeId={nodeId} />
      <GovernanceSection nodeId={nodeId} />
      <MarketStructureSection nodeId={nodeId} />
      <LabourSection nodeId={nodeId} />
      <MoneyPolicySection nodeId={nodeId} />
      <SecuritiesSection nodeId={nodeId} />
      <LeaguesSection nodeId={nodeId} />
      <DeparturesSection nodeId={nodeId} />
      <ReferendumsSection nodeId={nodeId} />
      <ReckoningSection nodeId={nodeId} />
      <LeaderCultsSection nodeId={nodeId} />
      <RestorationsSection nodeId={nodeId} />
      <OccupationSection nodeId={nodeId} />
      <ArsenalSection nodeId={nodeId} />
      <InterworldSection nodeId={nodeId} />
      <CityRulesSection nodeId={nodeId} />
      <ProtectedNatureSection nodeId={nodeId} />
      <FamilySection nodeId={nodeId} />
      <MoodSection nodeId={nodeId} />
      <InterpretationSection nodeId={nodeId} />
      <GraveGoodsSection nodeId={nodeId} />
      <ConditionKindsSection nodeId={nodeId} />
      <FertilitySection nodeId={nodeId} />
      <PersonHonoursSection nodeId={nodeId} />
      <SeaWavesSection nodeId={nodeId} />
      <CreatureGroupsSection nodeId={nodeId} />
      <DivineConceptionsSection nodeId={nodeId} />
      <SpeechSection nodeId={nodeId} />
      <FolkKnowledgeSection nodeId={nodeId} />
      <EndowmentsSection nodeId={nodeId} />
      <TheDeadSection nodeId={nodeId} />
      <PracticesSection nodeId={nodeId} />
      <ProfessionsSection nodeId={nodeId} />
      <ForecastingSection nodeId={nodeId} />
      <PlantBodiesSection nodeId={nodeId} />
      <BodySystemsSection nodeId={nodeId} />
      <DiseaseAgentsSection nodeId={nodeId} />
      <WaterIceSection nodeId={nodeId} />
      <SpaceWeatherSection nodeId={nodeId} />
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
      <CouplingsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <FossilSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <GroundsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <MadeKindsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      <RecordRowsSection nodeId={nodeId} />
    </>
  )
}
