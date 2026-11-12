import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { LearningPanel } from './LearningPanel'
import { LineagePanel } from './LineagePanel'
import { PatronagePanel } from './PatronagePanel'
import { RulePanel } from './RulePanel'
import { type RegimeNodeView, useNodeRegime } from './api'
import { REGIME_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: RegimeNodeView) => number
}[] = [
  {
    key: 'rule',
    label: 'Rule',
    count: (data) => (data.regime ? 1 : 0) + data.members.length,
  },
  {
    key: 'patronage',
    label: 'Patrons and power',
    count: (data) =>
      data.ties.length +
      data.offices.length +
      data.bases.length +
      (data.power_base ? 1 : 0),
  },
  {
    key: 'lineages',
    label: 'Lines and designs',
    count: (data) =>
      (data.lineage ? 1 : 0) + data.kin_lines.length + data.breeding.length,
  },
  {
    key: 'learning',
    label: 'Learning',
    count: (data) =>
      (data.examination ? 1 : 0) +
      data.sittings.length +
      data.credentials.length +
      (data.freedom ? 1 : 0) +
      data.schools.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  polity: 'rule',
  mortal: 'patronage',
  house: 'lineages',
  people: 'lineages',
  structure: 'learning',
  theory: 'learning',
  ideology: 'learning',
}

export function RegimeSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeRegime(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  return (
    <Section
      id='section-regime'
      title='Rule, patronage, lines and learning'
      description='Who chooses the ruler and what the ruling circle is paid; the kinds of legitimacy and the crisis at a founder’s death; the time horizon that sets how hard a realm is taxed; patrons and clients, seats bought and sinecures, the power bases of great subjects and the guard against coups; lines that take sides in feuds and designs that steer marriages; examinations, credentials, the freedom of learning and the schools of thought.'
      icon={REGIME_ICON}
      tone='gold'
    >
      <div data-surface='RegimeSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading the rule, the patrons and the schools' />
        ) : query.isError ? (
          <EmptyState
            icon={REGIME_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'patronage'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Rule, patronage, lines and learning'>
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
            <TabsContent value='rule'>
              <RulePanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='patronage'>
              <PatronagePanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='lineages'>
              <LineagePanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='learning'>
              <LearningPanel
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
