import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { ArcanePanel } from './ArcanePanel'
import { LearningPanel } from './LearningPanel'
import { MoneyPanel } from './MoneyPanel'
import { TradesPanel } from './TradesPanel'
import { type CraftsNodeView, useNodeCrafts } from './api'
import { CRAFTS_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: CraftsNodeView) => number
}[] = [
  {
    key: 'trades',
    label: 'Grounds and works',
    count: (data) => data.grounds.length + data.works.length,
  },
  {
    key: 'money',
    label: 'Insurance and rights',
    count: (data) =>
      data.policies.length + data.rights.length + (data.insurer ? 1 : 0),
  },
  {
    key: 'learning',
    label: 'Aids, games and numbers',
    count: (data) =>
      data.aids.length + (data.clock ? 1 : 0) + (data.numbers ? 1 : 0),
  },
  {
    key: 'arcane',
    label: 'Magic and spirits',
    count: (data) =>
      data.affinities.length + data.links.length + data.spirits.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  mortal: 'learning',
  people: 'learning',
  settlement: 'trades',
  resource: 'trades',
  species: 'trades',
  faction: 'money',
  house: 'money',
  artwork: 'money',
  rite: 'money',
  region: 'arcane',
}

export function CraftsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeCrafts(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const props = { nodeId, kind, blocked: readOnlyReason }
  return (
    <Section
      id='section-crafts'
      title='Trades, aids, games and magic of things'
      description='The fishing and hunting grounds and chemical works of a place, the insurance and held rights of those who trade and make, the aids, clocks, games and reckoning of a people, and the affinities of materials, the links of casters and the spirits of feeling in a land. Every kind of thing shows these where they touch it, and a control that cannot apply to this kind of thing stays on screen and says why.'
      icon={CRAFTS_ICON}
      tone='verdigris'
    >
      <div data-surface='CraftsSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading trades, aids, games and magic' />
        ) : query.isError ? (
          <EmptyState
            icon={CRAFTS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'trades'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Trades, aids, games and magic'>
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
            <TabsContent value='trades' className='flex min-w-0 flex-col gap-6'>
              <TradesPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='money' className='flex min-w-0 flex-col gap-6'>
              <MoneyPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent
              value='learning'
              className='flex min-w-0 flex-col gap-6'
            >
              <LearningPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='arcane' className='flex min-w-0 flex-col gap-6'>
              <ArcanePanel {...props} data={query.data} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
