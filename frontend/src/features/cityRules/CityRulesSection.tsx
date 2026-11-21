import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { CITY_RULES } from './families'

export function CityRulesSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={CITY_RULES} />
}
