import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { OrderOfBattlePanel, TheatresPanel } from './CommandPanels'
import { ExpeditionPanel, QuirksPanel } from './ExpeditionPanels'
import { AdmiraltyPanel, ShipPanel } from './SeaPanels'
import { SupplyPanel } from './SupplyPanels'
import { type OperationsNodeView, useNodeOperations } from './api'
import { OPERATIONS_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: OperationsNodeView) => number
}[] = [
  {
    key: 'command',
    label: 'Order of battle and fronts',
    count: (data) => data.echelons.length + data.theatres.length,
  },
  {
    key: 'supply',
    label: 'Supply and offensives',
    count: (data) =>
      data.flows.length +
      data.depots.length +
      data.transport.length +
      (data.operation ? 1 : 0),
  },
  {
    key: 'sea',
    label: 'Ships and admiralty',
    count: (data) =>
      (data.ship ? 1 : 0) + data.crews.length + (data.admiralty ? 1 : 0),
  },
  {
    key: 'expeditions',
    label: 'Expeditions and quirks',
    count: (data) => data.expeditions.length + data.quirks.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  army: 'command',
  polity: 'command',
  vessel: 'sea',
  mortal: 'expeditions',
  region: 'expeditions',
  place: 'expeditions',
}

export function OperationsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeOperations(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  return (
    <Section
      id='section-operations'
      title='Command, supply, ships and expeditions'
      description='The order of battle with its headquarters, command range and points; theatres of war and the reserves each receives; depots, transport and the supply that reaches each army, and offensives that outrun it; ships by the wind, their damage, crews, fires and prizes, and the admiralty that builds them; expeditions with their party, provisions, light and log, and the quirks they leave. Every kind of thing shows these records where they touch it: armies and realms command, ships sail, mortals set out and bear quirks, and lands, places and spirits are where expeditions go. A control that cannot apply to this kind of thing stays on screen and says why.'
      icon={OPERATIONS_ICON}
      tone='warning'
    >
      <div
        data-surface='OperationsSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the orders, the supply lines, the fleets and the expeditions' />
        ) : query.isError ? (
          <EmptyState
            icon={OPERATIONS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'command'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Command, supply, ships and expeditions'>
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
            <TabsContent
              value='command'
              className='flex min-w-0 flex-col gap-6'
            >
              <OrderOfBattlePanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <TheatresPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='supply'>
              <SupplyPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='sea' className='flex min-w-0 flex-col gap-6'>
              <ShipPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <AdmiraltyPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent
              value='expeditions'
              className='flex min-w-0 flex-col gap-6'
            >
              <ExpeditionPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <QuirksPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
