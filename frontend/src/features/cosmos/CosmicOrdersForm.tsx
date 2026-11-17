import { useState } from 'react'
import { Anchor, Ghost, Plane, Scale, Star, Store, Unplug } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { CosmicActionButton } from './CosmicActionButton'
import { EntityPicker } from './EntityPicker'
import { OrderBlock, OrderFields } from './OrderBlock'
import { type ActionResponse } from './api'
import { type CosmosIndex } from './model/cosmosModel'
import { type RuleBook } from './model/rules'
import { useCosmicAction } from './useCosmicAction'

const TRAVELLER_TYPES = [
  'mortal',
  'people',
  'settlement',
  'cult',
  'faction',
] as const
const COMMUNITY_TYPES = ['people', 'settlement', 'cult', 'faction'] as const
const REGION_TYPES = ['region'] as const
const FACTION_TYPES = ['faction'] as const
const SOUL_TYPES = ['spirit'] as const
const VESSEL_TYPES = ['item', 'vessel', 'structure', 'artwork'] as const
const DEPOSIT_TYPES = ['resource'] as const
const STAR_ENTITY_TYPES = [
  'mortal',
  'celestial',
  'people',
  'settlement',
  'item',
  'legend',
] as const
const NOBODY = 'nobody'

type OrdersProps = {
  index: CosmosIndex
  rules: RuleBook
  worldId: number | undefined
}

function useOrder() {
  return useCosmicAction({
    run: (call: () => Promise<ActionResponse>) => call(),
  })
}

function WorldSelect({
  index,
  value,
  onChange,
  label,
}: {
  index: CosmosIndex
  value: string
  onChange: (value: string) => void
  label: string
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger aria-label={label} className='w-full'>
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        {index.worlds.map((item) => (
          <SelectItem key={item.world.id} value={String(item.world.id)}>
            {item.world.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function CosmicOrdersForm({ index, rules, worldId }: OrdersProps) {
  const order = useOrder()
  const [exiled, setExiled] = useState<number | null>(null)
  const [exileWorld, setExileWorld] = useState('')
  const [pardoned, setPardoned] = useState<number | null>(null)
  const [soul, setSoul] = useState<number | null>(null)
  const [vessel, setVessel] = useState<number | null>(null)
  const [region, setRegion] = useState<number | null>(null)
  const [band, setBand] = useState<number | null>(null)
  const [deposit, setDeposit] = useState<number | null>(null)
  const [owner, setOwner] = useState<number | null>(null)
  const [starWorld, setStarWorld] = useState('')
  const [epochStar, setEpochStar] = useState<number | null>(null)
  const exileTarget = exileWorld || ''
  const epochWorld =
    starWorld || String(worldId ?? index.worlds[0]?.world.id ?? '')
  const pick = 'Choose a record first.'
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <OrderBlock
        title='Exile to another world'
        description='A mortal or a community is cast out to a world of your choosing; pardon lifts the curse.'
      >
        <OrderFields>
          <EntityPicker
            types={TRAVELLER_TYPES}
            value={exiled}
            onChange={setExiled}
            placeholder='Who is exiled'
            worldName={index.worldName}
          />
          <WorldSelect
            index={index}
            value={exileTarget}
            onChange={setExileWorld}
            label='To which world'
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            actionId='exile'
            label='Exile'
            icon={Plane}
            variant='destructive'
            pending={order.isPending}
            blockedReason={
              exiled === null
                ? pick
                : exileTarget === ''
                  ? 'Choose a world.'
                  : undefined
            }
            confirm={{
              title: `Exile ${index.entityName(exiled) ?? 'this record'}?`,
              description: `They are cast out to ${index.worldName(Number(exileTarget))}.`,
              confirmText: 'Exile',
            }}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/entities/{entity_id}/exile', {
                    params: { path: { entity_id: exiled ?? 0 } },
                    body: { world_id: Number(exileTarget) },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Pardon'
        description='Forgive oath-breaking, exile and curses at once.'
      >
        <OrderFields>
          <EntityPicker
            types={TRAVELLER_TYPES}
            value={pardoned}
            onChange={setPardoned}
            placeholder='Who is pardoned'
            worldName={index.worldName}
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            actionId='pardon'
            label='Pardon'
            icon={Scale}
            pending={order.isPending}
            blockedReason={pardoned === null ? pick : undefined}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/entities/{entity_id}/pardon', {
                    params: { path: { entity_id: pardoned ?? 0 } },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Bind a soul to a vessel'
        description='A free soul is bound into an item, a vessel or a work; a structure begins to move and act.'
      >
        <OrderFields>
          <EntityPicker
            types={SOUL_TYPES}
            value={soul}
            onChange={setSoul}
            placeholder='Which soul'
            worldName={index.worldName}
          />
          <EntityPicker
            types={VESSEL_TYPES}
            value={vessel}
            onChange={setVessel}
            placeholder='Into what'
            worldName={index.worldName}
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            actionId='cosmic:soul_bind'
            label='Bind the soul'
            icon={Ghost}
            cost={rules.path('cosmic_costs.spirit_cloak')}
            pending={order.isPending}
            blockedReason={
              soul === null || vessel === null
                ? 'Choose a soul and a vessel.'
                : undefined
            }
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/cosmic/soul-bind', {
                    body: { soul_id: soul ?? 0, target_id: vessel ?? 0 },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Wandering markets and route raiders'
        description='Raise a market that drifts between worlds, or loose pirates on the routes from a region.'
      >
        <OrderFields>
          <EntityPicker
            types={REGION_TYPES}
            value={region}
            onChange={setRegion}
            placeholder='From which region'
            worldName={index.worldName}
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            actionId='market:found'
            label='Found a wandering market'
            icon={Store}
            pending={order.isPending}
            blockedReason={
              region === null ? 'Choose a region first.' : undefined
            }
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/market:found', {
                    body: { region_id: region ?? 0 },
                  })
                )
              )
            }
          />
          <CosmicActionButton
            actionId='pirates:spawn'
            label='Loose route raiders'
            icon={Anchor}
            variant='destructive'
            pending={order.isPending}
            blockedReason={
              region === null ? 'Choose a region first.' : undefined
            }
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/pirates:spawn', {
                    body: { region_id: region ?? 0 },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Disband a market or pirate band'
        description='The faction scatters and its routes go quiet.'
      >
        <OrderFields>
          <EntityPicker
            types={FACTION_TYPES}
            value={band}
            onChange={setBand}
            placeholder='Which band'
            worldName={index.worldName}
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            actionId='market:disband'
            label='Disband'
            icon={Unplug}
            pending={order.isPending}
            blockedReason={band === null ? 'Choose a band first.' : undefined}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/market:disband', {
                    body: { faction_id: band ?? 0 },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Give a cosmic deposit an owner'
        description='A living community owns the deposit of the travel resource, or nobody does.'
      >
        <OrderFields>
          <EntityPicker
            types={DEPOSIT_TYPES}
            value={deposit}
            onChange={setDeposit}
            placeholder='Which deposit'
            worldName={index.worldName}
          />
          <EntityPicker
            types={COMMUNITY_TYPES}
            value={owner}
            onChange={setOwner}
            placeholder={`Owner (blank: ${NOBODY})`}
            worldName={index.worldName}
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            actionId='deposit:owner'
            label={owner === null ? 'Make it nobody’s' : 'Give it'}
            pending={order.isPending}
            blockedReason={
              deposit === null ? 'Choose a deposit first.' : undefined
            }
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/deposit:owner', {
                    body: { deposit_id: deposit ?? 0, owner_id: owner },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
      <OrderBlock
        title='Set the star of the epoch'
        description='Choose who shines this epoch in a world; leave the record blank to let the sky choose again.'
      >
        <OrderFields>
          <WorldSelect
            index={index}
            value={epochWorld}
            onChange={(value) => {
              setStarWorld(value)
              setEpochStar(null)
            }}
            label='Which world'
          />
          <EntityPicker
            types={STAR_ENTITY_TYPES}
            value={epochStar}
            onChange={setEpochStar}
            placeholder='Which record (optional)'
            worldId={epochWorld ? Number(epochWorld) : undefined}
          />
        </OrderFields>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <CosmicActionButton
            actionId='world:epoch_star'
            label='Set the star'
            icon={Star}
            pending={order.isPending}
            blockedReason={epochWorld === '' ? 'Choose a world.' : undefined}
            onRun={() =>
              order.mutate(() =>
                unwrap(
                  api.POST('/api/actions/world:epoch_star', {
                    body: {
                      world_id: Number(epochWorld),
                      entity_id: epochStar,
                    },
                  })
                )
              )
            }
          />
        </div>
      </OrderBlock>
    </div>
  )
}
