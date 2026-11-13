import { BookOpen } from 'lucide-react'
import { EmptyState, LoadingBlock } from '@/components/domain'
import { BuildingTypePage } from './BuildingTypePage'
import { DishPage } from './DishPage'
import { EquipmentPage } from './EquipmentPage'
import { UnitTypePage } from './UnitTypePage'
import { VehicleTypePage } from './VehicleTypePage'
import { useWorldKinds } from './api'
import { type KindSelection } from './kindKeys'

function Missing() {
  return (
    <EmptyState
      icon={BookOpen}
      title='No such type'
      description='This type is no longer part of the world.'
    />
  )
}

export function KindPage({ selection }: { selection: KindSelection }) {
  const query = useWorldKinds(selection.worldId)
  if (query.isPending) return <LoadingBlock label='Reading the type' />
  if (query.isError)
    return (
      <EmptyState
        icon={BookOpen}
        title='The type could not be read'
        description={query.error.message}
      />
    )
  const data = query.data
  if (selection.kind === 'vehicle') {
    const row = data.vehicle_types.find((item) => item.id === selection.id)
    return row ? (
      <VehicleTypePage row={row} models={data.equipment_models} />
    ) : (
      <Missing />
    )
  }
  if (selection.kind === 'unit') {
    const row = data.unit_types.find((item) => item.id === selection.id)
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
  if (selection.kind === 'equipment') {
    const row = data.equipment_models.find((item) => item.id === selection.id)
    return row ? <EquipmentPage row={row} /> : <Missing />
  }
  if (selection.kind === 'dish') {
    const row = data.dishes.find((item) => item.id === selection.id)
    return row ? <DishPage row={row} /> : <Missing />
  }
  const row = data.building_types.find((item) => item.id === selection.id)
  return row ? <BuildingTypePage row={row} /> : <Missing />
}
