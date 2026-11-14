import { useState } from 'react'
import { Leaf } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { BodyPanel } from './BodyPanel'
import { BondsPanel } from './BondsPanel'
import { SensesPanel } from './SensesPanel'
import { SoilPanel } from './SoilPanel'
import { type NatureNodeView, useNatureAction, useNodeNature } from './api'
import { NATURE_ICON, TAB_ICONS } from './labels'

type Pane = keyof typeof TAB_ICONS

const PANES: {
  key: Pane
  label: string
  count: (data: NatureNodeView) => number
}[] = [
  {
    key: 'body',
    label: 'Body and seasons',
    count: (data) =>
      Number(Boolean(data.kind_profile || data.folk_profile || data.plant)),
  },
  { key: 'senses', label: 'Senses', count: (data) => data.senses.length },
  {
    key: 'bonds',
    label: 'Bonds between kinds',
    count: (data) => data.bonds.length,
  },
  {
    key: 'soil',
    label: 'Soil and cultures',
    count: (data) =>
      data.cultures.length + (data.soil ? 1 : 0) + data.defences.length,
  },
]

const FIRST_PANE: Record<string, Pane> = {
  region: 'soil',
  settlement: 'soil',
  faction: 'soil',
  structure: 'soil',
  house: 'soil',
  mortal: 'senses',
}

export function NatureSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeNature(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const running = useNatureAction(
    'nature:run',
    (_: void) => ({}),
    'Every soil, culture, bond and sleeper is read'
  )
  const blocked = readOnlyReason
  return (
    <Section
      id='section-nature'
      title='Living nature: bodies, senses, bonds and soils'
      description='How the kinds and peoples of this thing live through the seasons, what they sense, how kinds bind one another, the life of the soil, the defences of plants and the ferment cultures kept here. Every kind of thing shows these where they touch it, and a control that cannot apply here stays on screen and says why.'
      icon={NATURE_ICON}
      tone='verdigris'
    >
      <div data-surface='NatureSection' className='flex min-w-0 flex-col gap-6'>
        {query.isPending ? (
          <LoadingBlock label='Reading bodies, senses, bonds and soils' />
        ) : query.isError ? (
          <EmptyState
            icon={NATURE_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? FIRST_PANE[kind ?? ''] ?? 'body'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Bodies, senses, bonds and soils'>
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
              <BodyPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent value='senses' className='flex min-w-0 flex-col gap-6'>
              <SensesPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent value='bonds' className='flex min-w-0 flex-col gap-6'>
              <BondsPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent value='soil' className='flex min-w-0 flex-col gap-6'>
              <SoilPanel
                nodeId={nodeId}
                kind={kind}
                data={query.data}
                blocked={blocked}
              />
            </TabsContent>
          </Tabs>
        )}
        <div className='flex min-w-0 flex-wrap gap-2'>
          <StepButton
            icon={Leaf}
            label='Read living nature now'
            busy={why(blocked, running.isPending)}
            onClick={() => running.mutate()}
          />
        </div>
      </div>
    </Section>
  )
}
