import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { BodyPanel } from './BodyPanel'
import { CivicsPanel } from './CivicsPanel'
import { FolkPanel } from './FolkPanel'
import { TownPanel } from './TownPanel'
import { type CustomsNodeView, useNodeCustoms } from './api'
import { CUSTOMS_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: CustomsNodeView) => number
}[] = [
  {
    key: 'folk',
    label: 'Folk customs',
    count: (data) =>
      data.revivals.length +
      data.intoxicants.length +
      data.mark_customs.length +
      data.budgets.length +
      data.age_sets.length +
      (data.naming ? 1 : 0),
  },
  {
    key: 'body',
    label: 'Marks, names and belonging',
    count: (data) =>
      data.marks.length + data.names.length + (data.membership ? 1 : 0),
  },
  {
    key: 'town',
    label: 'Town life',
    count: (data) =>
      data.taverns.length +
      data.welfare.length +
      (data.commute ? 1 : 0) +
      (data.cooperative ? 1 : 0),
  },
  {
    key: 'civics',
    label: 'Civics',
    count: (data) =>
      data.evidence.length +
      data.categories.length +
      (data.border ? 1 : 0) +
      (data.relief ? 1 : 0) +
      (data.measures ? 1 : 0),
  },
]

const FIRST_PANE: Record<string, Pane> = {
  mortal: 'body',
  people: 'folk',
  settlement: 'town',
  structure: 'town',
  faction: 'town',
  polity: 'civics',
}

export function CustomsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeCustoms(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const props = { nodeId, kind, blocked: readOnlyReason }
  return (
    <Section
      id='section-customs'
      title='Customs, town life and civics'
      description='The customs of a people: movements against the ways pressed on it, intoxicants, the marks it reads, the year of each class, its naming and its age-sets; the marks, names, age-set and standing of a mortal; the taverns, houses of welfare, way to work and cooperatives of a town; and the evidence, citizenship, borders, relief and measures of a realm. Every kind of thing shows these where they touch it, and a control that cannot apply to this kind of thing stays on screen and says why.'
      icon={CUSTOMS_ICON}
      tone='gold'
    >
      <div
        data-surface='CustomsSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading customs, town life and civics' />
        ) : query.isError ? (
          <EmptyState
            icon={CUSTOMS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'folk'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Customs, town life and civics'>
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
            <TabsContent value='folk' className='flex min-w-0 flex-col gap-6'>
              <FolkPanel data={query.data} blocked={readOnlyReason} />
            </TabsContent>
            <TabsContent value='body' className='flex min-w-0 flex-col gap-6'>
              <BodyPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='town' className='flex min-w-0 flex-col gap-6'>
              <TownPanel {...props} data={query.data} />
            </TabsContent>
            <TabsContent value='civics' className='flex min-w-0 flex-col gap-6'>
              <CivicsPanel {...props} data={query.data} />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </Section>
  )
}
