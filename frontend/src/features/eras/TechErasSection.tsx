import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { EraPanel } from './EraPanel'
import { LadderPanel } from './LadderPanel'
import { ProgrammesPanel } from './ProgrammesPanel'
import { type ErasNodeView, useNodeEras } from './api'
import { TAB_ICONS, TECH_ERAS_ICON } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: ErasNodeView) => number
}[] = [
  { key: 'era', label: 'Era', count: (data) => data.channels.length },
  {
    key: 'ladder',
    label: 'Techniques',
    count: (data) => data.techniques.filter((row) => row.held).length,
  },
  {
    key: 'programmes',
    label: 'Programmes',
    count: (data) => data.programmes.length,
  },
]

export function TechErasSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeEras(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const props = { blocked: readOnlyReason }
  return (
    <Section
      id='section-tech-eras'
      title='Technology eras and programmes'
      description='The era this thing has reached through the techniques its town, people or realm knows, what each technique changes, and the programmes realms run toward the greatest of them. Every kind of thing shows the era of the town, people or realm it belongs to; a control that cannot apply here stays on screen and says why.'
      icon={TECH_ERAS_ICON}
      tone='gold'
    >
      <div
        data-surface='TechErasSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading eras, techniques and programmes' />
        ) : query.isError ? (
          <EmptyState
            icon={TECH_ERAS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? (kind === 'polity' ? 'programmes' : 'era')}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Era, techniques and programmes'>
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
            <TabsContent value='era' className='flex min-w-0 flex-col gap-6'>
              <EraPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='ladder' className='flex min-w-0 flex-col gap-6'>
              <LadderPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent
              value='programmes'
              className='flex min-w-0 flex-col gap-6'
            >
              <ProgrammesPanel {...props} data={query.data} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
