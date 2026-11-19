import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { SPEECH } from './families'

export function SpeechSection({ nodeId }: { nodeId: number }) {
  return <RecordRowsSection nodeId={nodeId} family={SPEECH} />
}
