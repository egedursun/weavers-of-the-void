import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useEntityType } from '@/features/arcana/model'
import { CrowdPanel } from './CrowdPanel'
import { GenerationPanel } from './GenerationPanel'
import { HistoryPanel } from './HistoryPanel'
import { NormPanel } from './NormPanel'
import { DatingPanel, DesignPanel, HeraldryPanel } from './RecordsPanels'
import { StoryletPanel } from './StoryletPanel'
import { type CollectiveView, useNodeCollective } from './api'
import { COLLECTIVE_ICON, SECTION_ICONS } from './labels'

type Pane = keyof typeof SECTION_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: CollectiveView) => number
}[] = [
  {
    key: 'crowds',
    label: 'Crowds',
    count: (data) =>
      data.mobs.length + data.movements.length + data.cascades.length,
  },
  {
    key: 'history',
    label: 'Memory',
    count: (data) =>
      data.accounts.length +
      data.strikes.length +
      data.commemorations.length +
      data.lost_lands.length +
      (data.myth ? 1 : 0),
  },
  {
    key: 'storylets',
    label: 'Storylets',
    count: (data) => data.storylets.length,
  },
  {
    key: 'norms',
    label: 'Customs',
    count: (data) =>
      data.norms.length + data.roles.length + data.lessons.length,
  },
  {
    key: 'generations',
    label: 'Generations',
    count: (data) => data.generations.length + data.diasporas.length,
  },
  { key: 'dating', label: 'Reckoning', count: (data) => (data.dating ? 1 : 0) },
  { key: 'heraldry', label: 'Arms', count: (data) => (data.arms ? 1 : 0) },
  { key: 'designs', label: 'Designs', count: (data) => data.designs.length },
]

const FIRST_PANE: Record<string, Pane> = {
  settlement: 'crowds',
  polity: 'history',
  people: 'norms',
  cult: 'norms',
  house: 'heraldry',
  army: 'heraldry',
  faction: 'heraldry',
  title: 'heraldry',
  vessel: 'designs',
  mortal: 'storylets',
}

export function CollectiveSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeCollective(nodeId)
  const type = useEntityType(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  return (
    <Section
      id='section-collective'
      title='Crowds, memory, customs and craft'
      description='The town’s mood and the cascades, mobs and movements it breeds; the accounts kept of every event and how far they stray from the truth; storylets; customs and roles; generations, diasporas and the balance of the people; how years are counted; arms; and the vehicle types its yards build to.'
      icon={COLLECTIVE_ICON}
      tone='gold'
    >
      <div
        data-surface='CollectiveSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the crowds and the chronicles' />
        ) : query.isError ? (
          <EmptyState
            icon={COLLECTIVE_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[type ?? ''] ?? 'history'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Crowds, memory, customs and craft'>
              {PANES.map(({ key, label, count }) => {
                const Icon = SECTION_ICONS[key]
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
            <TabsContent value='crowds'>
              <CrowdPanel
                nodeId={nodeId}
                isTown={type === 'settlement'}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='history'>
              <HistoryPanel
                nodeId={nodeId}
                type={type}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='storylets'>
              <StoryletPanel data={query.data} blocked={readOnlyReason} />
            </TabsContent>
            <TabsContent value='norms'>
              <NormPanel
                nodeId={nodeId}
                type={type}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='generations'>
              <GenerationPanel
                nodeId={nodeId}
                type={type}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='dating'>
              <DatingPanel
                nodeId={nodeId}
                type={type}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='heraldry'>
              <HeraldryPanel
                nodeId={nodeId}
                name={query.data.node.name}
                type={type}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='designs'>
              <DesignPanel
                nodeId={nodeId}
                type={type}
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
