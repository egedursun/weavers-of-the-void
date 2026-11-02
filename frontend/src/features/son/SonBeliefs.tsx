import { BeliefSection } from '@/features/pantheon/BeliefSection'
import { type FolkView } from '@/features/pantheon/api'

export function SonBeliefs({
  views,
  sonId,
  name,
}: {
  views: FolkView[]
  sonId: number
  name: string
}) {
  return <BeliefSection views={views} sonId={sonId} godName={name} />
}
