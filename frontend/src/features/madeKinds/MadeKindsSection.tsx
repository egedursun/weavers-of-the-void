import { useState } from 'react'
import { Hammer, Heart, Layers, Package, Truck, Utensils } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { useNodeKind } from '@/features/cycles/model'
import { StructureSectionsPanel, VesselSectionsPanel } from './IntegrityPanels'
import { KitPanel } from './KitPanel'
import { KitchenPanel, LeaningsPanel } from './LifePanels'
import { OwnKindsPanel } from './OwnKindsPanel'
import { VehiclesPanel } from './VehiclesPanel'
import { type ThingKinds, useThingKinds, useWorldKinds } from './api'

type Pane = 'vehicles' | 'kit' | 'kinds' | 'sections' | 'kitchen' | 'leanings'

const COMMUNITIES = new Set(['settlement', 'people'])

function panes(
  data: ThingKinds,
  kind: string | null
): { key: Pane; label: string; icon: typeof Truck; count: number }[] {
  const found: {
    key: Pane
    label: string
    icon: typeof Truck
    count: number
  }[] = [
    {
      key: 'vehicles',
      label: 'Vehicles',
      icon: Truck,
      count: data.vehicle_groups.length,
    },
    {
      key: 'kit',
      label: 'Stores and kit',
      icon: Package,
      count: data.stores.length + data.stacks.length,
    },
    {
      key: 'kinds',
      label: 'Kinds of its own',
      icon: Hammer,
      count:
        data.own.vehicle_types.length +
        data.own.unit_types.length +
        data.own.equipment_models.length +
        data.own.dishes.length +
        data.own.building_types.length,
    },
  ]
  if (data.vessel_sections.length || data.sections.length)
    found.push({
      key: 'sections',
      label: 'Sections',
      icon: Layers,
      count: data.vessel_sections.length + data.sections.length,
    })
  if (COMMUNITIES.has(kind ?? ''))
    found.push({
      key: 'kitchen',
      label: 'Kitchen',
      icon: Utensils,
      count: data.cooking.length,
    })
  if (data.attraction)
    found.push({
      key: 'leanings',
      label: 'Leanings and mind',
      icon: Heart,
      count: data.attraction.decline,
    })
  return found
}

export function MadeKindsSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useThingKinds(nodeId)
  const world = useWorldKinds(query.data?.world_id ?? null)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const types = world.data
  return (
    <Section
      id='section-made-kinds'
      title='Vehicles, kit and made kinds'
      description='The vehicles it holds with the damage to each of their sections, the weapons, armour and materiel it keeps or carries, and the named kinds it made: vehicle types, kinds of soldier, equipment models, dishes and building types. Structures and vessels show their sections, towns and peoples their kitchens, mortals their leanings and the state of their minds.'
      icon={Truck}
      tone='gold'
    >
      <div
        data-surface='MadeKindsSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading its vehicles, stores and kinds' />
        ) : query.isError ? (
          <EmptyState
            icon={Truck}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? 'vehicles'}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Vehicles, kit and made kinds'>
              {panes(query.data, kind).map(
                ({ key, label, icon: Icon, count }) => (
                  <TabsTrigger key={key} value={key}>
                    <Icon />
                    {label}
                    {count > 0 && (
                      <Badge size='sm' variant='secondary'>
                        {count}
                      </Badge>
                    )}
                  </TabsTrigger>
                )
              )}
            </TabsList>
            <TabsContent value='vehicles'>
              <VehiclesPanel
                nodeId={nodeId}
                data={query.data}
                types={types?.vehicle_types ?? []}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='kit'>
              <KitPanel
                nodeId={nodeId}
                data={query.data}
                models={types?.equipment_models ?? []}
                army={kind === 'army'}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='kinds'>
              <OwnKindsPanel
                nodeId={nodeId}
                data={query.data}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='sections'>
              {query.data.vessel_sections.length > 0 ? (
                <VesselSectionsPanel
                  nodeId={nodeId}
                  data={query.data}
                  blocked={readOnlyReason}
                />
              ) : (
                <StructureSectionsPanel
                  nodeId={nodeId}
                  data={query.data}
                  blocked={readOnlyReason}
                />
              )}
            </TabsContent>
            <TabsContent value='kitchen'>
              <KitchenPanel
                nodeId={nodeId}
                data={query.data}
                dishes={types?.dishes ?? []}
                blocked={readOnlyReason}
              />
            </TabsContent>
            <TabsContent value='leanings'>
              <LeaningsPanel
                nodeId={nodeId}
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
