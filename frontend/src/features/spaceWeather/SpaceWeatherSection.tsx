import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { SPACE_WEATHER } from './families'

export function SpaceWeatherSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={SPACE_WEATHER} />
}
