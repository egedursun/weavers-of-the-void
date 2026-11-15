import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import {
  BuildingPanel,
  ContainersPanel,
  PilotsPanel,
  VaultsPanel,
  WaterPanel,
  WritingPanel,
} from './MeansPanels'
import { type MeansNodeView, useMeansAction, useNodeMeans } from './api'
import { MEANS_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: MeansNodeView) => number
}[] = [
  {
    key: 'writing',
    label: 'Writing',
    count: (data) => data.works.length + (data.custom ? 1 : 0),
  },
  { key: 'vaults', label: 'Vaults', count: (data) => data.vaults.length },
  { key: 'water', label: 'Water lifting', count: (data) => data.lifts.length },
  { key: 'pilots', label: 'Pilots', count: (data) => data.kits.length },
  {
    key: 'containers',
    label: 'Containers',
    count: (data) => data.containers.length,
  },
  {
    key: 'building',
    label: 'Building material',
    count: (data) => (data.building ? 1 : 0),
  },
]

const FIRST_PANE: Record<string, Pane> = {
  structure: 'building',
  settlement: 'water',
  people: 'writing',
  item: 'writing',
}

export function MeansSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeMeans(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const running = useMeansAction(
    'means:run',
    (_: void) => ({}),
    'Every medium, vault, device, instrument and container is read'
  )
  const blocked = readOnlyReason
  return (
    <Section
      id='section-means'
      title='Means of craft: writing, vaults, water, pilots, containers and building'
      description='What this thing writes on, how its stores are locked, how its town lifts water, what instruments its pilots use, the containers it keeps and what its works are built of. Every kind of thing shows these where they touch it, and a control that cannot apply here stays on screen and says why.'
      icon={MEANS_ICON}
      tone='gold'
    >
      <div data-surface='MeansSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading writing, vaults, water, pilots and containers' />
        ) : query.isError ? (
          <EmptyState
            icon={MEANS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'writing'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Writing, vaults, water, pilots, containers and building'>
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
              value='writing'
              className='flex min-w-0 flex-col gap-6'
            >
              <WritingPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent value='vaults' className='flex min-w-0 flex-col gap-6'>
              <VaultsPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent value='water' className='flex min-w-0 flex-col gap-6'>
              <WaterPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent value='pilots' className='flex min-w-0 flex-col gap-6'>
              <PilotsPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent
              value='containers'
              className='flex min-w-0 flex-col gap-6'
            >
              <ContainersPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent
              value='building'
              className='flex min-w-0 flex-col gap-6'
            >
              <BuildingPanel data={query.data} blocked={blocked} />
            </TabsContent>
          </Tabs>
        )}
        <StepButton
          icon={MEANS_ICON}
          label='Read the means of craft now'
          busy={why(blocked, running.isPending)}
          onClick={() => running.mutate()}
        />
      </div>
    </Section>
  )
}
