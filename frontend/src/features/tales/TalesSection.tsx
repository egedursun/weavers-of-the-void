import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { AgesPanel } from './AgesPanel'
import { SetupsPanel, TalesPanel } from './TalePanels'
import {
  FormationPanel,
  SeasonsPanel,
  TransformationPanel,
} from './WorldPanels'
import { type TalesNodeView, useNodeTales } from './api'
import { TAB_ICONS, TALES_ICON } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: TalesNodeView) => number
}[] = [
  {
    key: 'tales',
    label: 'Tales and setups',
    count: (data) => data.arcs.length + data.setups.length,
  },
  {
    key: 'world',
    label: 'Forming, seasons and remaking',
    count: (data) =>
      (data.formation ? 1 : 0) +
      (data.season ? 1 : 0) +
      data.forecasts.length +
      data.transformations.length,
  },
  {
    key: 'ages',
    label: 'Ages and echoes',
    count: (data) => data.ages.length + data.echoes.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  world: 'world',
  creator: 'ages',
}

export function TalesSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeTales(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const props = { nodeId, kind, blocked: readOnlyReason }
  return (
    <Section
      id='section-tales'
      title='Tales, seasons and ages'
      description='The tales read in lives, with their figures, beats and drama, and what was set up to be paid off; the forming of a world from its disc and bombardment, its irregular seasons and the forecasts of its peoples, and the plans that remake its land; and the ages of the cosmos with the great lives that echo between them. Every kind of thing shows these records where they touch it: mortals, houses, realms and gods carry tales, worlds keep their forming and seasons, peoples forecast, holders of plans remake the land and the creator watches the ages. A control that cannot apply to this kind of thing stays on screen and says why.'
      icon={TALES_ICON}
      tone='gold'
    >
      <div data-surface='TalesSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading the tales, the seasons and the ages' />
        ) : query.isError ? (
          <EmptyState
            icon={TALES_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'tales'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Tales, seasons and ages'>
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
            <TabsContent value='tales' className='flex min-w-0 flex-col gap-6'>
              <TalesPanel {...props} data={query.data} />
              <SetupsPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='world' className='flex min-w-0 flex-col gap-6'>
              <FormationPanel {...props} data={query.data} />
              <SeasonsPanel {...props} data={query.data} />
              <TransformationPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='ages' className='flex min-w-0 flex-col gap-6'>
              <AgesPanel {...props} data={query.data} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
