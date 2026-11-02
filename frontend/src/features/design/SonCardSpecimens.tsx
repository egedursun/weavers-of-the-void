import { useMemo } from 'react'
import { Crown, Sparkles } from 'lucide-react'
import { RARITIES, RARITY_LABEL, type Rarity } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, RarityIcon, Section } from '@/components/domain'
import { RARITY_TEXT_CLASS } from '@/components/domain/rarityClasses'
import { Muted, Text } from '@/components/typography'
import { useWorldState } from '@/features/overview/api'
import { SonCard } from '@/features/pantheon/SonCard'
import { type SonPublic, useSons } from '@/features/pantheon/api'
import { useRevealQueue } from '@/features/pantheon/revealStore'

type Sample = {
  rarity: Rarity
  view: SonPublic
  borrowed: string | null
}

function samplesOf(sons: SonPublic[]): Sample[] {
  const donor = [...sons].sort(
    (left, right) =>
      RARITIES.indexOf(right.son.rarity) - RARITIES.indexOf(left.son.rarity)
  )[0]
  return RARITIES.flatMap((rarity): Sample[] => {
    const own = sons.find((view) => view.son.rarity === rarity)
    if (own) return [{ rarity, view: own, borrowed: null }]
    if (!donor) return []
    return [
      {
        rarity,
        view: { ...donor, son: { ...donor.son, rarity } },
        borrowed: donor.son.name,
      },
    ]
  })
}

export function SonCardSpecimens() {
  const sons = useSons()
  const state = useWorldState()
  const worlds = new Map(
    (state.data?.worlds ?? []).map((world) => [world.id, world.name])
  )
  const samples = useMemo(() => samplesOf(sons.data ?? []), [sons.data])
  const push = useRevealQueue((store) => store.push)
  const play = (list: Sample[]) =>
    push(
      list.map((sample) => ({
        key: `preview-${sample.rarity}-${Date.now()}`,
        sonId: sample.view.son.id,
        kind: 'preview' as const,
        rarity: sample.rarity,
        preview: sample.view,
      }))
    )
  return (
    <Section
      title='Son cards by rarity'
      description='One son of every rarity, exactly as the card opens in the Pantheon.'
      level={3}
      icon={Crown}
      actions={
        samples.length > 0 && (
          <Button variant='outline' size='sm' onClick={() => play(samples)}>
            <Sparkles />
            Play every reveal
          </Button>
        )
      }
    >
      {sons.isPending && <Skeleton className='h-textarea w-full' />}
      {sons.isError && <Text tone='destructive'>{sons.error.message}</Text>}
      {sons.data && samples.length === 0 && (
        <EmptyState
          size='compact'
          icon={Crown}
          title='No sons yet'
          description='Son cards appear here once the world has children.'
        />
      )}
      <div className='grid min-w-0 grid-cols-1 gap-6 lg:grid-cols-2 2xl:grid-cols-3'>
        {samples.map((sample) => (
          <div key={sample.rarity} className='flex min-w-0 flex-col gap-2'>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <RarityIcon
                rarity={sample.rarity}
                className={`size-icon-xl ${RARITY_TEXT_CLASS[sample.rarity]}`}
              />
              <Text as='span' weight='semibold'>
                {RARITY_LABEL[sample.rarity]}
              </Text>
              {sample.borrowed && (
                <Badge size='sm' variant='outline'>
                  Sample
                </Badge>
              )}
              <Button
                variant='ghost'
                size='sm'
                className='ms-auto'
                onClick={() => play([sample])}
              >
                <Sparkles />
                Play the reveal
              </Button>
            </div>
            {sample.borrowed && (
              <Muted variant='caption'>
                {`No ${RARITY_LABEL[sample.rarity].toLowerCase()} son lives yet; ${sample.borrowed} is shown at this rarity.`}
              </Muted>
            )}
            <SonCard
              view={sample.view}
              ready={false}
              interactive={false}
              worldName={
                sample.view.son.current_world_id !== null
                  ? (worlds.get(sample.view.son.current_world_id) ?? null)
                  : null
              }
            />
          </div>
        ))}
      </div>
    </Section>
  )
}
