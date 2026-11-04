import { formatInteger } from '@/lib/format'
import { type StructureView, UNIT_LABEL } from './structureLabels'

export function standing(view: StructureView): boolean {
  return (
    view.construction_state === 'complete' ||
    view.construction_state === 'damaged'
  )
}

export function raising(view: StructureView): boolean {
  return (
    view.construction_state === 'planned' ||
    view.construction_state === 'building'
  )
}

export function capacityText(view: StructureView): string {
  const unit = UNIT_LABEL[view.capacity_unit]
  return unit ? `${formatInteger(view.capacity)} ${unit}` : 'None'
}
