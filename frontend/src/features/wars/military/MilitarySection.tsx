import { useState } from 'react'
import {
  Bird,
  CalendarDays,
  Crown,
  Eye,
  EyeOff,
  Flag,
  Lock,
  Radar,
  Save,
  Shield,
  Swords,
  Trash2,
  TriangleAlert,
  UserRound,
  Users,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { commanderTraitValues } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  EmptyState,
  Medallion,
  MiniStat,
  Paged,
  PagedList,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { ArmyOrders } from './ArmyDepth'
import { ArmyPanel } from './ArmyPanel'
import { NetworkAgents } from './Intrigue'
import { MilitaryDepth } from './MilitaryDepth'
import { CohortCard, OccupationCard } from './WarRoom'
import {
  type CommanderTrait,
  type MilitaryOverview,
  type SpyNetwork,
  soldiersOf,
  useArmyCard,
  useMilitary,
} from './api'
import {
  COVER,
  OPERATION,
  PERCENT,
  TRAIT,
  fieldLabel,
  named,
  percentTone,
  busyOf,
  cardGrid,
  whole,
} from './labels'
import {
  Adjust,
  ChoiceField,
  NumberField,
  Panel,
  Plain,
  Tag,
  TableTag,
  ToggleField,
} from './parts'

const NETWORK_NUMBERS = ['agents', 'depth', 'exposure', 'intel'] as const
const NETWORK_ICON = {
  agents: Users,
  depth: Radar,
  exposure: EyeOff,
  intel: Eye,
} as const
type NetworkNumber = (typeof NETWORK_NUMBERS)[number]

function NetworkCard({
  network,
  watching,
  blocked,
}: {
  network: SpyNetwork
  watching: boolean
  blocked: string | null
}) {
  const [numbers, setNumbers] = useState<Record<NetworkNumber, string>>(
    () =>
      Object.fromEntries(
        NETWORK_NUMBERS.map((key) => [key, String(network[key])])
      ) as Record<NetworkNumber, string>
  )
  const [cover, setCover] = useState<string>(network.cover)
  const save = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/spy:edit_network', {
          body: {
            network_id: network.id,
            values: {
              ...Object.fromEntries(
                NETWORK_NUMBERS.map((key) => [
                  key,
                  whole(numbers[key], key === 'agents' ? undefined : PERCENT),
                ])
              ),
              cover,
            },
            dismantle: false,
          },
        })
      ),
  })
  const roll = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/spy:edit_network', {
          body: { network_id: network.id, dismantle: true },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending, roll.isPending)
  const disguise = named(COVER, network.cover)
  return (
    <li
      data-surface='SpyNetwork'
      className='@container/spy flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-3'
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion
          icon={watching ? EyeOff : Eye}
          tone={watching ? 'danger' : 'info'}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <Text as='span' weight='semibold' truncate>
            {`${network.owner?.name ?? 'Someone'} → ${network.target?.name ?? 'someone'}`}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {watching
              ? 'A network watching this record'
              : 'A network run by this record'}
          </Muted>
        </div>
        <div className='flex shrink-0 flex-col items-end'>
          <Stat value={formatInteger(network.agents)} size='kpi' />
          <Label>Agents</Label>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Tag
          item={disguise}
          text={`Disguised as ${disguise.label.toLowerCase()}`}
        />
        {network.spymaster && (
          <Plain
            icon={UserRound}
          >{`Spymaster ${network.spymaster.name}`}</Plain>
        )}
        <Plain
          icon={CalendarDays}
        >{`Since epoch ${network.since_epoch}`}</Plain>
        {network.last_operation && (
          <TableTag
            table={OPERATION}
            value={network.last_operation}
            text={`${named(OPERATION, network.last_operation).label}${network.last_epoch !== null ? ` · epoch ${network.last_epoch}` : ''}`}
          />
        )}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 @sm/spy:grid-cols-3'>
        <StatBar
          label='Depth'
          icon={Radar}
          value={network.depth}
          max={PERCENT}
          tone='verdigris'
        />
        <StatBar
          label='Exposure'
          icon={EyeOff}
          value={network.exposure}
          max={PERCENT}
          tone={percentTone(network.exposure, true)}
        />
        <StatBar
          label='Intelligence'
          icon={Eye}
          value={network.intel}
          max={PERCENT}
          tone='info'
        />
      </div>
      <div className='mt-auto flex min-w-0 flex-col'>
        <Adjust
          title='Shape the network'
          note='Agents, depth, exposure and gathered intelligence, and the cover they hide behind.'
        >
          <div className='grid min-w-0 grid-cols-1 gap-2 @sm/spy:grid-cols-2'>
            {NETWORK_NUMBERS.map((key) => (
              <NumberField
                key={key}
                label={fieldLabel(key)}
                icon={NETWORK_ICON[key]}
                value={numbers[key]}
                max={key === 'agents' ? undefined : PERCENT}
                onChange={(value) =>
                  setNumbers((current) => ({ ...current, [key]: value }))
                }
              />
            ))}
            <ChoiceField
              label='Cover'
              icon={disguise.icon}
              value={cover}
              table={COVER}
              blocked={busy}
              onPick={setCover}
            />
          </div>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Button
              size='sm'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => save.mutate(undefined)}
            >
              <Save />
              Save
            </Button>
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => roll.mutate(undefined)}
            >
              <Trash2 />
              Roll it up
            </Button>
          </div>
        </Adjust>
      </div>
      {network.owner && (
        <NetworkAgents
          networkId={network.id}
          ownerId={network.owner.id}
          blocked={blocked}
        />
      )}
    </li>
  )
}

function TraitToggle({
  mortalId,
  trait,
  held,
  blocked,
}: {
  mortalId: number
  trait: CommanderTrait
  held: boolean
  blocked: string | null
}) {
  const toggle = useGodAction<boolean>({
    run: (next) =>
      unwrap(
        api.POST('/api/actions/commander:trait', {
          body: { mortal_id: mortalId, trait, held: next },
        })
      ),
  })
  const busy = busyOf(blocked, toggle.isPending)
  return (
    <ToggleField
      item={named(TRAIT, trait)}
      checked={held}
      disabled={busy !== null}
      onChange={(next) => toggle.mutate(next)}
    />
  )
}

function CommanderTraits({
  entityId,
  traits,
  blocked,
}: {
  entityId: number
  traits: CommanderTrait[]
  blocked: string | null
}) {
  return (
    <Panel
      title='Battle traits'
      icon={Crown}
      tone='gold'
      count={traits.length}
      hint='How this mortal leads an army in the field'
    >
      <div
        data-surface='CommanderTraits'
        className='flex min-w-0 flex-col gap-3'
      >
        {traits.length === 0 ? (
          <Muted variant='caption'>
            No battle trait yet. Battles won and lost teach them.
          </Muted>
        ) : (
          <PagedList
            items={traits}
            initial={12}
            noun={['entry', 'entries']}
            as='div'
            className='flex min-w-0 flex-wrap gap-1.5'
            itemKey={(trait) => trait}
          >
            {(trait) => <TableTag key={trait} table={TRAIT} value={trait} />}
          </PagedList>
        )}
        <Adjust
          title='Grant or take battle traits'
          note='Each trait changes how this mortal fights when leading an army.'
        >
          <div className='grid min-w-0 grid-cols-1 gap-2 @sm/mil:grid-cols-2 @3xl/mil:grid-cols-3'>
            {commanderTraitValues.map((trait) => (
              <TraitToggle
                key={trait}
                mortalId={entityId}
                trait={trait}
                held={traits.includes(trait)}
                blocked={blocked}
              />
            ))}
          </div>
        </Adjust>
      </div>
    </Panel>
  )
}

function Overview({
  entityId,
  data,
  mortal,
  blocked,
}: {
  entityId: number
  data: MilitaryOverview
  mortal: boolean
  blocked: string | null
}) {
  const captives = [...data.captives_held, ...data.captives_lost]
  const networks = [...data.networks, ...data.watched_by]
  const occupations = [...data.occupying, ...data.occupied]
  const soldiers = data.armies.reduce((sum, army) => sum + soldiersOf(army), 0)
  const held = data.captives_held.reduce((sum, item) => sum + item.count, 0)
  const lost = data.captives_lost.reduce((sum, item) => sum + item.count, 0)
  const empty =
    data.armies.length +
      captives.length +
      networks.length +
      occupations.length ===
    0
  return (
    <div
      data-surface='MilitaryOverview'
      className='@container/mil flex min-w-0 flex-col gap-4'
    >
      {mortal && (
        <CommanderTraits
          entityId={entityId}
          traits={data.commander_traits}
          blocked={blocked}
        />
      )}
      {empty ? (
        <EmptyState
          size={mortal ? 'compact' : 'default'}
          icon={Bird}
          title='Untouched by war'
          description='No army, captive cohort, spy network or occupation touches this record.'
        />
      ) : (
        <div className='grid min-w-0 grid-cols-2 gap-2 @3xl/mil:grid-cols-4'>
          <MiniStat
            icon={Swords}
            label={data.armies.length === 1 ? 'Army' : 'Armies'}
            value={formatInteger(data.armies.length)}
            tone='danger'
            hint={`${formatInteger(soldiers)} soldiers under arms`}
          />
          <MiniStat
            icon={Lock}
            label='Captives held / lost'
            value={`${formatInteger(held)} / ${formatInteger(lost)}`}
            tone='warning'
            hint='People this record holds, then its own people held by others'
          />
          <MiniStat
            icon={Eye}
            label='Spy networks run / watching'
            value={`${data.networks.length} / ${data.watched_by.length}`}
            tone='info'
          />
          <MiniStat
            icon={Flag}
            label='Lands held / lost'
            value={`${data.occupying.length} / ${data.occupied.length}`}
            tone='gold'
          />
        </div>
      )}
      <Paged items={data.armies}>
        {(army) => (
          <ArmyPanel key={army.army?.id} army={army} blocked={blocked} />
        )}
      </Paged>
      {captives.length > 0 && (
        <Panel
          title='Captives'
          icon={Lock}
          tone='warning'
          count={captives.length}
          hint='Cohorts taken in war and what became of them'
        >
          <ul className={cardGrid(captives.length)}>
            <Paged items={data.captives_held} as='li'>
              {(cohort) => (
                <CohortCard
                  key={cohort.id}
                  cohort={cohort}
                  blocked={blocked}
                  perspective='Held by this record'
                />
              )}
            </Paged>
            <Paged items={data.captives_lost}>
              {(cohort) => (
                <CohortCard
                  key={cohort.id}
                  cohort={cohort}
                  blocked={blocked}
                  perspective='Its own people in chains'
                />
              )}
            </Paged>
          </ul>
        </Panel>
      )}
      {networks.length > 0 && (
        <Panel
          title='Spy networks'
          icon={Eye}
          tone='info'
          count={networks.length}
          hint='Agents, their cover and what they have learned'
        >
          <ul className={cardGrid(networks.length)}>
            <Paged items={data.networks} as='li'>
              {(network) => (
                <NetworkCard
                  key={network.id}
                  network={network}
                  watching={false}
                  blocked={blocked}
                />
              )}
            </Paged>
            <Paged items={data.watched_by}>
              {(network) => (
                <NetworkCard
                  key={network.id}
                  network={network}
                  watching
                  blocked={blocked}
                />
              )}
            </Paged>
          </ul>
        </Panel>
      )}
      {occupations.length > 0 && (
        <Panel
          title='Occupations'
          icon={Flag}
          tone='gold'
          count={occupations.length}
          hint='Lands held by the sword'
        >
          <ul className={cardGrid(occupations.length)}>
            <Paged items={data.occupying} as='li'>
              {(item) => (
                <OccupationCard
                  key={`held.${item.region?.id}`}
                  occupation={item}
                  blocked={blocked}
                  perspective='Held by this record'
                />
              )}
            </Paged>
            <Paged items={data.occupied}>
              {(item) => (
                <OccupationCard
                  key={`lost.${item.region?.id}`}
                  occupation={item}
                  blocked={blocked}
                  perspective='Occupied by an enemy'
                />
              )}
            </Paged>
          </ul>
        </Panel>
      )}
    </div>
  )
}

export function MilitarySection({
  entityId,
  kind,
  readOnlyReason,
}: {
  entityId: number
  kind: string
  readOnlyReason?: string | null
}) {
  const army = kind === 'army'
  const card = useArmyCard(entityId, army)
  const overview = useMilitary(entityId, !army)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const query = army ? card : overview
  return (
    <Section
      id='section-military'
      title={army ? 'Army' : 'War and captivity'}
      description={
        army
          ? 'Stacks, orders, supplies and marches.'
          : 'Armies, captives, spies and occupied lands.'
      }
      icon={army ? Swords : Shield}
    >
      {query.isPending && <Skeleton className='h-textarea w-full' />}
      {query.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Nothing could be read'
          description={query.error.message}
        />
      )}
      {army && card.data && (
        <div className='@container/mil flex min-w-0 flex-col gap-3'>
          <ArmyPanel army={card.data} blocked={blocked} />
          <ArmyOrders armyId={entityId} blocked={blocked} />
        </div>
      )}
      {!army && overview.data && (
        <Overview
          entityId={entityId}
          data={overview.data}
          mortal={kind === 'mortal'}
          blocked={blocked}
        />
      )}
      {!army && kind !== 'mortal' && (
        <MilitaryDepth entityId={entityId} kind={kind} blocked={blocked} />
      )}
    </Section>
  )
}
