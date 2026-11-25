import { Link } from '@tanstack/react-router'
import { BookOpen, Compass, Orbit } from 'lucide-react'
import { formatDecimal } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { DomainGlyph, HeroFrame, StatBar } from '@/components/domain'
import { useEntryStack } from '@/components/layout/entry/useEntryStack'
import { Label, Muted, PageTitle } from '@/components/typography'
import { bookUrl } from '@/features/chronicle/api'
import { PortraitGenerateOverlay } from '@/features/images/PortraitGenerateOverlay'
import { useRuleLookup } from '@/features/pantheon/gate'
import {
  FOREIGN_STATUS_BADGE,
  FOREIGN_STATUS_LABEL,
  useLabels,
} from '@/features/pantheon/labels'
import { type ForeignGodDetail } from './api'

export function ForeignGodHero({ detail }: { detail: ForeignGodDetail }) {
  const god = detail.god
  const { domain } = useLabels()
  const rule = useRuleLookup()
  const { open } = useEntryStack()
  const wake = rule('pantheon.sleep_wake_threshold')
  return (
    <HeroFrame>
      <header className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
        <PortraitGenerateOverlay
          nodeId={god.id}
          name={god.name}
          cover={detail.cover ?? null}
          rarity='mythic'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <Label variant='overline'>
            {detail.world
              ? `Foreign god › ${detail.world.name}`
              : 'Foreign god'}
          </Label>
          <PageTitle truncate={2}>
            {god.status === 'dead' ? `† ${god.name}` : god.name}
          </PageTitle>
          {god.title && <Muted>{god.title}</Muted>}
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge size='sm' variant={FOREIGN_STATUS_BADGE[god.status]}>
              {FOREIGN_STATUS_LABEL[god.status]}
            </Badge>
            <Badge size='sm' variant='outline'>
              <DomainGlyph domain={god.domain_primary} />
              {domain(god.domain_primary)}
            </Badge>
            {god.domain_secondary && (
              <Badge size='sm' variant='outline'>
                <DomainGlyph domain={god.domain_secondary} />
                {domain(god.domain_secondary)}
              </Badge>
            )}
            <Badge size='sm' variant='secondary'>{`Power ${god.power}`}</Badge>
            <Badge
              size='sm'
              variant='secondary'
            >{`${formatDecimal(god.faith, 1)} faith`}</Badge>
            <Badge size='sm' variant={god.contacted ? 'outline' : 'secondary'}>
              {god.contacted
                ? 'Made contact with the pantheon'
                : 'No contact yet'}
            </Badge>
            <Badge
              size='sm'
              variant='outline'
            >{`Since Epoch ${god.created_epoch}`}</Badge>
            {god.defeated_epoch !== null && (
              <Badge
                size='sm'
                variant='outline'
              >{`Defeated in Epoch ${god.defeated_epoch}`}</Badge>
            )}
            {god.death_epoch !== null && (
              <Badge
                size='sm'
                variant='destructive'
              >{`Died in Epoch ${god.death_epoch}`}</Badge>
            )}
          </div>
          {god.status === 'asleep' && wake !== undefined && (
            <StatBar
              label='Awakening'
              value={god.awakening_pressure}
              max={wake}
              tone='mythic'
            />
          )}
          {god.status === 'asleep' && god.awakening_average !== null && (
            <Muted variant='caption'>
              {`Stirred by about ${Math.round(god.awakening_average)} each epoch of late`}
            </Muted>
          )}
          {god.status === 'asleep' && (
            <Muted variant='caption'>
              Sons acting on this world, expeditions, great events, new lands
              and relics stir the sleeper; the usual noise of the world does
              not.
            </Muted>
          )}
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button variant='outline' size='sm' asChild>
              <Link to='/cosmos' search={{ world: god.world_id }}>
                <Orbit />
                Show the world in Cosmos
              </Link>
            </Button>
            {detail.world && (
              <Button
                variant='outline'
                size='sm'
                onClick={() =>
                  open({ kind: 'world-guide', id: String(detail.world?.id) })
                }
              >
                <Compass />
                World guide
              </Button>
            )}
            <Button variant='outline' size='sm' asChild>
              <a
                href={`${bookUrl()}#foreign-god-${god.id}`}
                target='_blank'
                rel='noreferrer'
              >
                <BookOpen />
                Open in the book
              </a>
            </Button>
          </div>
        </div>
      </header>
    </HeroFrame>
  )
}
