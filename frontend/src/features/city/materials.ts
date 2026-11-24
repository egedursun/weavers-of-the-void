import { Color, type Material, MeshStandardMaterial } from 'three'
import { tokenHex } from '@/features/cosmography/visual/palette'

const TINT_BLEND = 0.2
const GLOW = 0.18
const made = new WeakMap<Material, Map<string, Material>>()

export function shared(
  material: Material,
  tint: string | null,
  dim: number,
  bare = false,
  glow = false
): Material {
  if (
    !(material instanceof MeshStandardMaterial) ||
    (!tint && dim === 1 && !bare && !glow)
  )
    return material
  const key = `${tint ?? ''}|${dim.toFixed(2)}|${bare ? 'bare' : 'mapped'}|${glow ? 'glow' : 'dull'}`
  const known = made.get(material) ?? new Map<string, Material>()
  made.set(material, known)
  const found = known.get(key)
  if (found) return found
  const copy = material.clone()
  if (bare) {
    copy.map = null
    copy.roughness = 1
  }
  if (tint)
    copy.color = new Color(tint).lerp(
      new Color(tokenHex('--cosmos-bone')),
      TINT_BLEND
    )
  if (dim !== 1) copy.color.multiplyScalar(dim)
  if (glow && tint) {
    copy.emissive = new Color(tint)
    copy.emissiveIntensity = GLOW
  }
  known.set(key, copy)
  return copy
}
