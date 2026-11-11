import { Color, type Material, MeshStandardMaterial } from 'three'
import { tokenHex } from '@/features/cosmography/visual/palette'

const TINT_BLEND = 0.2
const made = new WeakMap<Material, Map<string, Material>>()

export function shared(
  material: Material,
  tint: string | null,
  dim: number
): Material {
  if (!(material instanceof MeshStandardMaterial) || (!tint && dim === 1))
    return material
  const key = `${tint ?? ''}|${dim.toFixed(2)}`
  const known = made.get(material) ?? new Map<string, Material>()
  made.set(material, known)
  const found = known.get(key)
  if (found) return found
  const copy = material.clone()
  if (tint)
    copy.color = new Color(tint).lerp(
      new Color(tokenHex('--cosmos-bone')),
      TINT_BLEND
    )
  if (dim !== 1) copy.color.multiplyScalar(dim)
  known.set(key, copy)
  return copy
}
