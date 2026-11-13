import {
  Mesh,
  OrthographicCamera,
  PlaneGeometry,
  Scene,
  type ShaderMaterial,
  WebGLRenderer,
} from 'three'
import { shaderMaterial } from '@/features/cosmos/scene3d/materials'
import { DIMENSION_LOOK } from './dimensionLook'
import { type DimensionState, dimensionUniforms } from './dimensionMaterial'
import { cssColor, screenPalette } from './palette'
import { prepareCanvas } from './scalePaint'
import { DIMENSION_FRAGMENT, QUAD_VERTEX } from './shaders'

type Stage = {
  renderer: WebGLRenderer
  scene: Scene
  camera: OrthographicCamera
  material: ShaderMaterial
}

const FRAME = 0.8
const FALLBACK_REACH = 0.42

let stage: Stage | null | undefined

function stageOf(sample: DimensionState): Stage | null {
  if (stage !== undefined) return stage
  try {
    const renderer = new WebGLRenderer({
      canvas: document.createElement('canvas'),
      alpha: true,
      antialias: true,
      preserveDrawingBuffer: true,
    })
    renderer.setClearColor(0x000000, 0)
    const material = shaderMaterial({
      vertex: QUAD_VERTEX,
      fragment: DIMENSION_FRAGMENT,
      uniforms: dimensionUniforms(sample, screenPalette, true),
      blend: 'additive',
    })
    const scene = new Scene()
    scene.add(new Mesh(new PlaneGeometry(2, 2), material))
    const camera = new OrthographicCamera(-FRAME, FRAME, FRAME, -FRAME, 0, 2)
    camera.position.z = 1
    stage = { renderer, scene, camera, material }
  } catch {
    stage = null
  }
  return stage
}

function paintFallback(
  context: CanvasRenderingContext2D,
  state: DimensionState,
  width: number,
  height: number
) {
  const look = DIMENSION_LOOK[state.kind]
  const reach = Math.min(width, height) * FALLBACK_REACH
  const gradient = context.createRadialGradient(
    width / 2,
    height / 2,
    0,
    width / 2,
    height / 2,
    reach
  )
  gradient.addColorStop(0, cssColor(look.core))
  gradient.addColorStop(0.45, cssColor(look.body, 0.85))
  gradient.addColorStop(0.85, cssColor(look.edge, 0.6))
  gradient.addColorStop(1, cssColor(look.edge, 0))
  context.fillStyle = gradient
  context.beginPath()
  context.arc(width / 2, height / 2, reach, 0, Math.PI * 2)
  context.fill()
}

export function paintDimension(
  canvas: HTMLCanvasElement,
  state: DimensionState
) {
  const prepared = prepareCanvas(canvas)
  if (!prepared) return
  const { context, width, height } = prepared
  const ready = stageOf(state)
  if (!ready) {
    paintFallback(context, state, width, height)
    return
  }
  const ratio = window.devicePixelRatio || 1
  const side = Math.min(width, height)
  ready.renderer.setSize(
    Math.round(side * ratio),
    Math.round(side * ratio),
    false
  )
  for (const [name, value] of Object.entries(
    dimensionUniforms(state, screenPalette, true)
  )) {
    const target = ready.material.uniforms[name]
    if (target) target.value = value.value
  }
  ready.renderer.render(ready.scene, ready.camera)
  context.globalCompositeOperation = 'lighter'
  context.drawImage(
    ready.renderer.domElement,
    (width - side) / 2,
    (height - side) / 2,
    side,
    side
  )
  context.globalCompositeOperation = 'source-over'
}
