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
import { useRecordRows } from './recordRows'
import { type ThingKind, shows } from './sectionHomes'
import { type ThingScope } from './thingScope'

export function ThingSections({
  nodeId,
  kind,
  statKeys = [],
  readOnlyReason = null,
  scope = 'every',
}: {
  nodeId: number
  kind: ThingKind
  statKeys?: string[]
  readOnlyReason?: string | null
  scope?: ThingScope
}) {
  const records = useRecordRows(nodeId)
  const held = new Set((records.data?.tables ?? []).map((table) => table.table))
  const show = (section: string) => shows(section, kind, held)
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
      {show('EntityMechanics') && (
        <EntityMechanics
          nodeId={nodeId}
          statKeys={statKeys}
          readOnlyReason={readOnlyReason}
        />
      )}
      {show('NameSection') && <NameSection nodeId={nodeId} />}
      {show('MindSplitSection') && <MindSplitSection nodeId={nodeId} />}
      {show('MindSeatSection') && (
        <MindSeatSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('AugmentsSection') && (
        <AugmentsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('NetworkSection') && (
        <NetworkSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('MadeWorldSection') && (
        <MadeWorldSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('PowersSection') && (
        <PowersSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('SourcesSection') && (
        <SourcesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('MagicSystemsSection') && (
        <MagicSystemsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('HiddenTruthsSection') && (
        <HiddenTruthsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('LivingSection') && (
        <LivingSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('FortuneSection') && (
        <FortuneSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('TechnologySection') && (
        <TechnologySection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('DivinePowersSection') && (
        <DivinePowersSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('CreatorBondsSection') && (
        <CreatorBondsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('PantheonSection') && (
        <PantheonSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('WaysOfLifeSection') && (
        <WaysOfLifeSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('TypedModelsSection') && (
        <TypedModelsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('SourceTrustSection') && (
        <SourceTrustSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('GodCouncilSection') && (
        <GodCouncilSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('FeelingsSection') && <FeelingsSection nodeId={nodeId} />}
      {show('TastesSection') && <TastesSection nodeId={nodeId} />}
      {show('EthicsSection') && <EthicsSection nodeId={nodeId} />}
      {show('AspirationsSection') && <AspirationsSection nodeId={nodeId} />}
      {show('BondsSection') && <BondsSection nodeId={nodeId} />}
      {show('RenownSection') && <RenownSection nodeId={nodeId} />}
      {show('WorksSection') && <WorksSection nodeId={nodeId} />}
      {show('FinanceSection') && <FinanceSection nodeId={nodeId} />}
      {show('LineageSection') && <LineageSection nodeId={nodeId} />}
      {show('HomeSection') && <HomeSection nodeId={nodeId} />}
      {show('IntrigueSection') && <IntrigueSection nodeId={nodeId} />}
      {show('CorrespondenceSection') && (
        <CorrespondenceSection nodeId={nodeId} />
      )}
      {show('TitlesSection') && <TitlesSection nodeId={nodeId} />}
      {show('EstatesSection') && <EstatesSection nodeId={nodeId} />}
      {show('JusticeSection') && <JusticeSection nodeId={nodeId} />}
      {show('StatecraftSection') && <StatecraftSection nodeId={nodeId} />}
      {show('AffairsSection') && <AffairsSection nodeId={nodeId} />}
      {show('GatheringsSection') && (
        <GatheringsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('HistoriesSection') && (
        <HistoriesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('HistorySection') && (
        <HistorySection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('DominionSection') && (
        <DominionSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('ArcanaSection') && (
        <ArcanaSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('MythicSection') && (
        <MythicSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('TonguesSection') && (
        <TonguesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('EvolutionSection') && (
        <EvolutionSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('UrbanSection') && (
        <UrbanSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('LawDepthSection') && (
        <LawDepthSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('CollectiveSection') && (
        <CollectiveSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('CyclesSection') && (
        <CyclesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('RegimeSection') && (
        <RegimeSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('AgrarianSection') && (
        <AgrarianSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('OperationsSection') && (
        <OperationsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('SacredSection') && (
        <SacredSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('PursuitsSection') && (
        <PursuitsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('TalesSection') && (
        <TalesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('FolkwaysSection') && (
        <FolkwaysSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('CustomsSection') && (
        <CustomsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('DailyLifeSection') && <DailyLifeSection nodeId={nodeId} />}
      {show('KinSection') && <KinSection nodeId={nodeId} />}
      {show('ChildhoodSection') && <ChildhoodSection nodeId={nodeId} />}
      {show('UnionsSection') && <UnionsSection nodeId={nodeId} />}
      {show('YouthSection') && <YouthSection nodeId={nodeId} />}
      {show('NumbersSection') && <NumbersSection nodeId={nodeId} />}
      {show('CommerceSection') && <CommerceSection nodeId={nodeId} />}
      {show('PublicWorksSection') && <PublicWorksSection nodeId={nodeId} />}
      {show('MediaSection') && <MediaSection nodeId={nodeId} />}
      {show('GovernanceSection') && <GovernanceSection nodeId={nodeId} />}
      {show('MarketStructureSection') && (
        <MarketStructureSection nodeId={nodeId} />
      )}
      {show('LabourSection') && <LabourSection nodeId={nodeId} />}
      {show('MoneyPolicySection') && <MoneyPolicySection nodeId={nodeId} />}
      {show('SecuritiesSection') && <SecuritiesSection nodeId={nodeId} />}
      {show('LeaguesSection') && <LeaguesSection nodeId={nodeId} />}
      {show('DeparturesSection') && <DeparturesSection nodeId={nodeId} />}
      {show('ReferendumsSection') && <ReferendumsSection nodeId={nodeId} />}
      {show('ReckoningSection') && <ReckoningSection nodeId={nodeId} />}
      {show('LeaderCultsSection') && <LeaderCultsSection nodeId={nodeId} />}
      {show('RestorationsSection') && <RestorationsSection nodeId={nodeId} />}
      {show('OccupationSection') && <OccupationSection nodeId={nodeId} />}
      {show('ArsenalSection') && <ArsenalSection nodeId={nodeId} />}
      {show('InterworldSection') && <InterworldSection nodeId={nodeId} />}
      {show('CityRulesSection') && <CityRulesSection nodeId={nodeId} />}
      {show('ProtectedNatureSection') && (
        <ProtectedNatureSection nodeId={nodeId} />
      )}
      {show('FamilySection') && <FamilySection nodeId={nodeId} />}
      {show('MoodSection') && <MoodSection nodeId={nodeId} />}
      {show('InterpretationSection') && (
        <InterpretationSection nodeId={nodeId} />
      )}
      {show('GraveGoodsSection') && <GraveGoodsSection nodeId={nodeId} />}
      {show('ConditionKindsSection') && (
        <ConditionKindsSection nodeId={nodeId} />
      )}
      {show('FertilitySection') && <FertilitySection nodeId={nodeId} />}
      {show('PersonHonoursSection') && <PersonHonoursSection nodeId={nodeId} />}
      {show('SeaWavesSection') && <SeaWavesSection nodeId={nodeId} />}
      {show('CreatureGroupsSection') && (
        <CreatureGroupsSection nodeId={nodeId} />
      )}
      {show('DivineConceptionsSection') && (
        <DivineConceptionsSection nodeId={nodeId} />
      )}
      {show('SpeechSection') && <SpeechSection nodeId={nodeId} />}
      {show('FolkKnowledgeSection') && <FolkKnowledgeSection nodeId={nodeId} />}
      {show('EndowmentsSection') && <EndowmentsSection nodeId={nodeId} />}
      {show('TheDeadSection') && <TheDeadSection nodeId={nodeId} />}
      {show('PracticesSection') && <PracticesSection nodeId={nodeId} />}
      {show('ProfessionsSection') && <ProfessionsSection nodeId={nodeId} />}
      {show('ForecastingSection') && <ForecastingSection nodeId={nodeId} />}
      {show('PlantBodiesSection') && <PlantBodiesSection nodeId={nodeId} />}
      {show('BodySystemsSection') && <BodySystemsSection nodeId={nodeId} />}
      {show('DiseaseAgentsSection') && <DiseaseAgentsSection nodeId={nodeId} />}
      {show('WaterIceSection') && <WaterIceSection nodeId={nodeId} />}
      {show('SpaceWeatherSection') && <SpaceWeatherSection nodeId={nodeId} />}
      {show('CraftsSection') && (
        <CraftsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('ClimesSection') && (
        <ClimesSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('BelongingSection') && (
        <BelongingSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('TechErasSection') && (
        <TechErasSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('NatureSection') && (
        <NatureSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('MeansSection') && (
        <MeansSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('OrdersSection') && (
        <OrdersSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('HonoursSection') && (
        <HonoursSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('WorldViewSection') && (
        <WorldViewSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('BiologySection') && (
        <BiologySection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('LifecycleSection') && (
        <LifecycleSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('WorldEndSection') && (
        <WorldEndSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('PrehistorySection') && (
        <PrehistorySection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('TransformSection') && (
        <TransformSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('CouplingsSection') && (
        <CouplingsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('FossilSection') && (
        <FossilSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('GroundsSection') && (
        <GroundsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('MadeKindsSection') && (
        <MadeKindsSection nodeId={nodeId} readOnlyReason={readOnlyReason} />
      )}
      {show('RecordRowsSection') && <RecordRowsSection nodeId={nodeId} />}
    </>
  )
}
