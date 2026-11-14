import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { BiasPanel } from './BiasPanel'
import { DietPanel } from './DietPanel'
import { MishapPanel } from './MishapPanel'
import { PurityPanel } from './PurityPanel'
import { WitchcraftPanel } from './WitchcraftPanel'
import { type FolkwaysNodeView, useNodeFolkways } from './api'
import { FOLKWAYS_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: FolkwaysNodeView) => number
}[] = [
  {
    key: 'body',
    label: 'Diet and nutrition',
    count: (data) =>
      (data.diet ? 1 : 0) + (data.nutrition ? 1 : 0) + data.needs.length,
  },
  {
    key: 'minds',
    label: 'Biases',
    count: (data) => data.biases.length,
  },
  {
    key: 'purity',
    label: 'Purity and rank',
    count: (data) =>
      (data.purity ? 1 : 0) +
      data.sources.length +
      data.methods.length +
      data.ranks.length,
  },
  {
    key: 'fortune',
    label: 'Misfortune, luck and witchcraft',
    count: (data) =>
      data.mishaps.length +
      data.beliefs.length +
      data.charms.length +
      data.accusations.length +
      data.hunts.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  mortal: 'body',
  son: 'minds',
  foreign_god: 'minds',
  people: 'purity',
  settlement: 'fortune',
  item: 'fortune',
}

export function FolkwaysSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeFolkways(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const props = { nodeId, kind, blocked: readOnlyReason }
  return (
    <Section
      id='section-folkways'
      title='Body, mind, purity and fortune'
      description='What a town, people or life eats and how well it is fed; the biases of those who decide; the purity, impurity and ranks a people keeps; and the misfortunes that befall, what folk blame them on, their beliefs about luck, their charms, and the accusations and witch hunts that follow. Every kind of thing shows these where they touch it: towns, peoples and lives are fed, mortals and gods decide, peoples and their folk keep purity, towns suffer misfortune and items become charms. A control that cannot apply to this kind of thing stays on screen and says why.'
      icon={FOLKWAYS_ICON}
      tone='gold'
    >
      <div
        data-surface='FolkwaysSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading diets, minds, purity and fortune' />
        ) : query.isError ? (
          <EmptyState
            icon={FOLKWAYS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'body'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Body, mind, purity and fortune'>
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
            <TabsContent value='body' className='flex min-w-0 flex-col gap-6'>
              <DietPanel
                nodeId={nodeId}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='minds' className='flex min-w-0 flex-col gap-6'>
              <BiasPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='purity' className='flex min-w-0 flex-col gap-6'>
              <PurityPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent
              value='fortune'
              className='flex min-w-0 flex-col gap-6'
            >
              <MishapPanel {...props} data={query.data} />
              <WitchcraftPanel {...props} data={query.data} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
