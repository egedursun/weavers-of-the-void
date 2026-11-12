import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { HoldingsPanel } from './HoldingsPanel'
import { LandPanel } from './LandPanel'
import { ReadinessPanel } from './ReadinessPanel'
import { StaplesPanel } from './StaplesPanel'
import { type AgrarianNodeView, useNodeAgrarian } from './api'
import { AGRARIAN_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: AgrarianNodeView) => number
}[] = [
  {
    key: 'land',
    label: 'Land and markets',
    count: (data) =>
      (data.ring ? 1 : 0) +
      data.nutrients.length +
      (data.intensity ? 1 : 0) +
      (data.central_place ? 1 : 0),
  },
  {
    key: 'holdings',
    label: 'Plantings, commons and game',
    count: (data) =>
      data.perennials.length +
      data.commons.length +
      data.reserves.length +
      (data.famine ? 1 : 0),
  },
  {
    key: 'readiness',
    label: 'Readiness and relief',
    count: (data) => data.works.length + data.aid.length + data.rebuilds.length,
  },
  {
    key: 'staples',
    label: 'Keystone and brands',
    count: (data) => data.keystones.length + data.brands.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  region: 'land',
  settlement: 'readiness',
  people: 'holdings',
  house: 'holdings',
  world: 'staples',
  cult: 'staples',
  polity: 'readiness',
}

export function AgrarianSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeAgrarian(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  return (
    <Section
      id='section-agrarian'
      title='Land, harvest, readiness and staples'
      description='The ring of land use around the nearest market and the rank of central places; the soil’s stocks and how hard the land is farmed; long-lived plantings, commons and their enclosure, game reserves and the famine foods a people remembers; works against disaster, aid to the stricken and rebuilding; the resource a world depends on and the brands of famous workshops.'
      icon={AGRARIAN_ICON}
      tone='success'
    >
      <div
        data-surface='AgrarianSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the land, its harvests and its stores' />
        ) : query.isError ? (
          <EmptyState
            icon={AGRARIAN_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'holdings'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Land, harvest, readiness and staples'>
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
            <TabsContent value='land'>
              <LandPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='holdings'>
              <HoldingsPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='readiness'>
              <ReadinessPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='staples'>
              <StaplesPanel data={query.data} blocked={readOnlyReason} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
