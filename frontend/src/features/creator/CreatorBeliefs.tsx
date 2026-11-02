import { BeliefSection } from '@/features/pantheon/BeliefSection'
import { type FolkView } from '@/features/pantheon/api'

export function CreatorBeliefs({
  views,
  name,
}: {
  views: FolkView[]
  name: string
}) {
  return <BeliefSection views={views} sonId={null} godName={name} />
}
