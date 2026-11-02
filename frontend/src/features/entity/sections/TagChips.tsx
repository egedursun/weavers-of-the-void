import { Badge } from '@/components/ui/badge'
import { humanize } from '../actions/schema'
import { useCatalogue } from '../api/queries'
import { type EntityDetail } from '../api/types'

type Tone =
  'default' | 'secondary' | 'destructive' | 'warning' | 'success' | 'outline'

const FLAG_TONE: Partial<Record<string, Tone>> = {
  legendary: 'default',
  wonder: 'default',
  chosen: 'default',
  prophet: 'default',
  deified: 'default',
  cursed: 'destructive',
  bloodline_curse: 'destructive',
  exile: 'destructive',
  oathbreaker: 'destructive',
  cosmic_plague: 'destructive',
  outer_cult: 'destructive',
  godless: 'warning',
  ruin: 'warning',
  lost: 'warning',
  depleted: 'warning',
  protected: 'success',
  protected_from_ruin: 'success',
  protected_from_disaster: 'success',
  agent_selected: 'success',
  immortal: 'success',
}

const HIDDEN_TAG = /^(branch|law|thread|war|corpse):/

export function TagChips({ detail }: { detail: EntityDetail }) {
  const catalogue = useCatalogue()
  const traitLabel = (key: string) =>
    catalogue.data?.creature_traits.find((item) => item.key === key)?.label ??
    humanize(key)
  const tags = detail.tags.filter((tag) => !HIDDEN_TAG.test(tag))
  return (
    <>
      {detail.flags.map((flag) => (
        <Badge key={`flag-${flag}`} variant={FLAG_TONE[flag] ?? 'secondary'}>
          {humanize(flag)}
        </Badge>
      ))}
      {detail.traits.map((trait) => (
        <Badge key={`trait-${trait}`} variant='outline'>
          {traitLabel(trait)}
        </Badge>
      ))}
      {tags.map((tag) => (
        <Badge key={`tag-${tag}`} variant='outline'>
          {humanize(tag.replace(/:/g, ' '))}
        </Badge>
      ))}
    </>
  )
}
