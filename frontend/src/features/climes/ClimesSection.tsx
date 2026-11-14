import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { CrossingsPanel } from './CrossingsPanel'
import { SeasonsPanel } from './SeasonsPanel'
import { WindsPanel } from './WindsPanel'
import { type ClimesNodeView, useNodeClimes } from './api'
import { CLIMES_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: ClimesNodeView) => number
}[] = [
  { key: 'winds', label: 'Winds', count: (data) => data.winds.length },
  {
    key: 'seasons',
    label: 'Monsoons and swings',
    count: (data) => data.monsoons.length + (data.oscillation ? 1 : 0),
  },
  {
    key: 'crossings',
    label: 'Windows and roads',
    count: (data) => data.windows.length + data.cultures.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  world: 'seasons',
  settlement: 'crossings',
  people: 'crossings',
  faction: 'crossings',
  cult: 'crossings',
}

export function ClimesSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeClimes(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const blocked = readOnlyReason
  return (
    <Section
      id='section-climes'
      title='Winds, seasons and crossings'
      description='The prevailing winds and rain shadows of the lands, the monsoons and climate swings of a world, the windows when physical ways open between worlds, and the cultures that grow along busy roads between them. Every kind of thing shows these where they touch it: a land its wind, a world its seasons and windows, a community the cultures it belongs to, and a control that cannot apply to this kind of thing stays on screen and says why.'
      icon={CLIMES_ICON}
      tone='info'
    >
      <div data-surface='ClimesSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading winds, seasons and crossings' />
        ) : query.isError ? (
          <EmptyState
            icon={CLIMES_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'winds'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Winds, seasons and crossings'>
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
            <TabsContent value='winds' className='flex min-w-0 flex-col gap-6'>
              <WindsPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent
              value='seasons'
              className='flex min-w-0 flex-col gap-6'
            >
              <SeasonsPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent
              value='crossings'
              className='flex min-w-0 flex-col gap-6'
            >
              <CrossingsPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={blocked}
              />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
