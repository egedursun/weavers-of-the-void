import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { FORECASTING } from './families'

export function ForecastingSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={FORECASTING} />
}
