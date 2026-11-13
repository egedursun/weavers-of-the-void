import { useEffect, useMemo } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { HalfFloatType, Vector2, WebGLRenderTarget } from 'three'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'

export type Bloom = { strength: number; radius: number; threshold: number }

const SOFT_BLOOM: Bloom = { strength: 0.55, radius: 0.08, threshold: 0.95 }

export function PostEffects3D({
  samples,
  bloom = SOFT_BLOOM,
}: {
  samples: number
  bloom?: Bloom
}) {
  const gl = useThree((state) => state.gl)
  const scene = useThree((state) => state.scene)
  const camera = useThree((state) => state.camera)
  const size = useThree((state) => state.size)
  const ratio = useThree((state) => state.viewport.dpr)
  const composer = useMemo(() => {
    const target = new WebGLRenderTarget(1, 1, { type: HalfFloatType, samples })
    const effects = new EffectComposer(gl, target)
    effects.addPass(new RenderPass(scene, camera))
    effects.addPass(
      new UnrealBloomPass(
        new Vector2(1, 1),
        bloom.strength,
        bloom.radius,
        bloom.threshold
      )
    )
    effects.addPass(new OutputPass())
    return effects
  }, [gl, scene, camera, samples, bloom])
  useEffect(() => {
    composer.setPixelRatio(ratio)
    composer.setSize(size.width, size.height)
  }, [composer, size, ratio])
  useEffect(() => () => composer.dispose(), [composer])
  useFrame(() => composer.render(), 1)
  return null
}
