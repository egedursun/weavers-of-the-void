import { Coins, Pickaxe, Pill } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Skeleton } from '@/components/ui/skeleton'
import { EntityLink, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { CosmicActionButton } from './CosmicActionButton'
import { type AddictionView, useAddictions } from './api'
import { useCosmicAction } from './useCosmicAction'

type Cure = { entityId: number; resourceId: number }

function useCureAddiction() {
  return useCosmicAction({
    run: ({ entityId, resourceId }: Cure) =>
      unwrap(
        api.POST('/api/actions/addiction:cure', {
          body: { entity_id: entityId, resource_id: resourceId },
        })
      ),
  })
}

export function AddictionList({
  addictions,
  showCommunity,
}: {
  addictions: AddictionView[]
  showCommunity: boolean
}) {
  const cure = useCureAddiction()
  return (
    <ul className='flex min-w-0 flex-col gap-2'>
      {addictions.map((item) => {
        const key = `${item.community.id}-${item.resource.id}`
        const busy =
          cure.isPending &&
          cure.variables?.entityId === item.community.id &&
          cure.variables.resourceId === item.resource.id
        return (
          <li key={key} className='flex min-w-0 flex-wrap items-center gap-2'>
            {showCommunity && (
              <EntityLink kind='entity' id={String(item.community.id)}>
                {item.community.name}
              </EntityLink>
            )}
            <Text as='span'>{showCommunity ? 'craves' : 'Craves'}</Text>
            <EntityLink kind='entity' id={String(item.resource.id)}>
              {item.resource.name}
            </EntityLink>
            <Muted as='span' variant='caption'>
              {item.withdrawal_since_epoch !== null
                ? `in withdrawal since epoch ${item.withdrawal_since_epoch}`
                : `addicted since epoch ${item.addicted_since_epoch ?? '?'}`}
            </Muted>
            <CosmicActionButton
              actionId='addiction:cure'
              label='Cure'
              icon={Pill}
              size='sm'
              pending={busy}
              onRun={() =>
                cure.mutate({
                  entityId: item.community.id,
                  resourceId: item.resource.id,
                })
              }
            />
          </li>
        )
      })}
    </ul>
  )
}

export function EconomyControls() {
  const addictions = useAddictions()
  const resources = useCosmicAction({
    run: () => unwrap(api.POST('/api/actions/economy:resources')),
  })
  const cosmic = useCosmicAction({
    run: () => unwrap(api.POST('/api/actions/economy:cosmic')),
  })
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Muted>
        Both run on their own every epoch; run one now to see its effect at
        once.
      </Muted>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <CosmicActionButton
          actionId='economy:resources'
          label='Run the resource mechanics'
          icon={Pickaxe}
          pending={resources.isPending}
          onRun={() => resources.mutate()}
        />
        <CosmicActionButton
          actionId='economy:cosmic'
          label='Run the cosmic economy'
          icon={Coins}
          pending={cosmic.isPending}
          onRun={() => cosmic.mutate()}
        />
      </div>
      <Muted variant='caption'>
        Resource mechanics wear down decaying stores, bind owners to addictive
        ones and let living resources make demands. The cosmic economy claims
        and opens deposits, moves markets and sends pirates after busy roads.
      </Muted>
      <div className='flex min-w-0 flex-col gap-2'>
        <Label variant='overline'>Addicted communities</Label>
        {addictions.isPending && <Skeleton className='h-control-lg w-full' />}
        {addictions.isError && (
          <Text tone='destructive'>{addictions.error.message}</Text>
        )}
        {addictions.data &&
          (addictions.data.length === 0 ? (
            <Muted>No community is bound to a resource.</Muted>
          ) : (
            <AddictionList addictions={addictions.data} showCommunity />
          ))}
      </div>
    </div>
  )
}

export function CommunityAddictions({ entityId }: { entityId: number }) {
  const addictions = useAddictions(entityId)
  if (addictions.isError)
    return <Text tone='destructive'>{addictions.error.message}</Text>
  if (!addictions.data || addictions.data.length === 0) return null
  return (
    <Section
      id='section-addictions'
      title='Cravings'
      description='It has held an addictive resource too long; without it, it withers. Withdrawal may pass on its own, or you can cure it.'
    >
      <AddictionList addictions={addictions.data} showCommunity={false} />
    </Section>
  )
}
