import { cn } from '@/lib/utils'
import { GEM_CLASS } from '@/components/ui/ornate'
import { Sigil } from '@/components/domain'
import { crestTone } from '@/features/universes/universeLook'

type CrestSize = 'xs' | 'sm' | 'md'

const CREST_SIZE: Record<CrestSize, string> = {
  xs: 'size-icon-lg p-0.5',
  sm: 'size-control-lg p-1',
  md: 'size-portrait-lg p-1.5',
}

export function WorkspaceCrest({
  name,
  size = 'sm',
}: {
  name: string
  size?: CrestSize
}) {
  return (
    <span
      data-domain='workspace-crest'
      className={cn('medallion', CREST_SIZE[size], GEM_CLASS[crestTone(name)])}
    >
      <Sigil seed={`workspace:${name}`} />
    </span>
  )
}
