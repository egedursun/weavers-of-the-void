import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { ArtMarketPanel, CanonPanel, ForgeryPanel } from './ArtPanels'
import { ConstructPanel, OrdersPanel } from './ConstructPanels'
import { BirthSignPanel, ContractPanel, RemadePanel } from './FatePanels'
import {
  ClubPanel,
  LeaguePanel,
  MatchPanel,
  MovementPanel,
} from './PastimePanels'
import { type PursuitsNodeView, useNodePursuits } from './api'
import { PURSUITS_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: PursuitsNodeView) => number
}[] = [
  {
    key: 'works',
    label: 'Works, forgeries and canon',
    count: (data) =>
      data.prices.length +
      data.sales.length +
      (data.collector ? 1 : 0) +
      data.forgeries.length +
      data.canon.length,
  },
  {
    key: 'pastimes',
    label: 'Movements, clubs and matches',
    count: (data) =>
      (data.movement ? 1 : 0) +
      data.clubs.length +
      (data.league ? 1 : 0) +
      data.matches.length +
      data.bets.length,
  },
  {
    key: 'constructs',
    label: 'Constructs and their orders',
    count: (data) =>
      (data.as_construct ? 1 : 0) + data.made.length + data.instructions.length,
  },
  {
    key: 'fates',
    label: 'Bounties, signs and remaking',
    count: (data) =>
      data.contracts.length + (data.sign ? 1 : 0) + (data.remade ? 1 : 0),
  },
]

const FIRST_PANE: Record<string, Pane> = {
  artwork: 'works',
  people: 'works',
  item: 'works',
  art_form: 'works',
  faction: 'pastimes',
  settlement: 'pastimes',
  polity: 'pastimes',
  beast: 'constructs',
  army: 'constructs',
  mortal: 'fates',
}

export function PursuitsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodePursuits(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const props = { nodeId, kind, blocked: readOnlyReason }
  return (
    <Section
      id='section-pursuits'
      title='Works, pastimes, constructs and fates'
      description='The market in works with its collectors, prices and sales, the forgeries that pass for the real thing and the canon of each people; art movements with their manifestos, clubs, leagues, matches and the wagers of towns; constructs with their bodies, power, wear and will and the orders and tokens that command them; bounties on beasts and the hunters who take them, the signs mortals are born under, and the condemned whom the law remade in body. Every kind of thing shows these records where they touch it: works are priced and forged, peoples keep canons, towns found clubs and post bounties, realms keep leagues, makers build constructs, gods hold their tokens and mortals are born under signs. A control that cannot apply to this kind of thing stays on screen and says why.'
      icon={PURSUITS_ICON}
      tone='verdigris'
    >
      <div
        data-surface='PursuitsSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the works, the clubs, the constructs and the signs' />
        ) : query.isError ? (
          <EmptyState
            icon={PURSUITS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'works'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Works, pastimes, constructs and fates'>
              {PANES.map(({ key, label, count }) => {
                const Icon = TAB_ICONS[key]
                const total = count(query.data)
                return (
                  <TabsTrigger key={key} value={key}>
                    <Icon />
                    {label}
                    {total > 0 && (
                      <Badge size='sm' variant='secondary'>
                        {total}
                      </Badge>
                    )}
                  </TabsTrigger>
                )
              })}
            </TabsList>
            <TabsContent value='works' className='flex min-w-0 flex-col gap-6'>
              <ArtMarketPanel {...props} data={query.data} />
              <ForgeryPanel {...props} data={query.data} />
              <CanonPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent
              value='pastimes'
              className='flex min-w-0 flex-col gap-6'
            >
              <MovementPanel {...props} data={query.data} />
              <ClubPanel {...props} data={query.data} />
              <LeaguePanel {...props} data={query.data} />
              <MatchPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent
              value='constructs'
              className='flex min-w-0 flex-col gap-6'
            >
              <ConstructPanel {...props} data={query.data} />
              <OrdersPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='fates' className='flex min-w-0 flex-col gap-6'>
              <ContractPanel {...props} data={query.data} />
              <BirthSignPanel {...props} data={query.data} />
              <RemadePanel {...props} data={query.data} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
