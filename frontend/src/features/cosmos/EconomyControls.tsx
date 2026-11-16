import {
  Coins,
  Link2,
  Lock,
  Pencil,
  Pickaxe,
  Pill,
  ShieldCheck,
  ShieldOff,
  Trash2,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EntityLink, Paged, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { RowAction } from '@/features/entity/actions/RowAction'
import { COMMUNITY_TYPES } from '@/features/entity/constants'
import { CosmicActionButton } from './CosmicActionButton'
import {
  type AddictionView,
  type ImmunityView,
  useAddictions,
  useImmunities,
} from './api'
import { useCosmicAction } from './useCosmicAction'

type Cure = { entityId: number; resourceId: number }

const CRAVING_LABELS = {
  entity_id: 'Community',
  resource_id: 'Resource',
  addicted_since_epoch: 'Hooked since epoch',
  withdrawal_since_epoch: 'In withdrawal since epoch',
  owned_epochs: 'Epochs held',
  hold: 'Hold it as it is',
  immune: 'Immune',
  recovered_epoch: 'Freed in epoch',
}

const PAIR_PICKERS = {
  entity_id: { source: 'entity' as const, types: COMMUNITY_TYPES },
  resource_id: { source: 'entity' as const, types: ['resource' as const] },
}

export function BindCraving({ entityId }: { entityId?: number }) {
  const fixed: Record<string, number> =
    entityId === undefined ? {} : { entity_id: entityId }
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      <RowAction
        path='/api/actions/addiction:set'
        icon={Link2}
        label='Bind a craving'
        fixed={fixed}
        hide={['remove']}
        labels={CRAVING_LABELS}
        pickers={PAIR_PICKERS}
        note='The community comes to need the resource; without it, it withers until freed.'
      />
      <RowAction
        path='/api/actions/addiction:immunity'
        icon={ShieldCheck}
        label='Grant immunity'
        fixed={{ ...fixed, immune: true }}
        labels={CRAVING_LABELS}
        pickers={PAIR_PICKERS}
        note='The community can never again be hooked by that resource.'
      />
    </div>
  )
}

export function ImmunityList({
  immunities,
  showCommunity,
}: {
  immunities: ImmunityView[]
  showCommunity: boolean
}) {
  return (
    <ul className='flex min-w-0 flex-col gap-2'>
      <Paged items={immunities} as='li'>
        {(item) => {
          const pair = {
            entity_id: item.community.id,
            resource_id: item.resource.id,
          }
          return (
            <li
              key={`${item.community.id}-${item.resource.id}`}
              className='flex min-w-0 flex-wrap items-center gap-2'
            >
              <ShieldCheck
                aria-hidden='true'
                className='size-icon-xs text-success'
              />
              {showCommunity && (
                <EntityLink kind='entity' id={String(item.community.id)}>
                  {item.community.name}
                </EntityLink>
              )}
              <Text as='span'>
                {showCommunity ? 'is immune to' : 'Immune to'}
              </Text>
              <EntityLink kind='entity' id={String(item.resource.id)}>
                {item.resource.name}
              </EntityLink>
              <Muted as='span' variant='caption'>
                {`since epoch ${item.recovered_epoch}`}
              </Muted>
              <RowAction
                path='/api/actions/addiction:immunity'
                icon={Pencil}
                label='Change when they were freed'
                iconOnly
                fixed={{ ...pair, immune: true }}
                defaults={{ recovered_epoch: item.recovered_epoch }}
                labels={CRAVING_LABELS}
              />
              <RowAction
                path='/api/actions/addiction:immunity'
                icon={ShieldOff}
                label='Take the immunity away'
                iconOnly
                destructive
                fixed={{ ...pair, immune: false }}
                hide={['recovered_epoch']}
                confirm='They can be hooked by it again.'
              />
            </li>
          )
        }}
      </Paged>
    </ul>
  )
}

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
      <Paged items={addictions} as='li'>
        {(item) => {
          const key = `${item.community.id}-${item.resource.id}`
          const pair = {
            entity_id: item.community.id,
            resource_id: item.resource.id,
          }
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
              {item.held && (
                <Badge size='sm' variant='warning'>
                  <Lock />
                  Held
                </Badge>
              )}
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
              <RowAction
                path='/api/actions/addiction:set'
                icon={Pencil}
                label='Reshape the craving'
                iconOnly
                fixed={pair}
                hide={['remove', 'hold']}
                defaults={{
                  addicted_since_epoch: item.addicted_since_epoch,
                  withdrawal_since_epoch: item.withdrawal_since_epoch,
                  owned_epochs: item.owned_epochs,
                }}
                labels={CRAVING_LABELS}
              />
              <RowAction
                path='/api/actions/addiction:set'
                icon={item.held ? Unlock : Lock}
                label={item.held ? 'Let it change again' : 'Hold it as it is'}
                iconOnly
                fixed={{
                  ...pair,
                  hold: !item.held,
                  addicted_since_epoch: item.addicted_since_epoch,
                  withdrawal_since_epoch: item.withdrawal_since_epoch,
                }}
                hide={['remove', 'owned_epochs']}
                confirm={
                  item.held
                    ? 'The craving may deepen, ease or pass again.'
                    : 'Neither withdrawal nor recovery will touch it until you release it.'
                }
              />
              <RowAction
                path='/api/actions/addiction:set'
                icon={Trash2}
                label='Unmake the craving'
                iconOnly
                destructive
                fixed={{ ...pair, remove: true }}
                hide={[
                  'addicted_since_epoch',
                  'withdrawal_since_epoch',
                  'owned_epochs',
                  'hold',
                ]}
                confirm='Unmake it as if it never was; no immunity is left behind.'
              />
            </li>
          )
        }}
      </Paged>
    </ul>
  )
}

export function EconomyControls() {
  const addictions = useAddictions()
  const immunities = useImmunities()
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
        <BindCraving />
      </div>
      {immunities.data && immunities.data.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Immune communities</Label>
          <ImmunityList immunities={immunities.data} showCommunity />
        </div>
      )}
    </div>
  )
}

export function CommunityAddictions({ entityId }: { entityId: number }) {
  const addictions = useAddictions(entityId)
  const immunities = useImmunities(entityId)
  if (addictions.isError)
    return <Text tone='destructive'>{addictions.error.message}</Text>
  if (!addictions.data) return null
  return (
    <Section
      id='section-addictions'
      title='Cravings'
      description='It has held an addictive resource too long; without it, it withers. Withdrawal may pass on its own, or you can cure it.'
    >
      <div className='flex min-w-0 flex-col gap-3'>
        {addictions.data.length === 0 ? (
          <Muted>It craves nothing.</Muted>
        ) : (
          <AddictionList addictions={addictions.data} showCommunity={false} />
        )}
        {immunities.data && immunities.data.length > 0 && (
          <ImmunityList immunities={immunities.data} showCommunity={false} />
        )}
        <BindCraving entityId={entityId} />
      </div>
    </Section>
  )
}
