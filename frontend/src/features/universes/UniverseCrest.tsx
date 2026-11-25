import { cn } from '@/lib/utils'
import { GEM_CLASS } from '@/components/ui/ornate'
import { Picture, Sigil } from '@/components/domain'
import { coverUrl } from './api'
import { type UniverseSummary } from './types'
import { crestTone } from './universeLook'

type CrestSize = 'xs' | 'sm' | 'md' | 'lg'

const CREST_SIZE: Record<CrestSize, string> = {
  xs: 'size-icon-lg p-0.5',
  sm: 'size-control-lg p-1',
  md: 'size-portrait-lg p-1.5',
  lg: 'size-portrait-xl p-2 @xs/library:size-portrait-2xl @xs/library:p-3',
}

export function UniverseCrest({
  name,
  size = 'md',
}: {
  name: string
  size?: CrestSize
}) {
  return (
    <span
      data-domain='universe-crest'
      className={cn('medallion', CREST_SIZE[size], GEM_CLASS[crestTone(name)])}
    >
      <Sigil seed={name} />
    </span>
  )
}

export function UniverseCover({ universe }: { universe: UniverseSummary }) {
  const crest = (
    <span
      role='img'
      aria-label={`The crest of ${universe.name}`}
      className={cn(
        'flex size-full items-center justify-center bg-linear-to-br from-primary/15 via-brand-violet/12 to-brand-magenta/10',
        GEM_CLASS[crestTone(universe.name)]
      )}
    >
      <UniverseCrest name={universe.name} size='lg' />
    </span>
  )
  return (
    <Picture
      src={coverUrl(universe)}
      alt={`The cover of ${universe.name}`}
      loading='lazy'
      decoding='async'
      className='size-full object-cover'
      fallback={crest}
    />
  )
}
