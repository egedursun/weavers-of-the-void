import { type ReactNode } from 'react'
import {
  Bird,
  Fence,
  Gem,
  HandHeart,
  Hammer,
  Map as MapIcon,
  Star,
  Store,
} from 'lucide-react'
import { plural } from '@/lib/units'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { Chip, Meter, RecordRow } from '@/features/cosmography/parts'
import { Ref } from '@/features/gatherings/parts'
import { useGodGate } from '@/features/pantheon/gate'
import { useCosmosAgrarian } from './api'
import {
  AGRARIAN_ICON,
  AID_KINDS,
  CAUSES,
  COMMONS_KINDS,
  COMMONS_RULES,
  PLANS,
  RANKS,
  RINGS,
  USES,
} from './labels'

const SHOWN = 6

function Listing<T>({
  title,
  items,
  empty,
  noun,
  itemKey,
  children,
}: {
  title: string
  items: T[]
  empty: string
  noun: [string, string]
  itemKey: (item: T) => string | number
  children: (item: T) => ReactNode
}) {
  return (
    <>
      <Label variant='overline'>{`${title} (${items.length})`}</Label>
      {items.length === 0 ? (
        <Muted variant='caption'>{empty}</Muted>
      ) : (
        <PagedList
          items={items}
          initial={SHOWN}
          noun={noun}
          className='flex min-w-0 flex-col gap-2'
          itemKey={itemKey}
        >
          {children}
        </PagedList>
      )}
    </>
  )
}

export function CosmosAgrarianSection() {
  const query = useCosmosAgrarian()
  const { reason } = useGodGate()
  const blocked = reason()
  const data = query.data
  return (
    <Section
      id='section-cosmos-agrarian'
      title='Lands, markets, keystones and the stricken'
      description='The gaps between markets and the ranks of central places, the keystone every world depends on, the brands known by name, the latest aid to stricken towns, the towns still rebuilding, the commons and the game reserves.'
      icon={AGRARIAN_ICON}
      tone='success'
    >
      <div
        data-surface='CosmosAgrarianPanel'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the lands and markets of every world' />
        ) : query.isError || !data ? (
          <EmptyState
            icon={AGRARIAN_ICON}
            size='inline'
            title='This could not be read'
            description={query.error?.message ?? ''}
          />
        ) : (
          <>
            {blocked && <Muted variant='caption'>{blocked}</Muted>}
            <div className='@container/tiles min-w-0'>
              <div className='grid min-w-0 grid-cols-2 gap-2 @xl/tiles:grid-cols-4'>
                <KpiTile
                  label='Lands read'
                  value={data.rings.length}
                  icon={MapIcon}
                  tone='verdigris'
                />
                <KpiTile
                  label='Markets'
                  value={
                    data.central_places.filter((item) => item.rank !== 'daily')
                      .length
                  }
                  icon={Store}
                  tone='gold'
                />
                <KpiTile
                  label='Keystones'
                  value={data.keystones.length}
                  icon={Gem}
                  tone='gold'
                />
                <KpiTile
                  label='Towns rebuilding'
                  value={data.rebuilds.length}
                  icon={Hammer}
                  tone='warning'
                />
              </div>
            </div>
            <Listing
              title='Lands by the gap between markets'
              items={data.rings}
              empty='No land has been read yet.'
              noun={['land', 'lands']}
              itemKey={(item) => item.region.id}
            >
              {(item) => (
                <RecordRow
                  icon={RINGS[item.ring].icon}
                  tone={RINGS[item.ring].tone}
                  title={<Ref node={item.region} />}
                  caption={`${RINGS[item.ring].label}${item.market ? ` around ${item.market.name}` : ''}${item.by_water ? ', carried by water' : ''}`}
                >
                  <Meter
                    label='Gap between markets'
                    value={item.gap}
                    tone='warning'
                  />
                </RecordRow>
              )}
            </Listing>
            <Listing
              title='Central places by centrality'
              items={data.central_places}
              empty='No settlement has been ranked yet.'
              noun={['place', 'places']}
              itemKey={(item) => item.settlement.id}
            >
              {(item) => (
                <RecordRow
                  icon={RANKS[item.rank].icon}
                  tone={RANKS[item.rank].tone}
                  title={<Ref node={item.settlement} />}
                  caption={`${RANKS[item.rank].label} for ${plural(item.catchment, 'buyer', 'buyers')}${item.served_by ? `, served by ${item.served_by.name}` : ''}`}
                >
                  <Meter
                    label='Centrality'
                    value={item.centrality}
                    tone='legendary'
                  />
                </RecordRow>
              )}
            </Listing>
            <Listing
              title='Keystones of the worlds'
              items={data.keystones}
              empty='No world depends on one resource yet.'
              noun={['keystone', 'keystones']}
              itemKey={(item) => item.id}
            >
              {(item) => (
                <RecordRow
                  icon={Gem}
                  tone={item.supply < 30 ? 'danger' : 'gold'}
                  title={item.name}
                  caption={`Keystone of ${item.world.name}, needed for ${USES[item.use].label.toLowerCase()}`}
                >
                  <div className='flex min-w-0 flex-wrap gap-2'>
                    {item.controller && (
                      <Chip
                        icon={Store}
                      >{`Held by ${item.controller.name}`}</Chip>
                    )}
                    {item.cult && (
                      <Chip icon={Gem}>{`Sacred to ${item.cult.name}`}</Chip>
                    )}
                  </div>
                  <Meter label='Supply' value={item.supply} tone='legendary' />
                </RecordRow>
              )}
            </Listing>
            <Listing
              title='Brands by reputation'
              items={[...data.brands].sort(
                (a, b) => b.reputation - a.reputation
              )}
              empty='No workshop is known by name yet.'
              noun={['brand', 'brands']}
              itemKey={(item) => item.id}
            >
              {(item) => (
                <RecordRow
                  icon={Star}
                  tone='gold'
                  title={item.name}
                  caption={`Of ${item.community.name}${item.owner ? `, owned by ${item.owner.name}` : ''}`}
                >
                  <Meter
                    label='Reputation'
                    value={item.reputation}
                    tone='legendary'
                  />
                </RecordRow>
              )}
            </Listing>
            <Listing
              title='Latest aid'
              items={data.aid}
              empty='No aid has been sent yet.'
              noun={['gift of aid', 'gifts of aid']}
              itemKey={(item) => item.id}
            >
              {(item) => (
                <RecordRow
                  icon={item.refused ? HandHeart : AID_KINDS[item.kind].icon}
                  tone={item.refused ? 'danger' : AID_KINDS[item.kind].tone}
                  title={`${item.giver.name} to ${item.receiver.name}`}
                  caption={`${AID_KINDS[item.kind].label} in epoch ${item.epoch}${item.refused ? ', turned away' : ''}`}
                />
              )}
            </Listing>
            <Listing
              title='Towns rebuilding'
              items={data.rebuilds}
              empty='No town is rebuilding.'
              noun={['town', 'towns']}
              itemKey={(item) => item.id}
            >
              {(item) => (
                <RecordRow
                  icon={CAUSES[item.cause].icon}
                  tone={PLANS[item.plan].tone}
                  title={<Ref node={item.settlement} />}
                  caption={`After ${CAUSES[item.cause].label.toLowerCase()}, ${PLANS[item.plan].label.toLowerCase()}`}
                >
                  <Meter label='Rebuilt' value={item.progress} tone='success' />
                </RecordRow>
              )}
            </Listing>
            <Listing
              title='Commons by their condition'
              items={data.commons}
              empty='No common is held yet.'
              noun={['common', 'commons']}
              itemKey={(item) => item.id}
            >
              {(item) => (
                <RecordRow
                  icon={
                    item.rule === 'enclosed'
                      ? Fence
                      : COMMONS_KINDS[item.kind].icon
                  }
                  tone={COMMONS_RULES[item.rule].tone}
                  title={<Ref node={item.region} />}
                  caption={`Common ${COMMONS_KINDS[item.kind].label.toLowerCase()}, ${COMMONS_RULES[item.rule].label.toLowerCase()}`}
                >
                  <Meter
                    label='Condition'
                    value={item.condition}
                    tone='success'
                  />
                </RecordRow>
              )}
            </Listing>
            <Listing
              title='Game reserves by resentment'
              items={data.reserves}
              empty='No game is reserved yet.'
              noun={['reserve', 'reserves']}
              itemKey={(item) => item.id}
            >
              {(item) => (
                <RecordRow
                  icon={Bird}
                  tone='verdigris'
                  title={<Ref node={item.region} />}
                  caption={`Reserved${item.holder ? ` by ${item.holder.name}` : ''}`}
                >
                  <Meter
                    label='Resentment'
                    value={item.resentment}
                    tone='destructive'
                  />
                </RecordRow>
              )}
            </Listing>
          </>
        )}
      </div>
    </Section>
  )
}
