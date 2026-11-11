import { type RefObject, createContext, useContext } from 'react'
import { Vector3 } from 'three'
import { type CosmosIndex } from '../model/cosmosModel'
import { type Layout3D } from '../model/layout3d'
import { type SharedGeometries } from './geometries'
import { type QualityPreset } from './quality'

export type ScreenPoint = {
  x: number
  y: number
  radius: number
  visible: boolean
}

export type RouteCurve = {
  a: Vector3
  b: Vector3
  c: Vector3
  open: boolean
}

export type Hover =
  | { kind: 'world'; id: number }
  | { kind: 'star'; id: number }
  | { kind: 'route'; id: number }
  | { kind: 'voyage'; id: number }
  | null

export type FrameState = {
  time: number
  reduced: boolean
  width: number
  height: number
  worldPosition: Map<number, Vector3>
  worldScale: Map<number, number>
  worldScreen: Map<number, ScreenPoint>
  starScreen: Map<number, ScreenPoint>
  routeCurves: Map<number, RouteCurve>
  routeScreen: Map<number, Float32Array>
  voyagePosition: Map<number, Vector3>
  voyageScreen: Map<number, ScreenPoint>
  hover: Hover
  selectedWorld: number | undefined
  selectedStar: number | undefined
  detailStar: number | undefined
  highlightedRoute: number | undefined
}

export function createFrameState(): FrameState {
  return {
    time: 0,
    reduced: false,
    width: 1,
    height: 1,
    worldPosition: new Map(),
    worldScale: new Map(),
    worldScreen: new Map(),
    starScreen: new Map(),
    routeCurves: new Map(),
    routeScreen: new Map(),
    voyagePosition: new Map(),
    voyageScreen: new Map(),
    hover: null,
    detailStar: undefined,
    selectedWorld: undefined,
    selectedStar: undefined,
    highlightedRoute: undefined,
  }
}

export type SceneValue = {
  frameRef: RefObject<FrameState>
  layout: Layout3D
  index: CosmosIndex
  preset: QualityPreset
  routeBend: Map<number, number>
  geometries: SharedGeometries
  labels: Map<string, HTMLElement>
}

export const SceneContext = createContext<SceneValue | null>(null)

export function useScene(): SceneValue {
  const value = useContext(SceneContext)
  if (!value) throw new Error('useScene must be used inside the cosmos scene')
  return value
}

export function worldVector(frame: FrameState, id: number): Vector3 {
  let vector = frame.worldPosition.get(id)
  if (!vector) {
    vector = new Vector3()
    frame.worldPosition.set(id, vector)
  }
  return vector
}
