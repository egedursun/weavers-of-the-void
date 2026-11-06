import { Sunrise } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EntityLink, Section, StatBar, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { type SonRecord } from '@/features/pantheon/api'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { humanize } from '@/features/pantheon/labels'
import { SiblingSchemes } from './SiblingSchemes'
import { useResurrection } from './api'

export function DeadSonPanel({ son }: { son: SonRecord }) {
  const rule = useRuleLookup()
  const { reason } = useGodGate()
  const cost = rule('balance.resurrection')
  const devotion = rule('death.resurrection_devotion_required')
  const riteChance = rule('death.rite_chance')
  const sacrificeChance = rule('death.sacrifice_chance')
  const rite = useResurrection(son.id)
  const deathEpoch = rite.data?.death_epoch ?? son.death_epoch
  const deathCause = rite.data?.death_cause ?? son.death_cause
  const corpse = rite.data?.corpse ?? null
  const resurrect = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/sons/{son_id}/resurrect', {
          params: { path: { son_id: son.id } },
        })
      ),
    success: 'Death was withdrawn',
  })
  return (
    <Section
      title={
        deathEpoch !== null
          ? `${son.name} died · Epoch ${deathEpoch}`
          : `${son.name} is dead`
      }
      surface='card'
      level={3}
    >
      {rite.isPending && <Skeleton className='h-24 w-full' />}
      {rite.isError && <Text tone='destructive'>{rite.error.message}</Text>}
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        {deathCause && (
          <Badge size='sm' variant='destructive'>
            {humanize(deathCause)}
          </Badge>
        )}
        {rite.data && rite.data.earliest_return_epoch !== null && (
          <Badge
            size='sm'
            variant={rite.data.epochs_remaining === 0 ? 'success' : 'outline'}
          >
            {rite.data.epochs_remaining === 0
              ? 'Can return'
              : `Earliest return in Epoch ${rite.data.earliest_return_epoch}`}
          </Badge>
        )}
        {rite.data && rite.data.epochs_remaining > 0 && (
          <Badge size='sm' variant='outline'>
            {`${rite.data.epochs_remaining} ${rite.data.epochs_remaining === 1 ? 'epoch' : 'epochs'} remaining`}
          </Badge>
        )}
      </div>
      {corpse && (
        <Text>
          Their body lies as bones:{' '}
          <EntityLink kind='entity' id={String(corpse.id)}>
            {corpse.name}
          </EntityLink>
        </Text>
      )}
      {rite.data && (
        <div className='flex min-w-0 flex-col gap-3'>
          <StatBar
            label='Resurrection devotion'
            value={rite.data.devotion}
            max={rite.data.devotion_required}
          />
          {rite.data.orders.length === 0 && (
            <Muted variant='caption'>
              No resurrection cult has formed yet.
            </Muted>
          )}
          {rite.data.orders.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1.5'>
              <Label variant='overline'>Resurrection cults</Label>
              <ul className='flex min-w-0 flex-col gap-1.5'>
                <Paged items={rite.data.orders} as='li'>
                  {(order) => (
                    <li
                      key={order.id}
                      className='flex min-w-0 items-baseline gap-2'
                    >
                      <EntityLink kind='entity' id={String(order.id)}>
                        {order.name}
                      </EntityLink>
                      <Muted as='span' variant='caption'>
                        {`${order.followers} followers · devotion ${order.devotion}`}
                      </Muted>
                    </li>
                  )}
                </Paged>
              </ul>
            </div>
          )}
          {rite.data.loyal_communities.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1.5'>
              <Label variant='overline'>Loyal communities</Label>
              <ul className='flex min-w-0 flex-wrap gap-x-3 gap-y-1'>
                <Paged items={rite.data.loyal_communities} as='li'>
                  {(community) => (
                    <li key={community.id} className='min-w-0'>
                      <EntityLink kind='entity' id={String(community.id)}>
                        {community.name}
                      </EntityLink>
                    </li>
                  )}
                </Paged>
              </ul>
            </div>
          )}
        </div>
      )}
      <Muted>
        {`Loyal followers form a resurrection cult that gathers devotion${devotion !== undefined ? `; at ${devotion} devotion` : '; when it is full'} the rite can bring them back. Rites${riteChance !== undefined ? ` (${riteChance}% per epoch)` : ''} and blood sacrifices${sacrificeChance !== undefined ? ` (${sacrificeChance}%)` : ''} also happen on their own, stronger at their bones; siblings may scheme for their return, and enemies may scatter the bones.`}
      </Muted>
      <SiblingSchemes son={son} />
      <div>
        <ActionButton
          label='Resurrect by your own hand'
          icon={Sunrise}
          variant='default'
          cost={cost}
          rule='balance.resurrection'
          blocked={reason({ cost, world: true })}
          pending={resurrect.isPending}
          onRun={() => resurrect.mutate()}
        />
      </div>
    </Section>
  )
}
