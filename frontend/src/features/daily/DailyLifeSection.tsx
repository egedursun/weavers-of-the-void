import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { DAILY_LIFE } from './families'

export function DailyLifeSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={DAILY_LIFE} />
}
