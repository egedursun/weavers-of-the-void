import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { GiftLedger } from './GiftLedger'
import { KinshipPanel } from './KinshipPanel'
import { LabourRegimePanel } from './LabourRegimePanel'
import { NomadPanel } from './NomadPanel'
import { PlanPanel } from './PlanPanel'
import { SolidarityPanel } from './SolidarityPanel'
import { StressPanel } from './StressPanel'
import { type CyclesView, useNodeCycles } from './api'
import { CYCLES_ICON, TAB_ICONS } from './labels'
import { useNodeKind } from './model'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: CyclesView) => number
}[] = [
  {
    key: 'stress',
    label: 'Strains',
    count: (data) => (data.stress ? 1 : 0) + data.challenges.length,
  },
  {
    key: 'solidarity',
    label: 'Solidarity',
    count: (data) => (data.solidarity ? 1 : 0),
  },
  { key: 'plans', label: 'Long plans', count: (data) => data.plans.length },
  {
    key: 'gifts',
    label: 'Gifts',
    count: (data) =>
      data.gifts.length + data.debts.length + data.circuits.length,
  },
  {
    key: 'kin',
    label: 'Kin and birth',
    count: (data) =>
      (data.kinship ? 1 : 0) +
      (data.reproduction ? 1 : 0) +
      (data.caste ? 1 : 0) +
      data.alliances.length +
      data.legacies.length,
  },
  {
    key: 'nomads',
    label: 'Nomads',
    count: (data) => (data.camp ? 1 : 0) + data.confederations.length,
  },
  {
    key: 'labour',
    label: 'Bound labour',
    count: (data) =>
      data.indentures.length + (data.market ? 1 : 0) + data.manumissions.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  polity: 'stress',
  people: 'kin',
  settlement: 'labour',
  mortal: 'gifts',
  house: 'kin',
  son: 'gifts',
  foreign_god: 'gifts',
}

export function CyclesSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeCycles(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  return (
    <Section
      id='section-cycles'
      title='Cycles, gifts, kin and bound labour'
      description='The strains that turn a realm through growth, stagflation, crisis and depression; the solidarity forged at frontiers and lost in ease; the challenges met; long plans that outlive their authors; the gift ledger and the debts of gods; ways of kin and birth; camps on the move; and labour bound by term, debt or chain.'
      icon={CYCLES_ICON}
      tone='verdigris'
    >
      <div data-surface='CyclesSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading the cycles and the ledgers' />
        ) : query.isError ? (
          <EmptyState
            icon={CYCLES_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'gifts'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Cycles, gifts, kin and bound labour'>
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
            <TabsContent value='stress'>
              <StressPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='solidarity'>
              <SolidarityPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='plans'>
              <PlanPanel
                nodeId={nodeId}
                plans={query.data.plans}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='gifts'>
              <GiftLedger
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='kin'>
              <KinshipPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='nomads'>
              <NomadPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='labour'>
              <LabourRegimePanel
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
