import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { CrisesPanel, MovementsPanel, MysticsPanel } from './MysteryPanels'
import {
  DivinationPanel,
  FeedingPanel,
  ForecastPanel,
  ForesightPanel,
} from './OmenPanels'
import { AfterlifePanel, FaithClimatePanel, RitesPanel } from './RitePanels'
import { PetitionsPanel, SpiritsPanel } from './SpiritPanels'
import { type SacredNodeView, useNodeSacred } from './api'
import { SACRED_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: SacredNodeView) => number
}[] = [
  {
    key: 'spirits',
    label: 'Spirits and petitions',
    count: (data) =>
      data.spirits.length + data.offices.length + data.petitions.length,
  },
  {
    key: 'mysteries',
    label: 'Mystics, movements and crises',
    count: (data) =>
      (data.mystic ? 1 : 0) +
      data.mystics.length +
      data.movements.length +
      data.crises.length,
  },
  {
    key: 'rites',
    label: 'Rites, afterlife and faith',
    count: (data) =>
      data.teachings.length +
      data.sacraments.length +
      data.afterlives.length +
      (data.climate ? 1 : 0),
  },
  {
    key: 'omens',
    label: 'Omens and foresight',
    count: (data) =>
      data.systems.length +
      data.readings.length +
      data.foresights.length +
      data.models.length,
  },
  {
    key: 'feelings',
    label: 'Fed by feeling',
    count: (data) => data.feedings.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  place: 'spirits',
  spirit: 'spirits',
  house: 'spirits',
  settlement: 'spirits',
  mortal: 'mysteries',
  cult: 'rites',
  people: 'omens',
  polity: 'omens',
  faction: 'omens',
  prophecy: 'mysteries',
  son: 'feelings',
  foreign_god: 'feelings',
}

export function SacredSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeSacred(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  return (
    <Section
      id='section-sacred'
      title='Spirits, mysteries, rites and omens'
      description='Place spirits with their offerings, favour and offices, and the petitions those offices read; mystics and their visions, millenarian movements and crises of faith; the sacraments a church teaches and gives, the afterlife it teaches against the one its dead meet, and what pulls a town’s faith; ways of divination and the omens read for rulers, seers and their foresights, and the forecasts of learned orders; and the feelings each god feeds on. Every kind of thing shows these records where they touch it: places, towns and houses keep spirits, mortals see visions and receive sacraments, churches teach, peoples divine, realms are forecast and gods feed. A control that cannot apply to this kind of thing stays on screen and says why.'
      icon={SACRED_ICON}
      tone='gold'
    >
      <div data-surface='SacredSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading the spirits, the visions, the rites and the omens' />
        ) : query.isError ? (
          <EmptyState
            icon={SACRED_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'spirits'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Spirits, mysteries, rites and omens'>
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
              value='spirits'
              className='flex min-w-0 flex-col gap-6'
            >
              <SpiritsPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <PetitionsPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent
              value='mysteries'
              className='flex min-w-0 flex-col gap-6'
            >
              <MysticsPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <MovementsPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <CrisesPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='rites' className='flex min-w-0 flex-col gap-6'>
              <RitesPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <AfterlifePanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <FaithClimatePanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='omens' className='flex min-w-0 flex-col gap-6'>
              <DivinationPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <ForesightPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
              <ForecastPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent
              value='feelings'
              className='flex min-w-0 flex-col gap-6'
            >
              <FeedingPanel
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
