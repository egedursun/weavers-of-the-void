import { BookOpen, Hammer } from 'lucide-react'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { BuildingTypePage } from './BuildingTypePage'
import { DishPage } from './DishPage'
import { EquipmentPage } from './EquipmentPage'
import { UnitTypePage } from './UnitTypePage'
import { VehicleTypePage } from './VehicleTypePage'
import { useWorldKinds } from './api'

function Missing() {
  return (
    <EmptyState
      icon={BookOpen}
      size='inline'
      title='Not yet made'
      description='Its make is laid down at the next epoch.'
    />
  )
}

function MadeBody({
  entityId,
  entityType,
  worldId,
}: {
  entityId: number
  entityType: string
  worldId: number | null
}) {
  const query = useWorldKinds(worldId)
  if (query.isPending) return <LoadingBlock label='Reading its make' />
  if (query.isError)
    return (
      <EmptyState
        icon={BookOpen}
        size='inline'
        title='Its make could not be read'
        description={query.error.message}
      />
    )
  const data = query.data
  if (entityType === 'vehicle_type') {
    const row = data.vehicle_types.find((item) => item.entity_id === entityId)
    return row ? (
      <VehicleTypePage row={row} models={data.equipment_models} />
    ) : (
      <Missing />
    )
  }
  if (entityType === 'unit_type') {
    const row = data.unit_types.find((item) => item.entity_id === entityId)
    return row ? (
      <UnitTypePage
        row={row}
        models={data.equipment_models}
        vehicles={data.vehicle_types}
      />
    ) : (
      <Missing />
    )
  }
  if (entityType === 'equipment_model') {
    const row = data.equipment_models.find(
      (item) => item.entity_id === entityId
    )
    return row ? <EquipmentPage row={row} /> : <Missing />
  }
  if (entityType === 'dish') {
    const row = data.dishes.find((item) => item.entity_id === entityId)
    return row ? <DishPage row={row} /> : <Missing />
  }
  const row = data.building_types.find((item) => item.entity_id === entityId)
  return row ? <BuildingTypePage row={row} /> : <Missing />
}

export function MadeEntitySection({
  entityId,
  entityType,
  worldId,
}: {
  entityId: number
  entityType: string
  worldId: number | null
}) {
  return (
    <Section
      id='section-made-type'
      title='Its make'
      description='How its makers made it: its parts, values and fittings, every one of them editable and holdable.'
      icon={Hammer}
      tone='gold'
    >
      <MadeBody entityId={entityId} entityType={entityType} worldId={worldId} />
    </Section>
  )
}
