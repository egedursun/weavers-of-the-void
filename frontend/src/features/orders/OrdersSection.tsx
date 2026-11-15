import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { OrderPanel } from './OrderPanel'
import {
  ExchangePanel,
  SavingPanel,
  TradePanel,
  TravelPanel,
} from './OrdersPanels'
import { type OrdersNodeView, useNodeOrders, useOrdersAction } from './api'
import { ORDERS_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: OrdersNodeView) => number
}[] = [
  {
    key: 'order',
    label: 'Economic order',
    count: (data) => data.orders.length + data.transitions.length,
  },
  {
    key: 'saving',
    label: 'Saving and hoards',
    count: (data) => data.savings.length + data.hoards.length,
  },
  {
    key: 'exchange',
    label: 'Rates and bills',
    count: (data) => data.rates.length + data.bills.length,
  },
  {
    key: 'trade',
    label: 'Work put out and chains',
    count: (data) => data.putting_out.length + data.chains.length,
  },
  { key: 'travel', label: 'Travellers', count: (data) => data.flows.length },
]

const FIRST_PANE: Record<string, Pane> = {
  polity: 'order',
  settlement: 'saving',
  faction: 'trade',
  structure: 'travel',
}

export function OrdersSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeOrders(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const running = useOrdersAction(
    'orders:run',
    (_: void) => ({}),
    'Every saving, rate, order, arrangement and journey is read'
  )
  const blocked = readOnlyReason
  return (
    <Section
      id='section-orders'
      title='Economic life: orders, saving, money, work put out and travel'
      description='The economic order of the realm this thing answers to, how its households save, the rates between coins at its market, the work merchants put out and the travellers who come and go. Every kind of thing shows these where they touch it, and a control that cannot apply here stays on screen and says why.'
      icon={ORDERS_ICON}
      tone='gold'
    >
      <div data-surface='OrdersSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading orders, saving, money and travel' />
        ) : query.isError ? (
          <EmptyState
            icon={ORDERS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'order'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Orders, saving, money, work put out and travel'>
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
            <TabsContent value='order' className='flex min-w-0 flex-col gap-6'>
              <OrderPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent value='saving' className='flex min-w-0 flex-col gap-6'>
              <SavingPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent
              value='exchange'
              className='flex min-w-0 flex-col gap-6'
            >
              <ExchangePanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent value='trade' className='flex min-w-0 flex-col gap-6'>
              <TradePanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent value='travel' className='flex min-w-0 flex-col gap-6'>
              <TravelPanel data={query.data} blocked={blocked} />
            </TabsContent>
          </Tabs>
        )}
        <StepButton
          icon={ORDERS_ICON}
          label='Read economic life now'
          busy={why(blocked, running.isPending)}
          onClick={() => running.mutate()}
        />
      </div>
    </Section>
  )
}
