import {
  AdditiveBlending,
  CustomBlending,
  NormalBlending,
  OneFactor,
  OneMinusSrcAlphaFactor,
  ShaderMaterial,
  type Blending,
  type IUniform,
  type Side,
  FrontSide,
} from 'three'
import { BILLBOARD_VERTEX } from './shaders/noise'

export type BlendMode = 'additive' | 'normal' | 'premultiplied'

type MaterialOptions = {
  vertex: string
  fragment: string
  uniforms: Record<string, IUniform>
  blend?: BlendMode
  side?: Side
  depthWrite?: boolean
  transparent?: boolean
}

const BLENDING: Record<BlendMode, Blending> = {
  additive: AdditiveBlending,
  normal: NormalBlending,
  premultiplied: CustomBlending,
}

export function shaderMaterial({
  vertex,
  fragment,
  uniforms,
  blend,
  side = FrontSide,
  depthWrite,
  transparent,
}: MaterialOptions): ShaderMaterial {
  const material = new ShaderMaterial({
    vertexShader: vertex,
    fragmentShader: fragment,
    uniforms,
    side,
    transparent: transparent ?? blend !== undefined,
    depthWrite: depthWrite ?? blend === undefined,
    blending: blend ? BLENDING[blend] : NormalBlending,
  })
  if (blend === 'premultiplied') {
    material.blendSrc = OneFactor
    material.blendDst = OneMinusSrcAlphaFactor
    material.premultipliedAlpha = true
  }
  return material
}

export function billboardMaterial(
  fragment: string,
  uniforms: Record<string, IUniform>,
  blend: BlendMode = 'additive'
): ShaderMaterial {
  return shaderMaterial({
    vertex: BILLBOARD_VERTEX,
    fragment,
    uniforms: { uSize: { value: 1 }, ...uniforms },
    blend,
  })
}

export function uniform<T>(value: T): IUniform<T> {
  return { value }
}
