import { FIELD_LABELS } from '@/features/entity/environment/labels'
import { type LandScene } from './api'

type Cover = LandScene['tiles'][number]['cover']
export type ShareField =
  | 'forest_cover'
  | 'farmed'
  | 'grazed'
  | 'wetland'
  | 'cleared'
  | 'mined'
  | 'built'
  | 'soil_fertility'
  | 'magic_density'

export const FIELD_OF_COVER: Record<Cover, ShareField | null> = {
  open: null,
  forest: 'forest_cover',
  fields: 'farmed',
  pasture: 'grazed',
  marsh: 'wetland',
  cleared: 'cleared',
  built: 'built',
  mined: 'mined',
}
export const SHARE_LABEL: Record<ShareField, string> = {
  forest_cover: FIELD_LABELS.forest_cover ?? 'Forest cover',
  farmed: 'Farmland',
  grazed: 'Pasture',
  wetland: FIELD_LABELS.wetland ?? 'Wetland',
  cleared: FIELD_LABELS.cleared ?? 'Cleared land',
  mined: 'Mines',
  built: 'Built up',
  soil_fertility: FIELD_LABELS.soil_fertility ?? 'Soil fertility',
  magic_density: FIELD_LABELS.magic_density ?? 'Magic density',
}
