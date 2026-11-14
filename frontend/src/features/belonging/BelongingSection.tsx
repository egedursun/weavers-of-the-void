import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { IdentityPanel } from './IdentityPanel'
import { PeersPanel } from './PeersPanel'
import { SanctuaryPanel } from './SanctuaryPanel'
import { SatirePanel } from './SatirePanel'
import { type BelongingNodeView, useNodeBelonging } from './api'
import { BELONGING_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: BelongingNodeView) => number
}[] = [
  {
    key: 'identities',
    label: 'Identities',
    count: (data) => data.identities.length,
  },
  {
    key: 'peers',
    label: 'Children at play',
    count: (data) => data.peer_groups.length,
  },
  {
    key: 'sanctuary',
    label: 'Sanctuary',
    count: (data) => data.sanctuaries.length + (data.sanctuary_law ? 1 : 0),
  },
  {
    key: 'satire',
    label: 'Satire and fools',
    count: (data) => data.satires.length + (data.jester ? 1 : 0),
  },
]

const FIRST_PANE: Record<string, Pane> = {
  structure: 'sanctuary',
  artwork: 'satire',
}

export function BelongingSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeBelonging(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const props = { nodeId, kind, blocked: readOnlyReason }
  return (
    <Section
      id='section-belonging'
      title='Who they are, children at play, sanctuary and satire'
      description='The identities a town, people or mortal holds and how much each matters, the peer groups its children play in, the sanctuary given to the hunted and the realm’s law of it, and the jests and satires told against rulers. Every kind of thing shows these where they touch it, and a control that cannot apply to this kind of thing stays on screen and says why.'
      icon={BELONGING_ICON}
      tone='gold'
    >
      <div
        data-surface='BelongingSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading identities, play, sanctuary and satire' />
        ) : query.isError ? (
          <EmptyState
            icon={BELONGING_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'identities'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Identities, play, sanctuary and satire'>
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
              value='identities'
              className='flex min-w-0 flex-col gap-6'
            >
              <IdentityPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='peers' className='flex min-w-0 flex-col gap-6'>
              <PeersPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent
              value='sanctuary'
              className='flex min-w-0 flex-col gap-6'
            >
              <SanctuaryPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='satire' className='flex min-w-0 flex-col gap-6'>
              <SatirePanel {...props} data={query.data} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
