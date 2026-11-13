import '@/styles/index.css'
import { describe, expect, it } from 'vitest'
import { paintDimension } from './dimensionPaint'
import {
  DIMENSION_TOKEN,
  type FormInput,
  GALAXY_LOOK,
  type GalaxyShape,
} from './galaxyForm'
import { paintGalaxy } from './galaxyPaint'
import { paintCluster } from './scalePaint'

const SIDE = 96
const GRID = 16
const DISTINCT = 0.02

const SHAPE: GalaxyShape = {
  core_reach_pct: 8,
  bulge_reach_pct: 18,
  bar_reach_pct: 30,
  inner_reach_pct: 40,
  disc_reach_pct: 100,
  halo_reach_pct: 130,
  arm_width_deg: 28,
  arm_wind_deg: 180,
  barred_types: ['barred_spiral', 'forged'],
  spiral_types: [
    'active',
    'barred_spiral',
    'crowned',
    'dreaming',
    'ember',
    'flocculent_spiral',
    'forged',
    'grand_design_spiral',
    'living',
    'low_surface_brightness',
    'mirror',
    'spiral',
    'veiled',
  ],
}

const CLUSTERS = [
  'galaxy_group',
  'local_group',
  'poor_cluster',
  'rich_cluster',
  'supercluster',
  'filament',
  'wall',
  'void',
  'crown_cluster',
  'drowned_cluster',
  'forge_cluster',
  'dream_cluster',
  'mirror_cluster',
] as const

function canvas(): HTMLCanvasElement {
  const element = document.createElement('canvas')
  element.style.width = `${SIDE}px`
  element.style.height = `${SIDE}px`
  element.style.display = 'block'
  document.body.append(element)
  return element
}

function signature(element: HTMLCanvasElement): number[] {
  const context = element.getContext('2d')
  if (!context) return []
  const { data, width, height } = context.getImageData(
    0,
    0,
    element.width,
    element.height
  )
  const cells = new Array<number>(GRID * GRID * 3).fill(0)
  for (let y = 0; y < height; y += 1)
    for (let x = 0; x < width; x += 1) {
      const cell =
        (Math.floor((y * GRID) / height) * GRID +
          Math.floor((x * GRID) / width)) *
        3
      const offset = (y * width + x) * 4
      cells[cell] += data[offset]
      cells[cell + 1] += data[offset + 1]
      cells[cell + 2] += data[offset + 2]
    }
  const per = (width * height) / (GRID * GRID)
  element.remove()
  return cells.map((value) => value / per / 255)
}

function apart(a: number[], b: number[]): number {
  return (
    a.reduce((total, value, index) => total + Math.abs(value - b[index]), 0) /
    a.length
  )
}

function alike(signatures: Map<string, number[]>): string[] {
  const keys = [...signatures.keys()]
  const close: string[] = []
  keys.forEach((left, index) =>
    keys.slice(index + 1).forEach((right) => {
      const gap = apart(signatures.get(left) ?? [], signatures.get(right) ?? [])
      if (gap < DISTINCT) close.push(`${left} ~ ${right} (${gap.toFixed(4)})`)
    })
  )
  return close
}

describe('the kinds of the heavens', () => {
  it('draws every dimension kind in its own form', () => {
    const signatures = new Map(
      (Object.keys(DIMENSION_TOKEN) as (keyof typeof DIMENSION_TOKEN)[]).map(
        (kind) => {
          const element = canvas()
          paintDimension(element, {
            id: 1,
            kind,
            veil: 50,
            stability: 70,
            magic: 50,
            time_factor: 1,
          })
          return [kind, signature(element)]
        }
      )
    )
    expect(alike(signatures)).toEqual([])
  })

  it('draws every cluster kind in its own arrangement', () => {
    const signatures = new Map(
      CLUSTERS.map((kind) => {
        const element = canvas()
        paintCluster(element, { id: 1, kind, galaxies: 6, heat: 40 })
        return [kind, signature(element)]
      })
    )
    expect(alike(signatures)).toEqual([])
  })

  it('draws every galaxy type in its own shape', () => {
    const signatures = new Map(
      (Object.keys(GALAXY_LOOK) as FormInput['galaxy_type'][]).map((type) => {
        const element = canvas()
        paintGalaxy(
          element,
          {
            id: 1,
            galaxy_type: type,
            radius: 900,
            arm_count: 2,
            nucleus: 'dormant',
            star_formation: 50,
            metallicity: 50,
            age_stage: 'mature',
            leak: 0,
            merge_progress: 0,
          },
          SHAPE,
          [],
          GALAXY_LOOK[type].view ?? 0.5,
          3000
        )
        return [type, signature(element)]
      })
    )
    expect(alike(signatures)).toEqual([])
  })
})
