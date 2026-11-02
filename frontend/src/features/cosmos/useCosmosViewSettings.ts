import { useCallback, useState } from 'react'

export type CosmosViewMode = '3d' | '2d'
export type CosmosQuality = 'low' | 'medium' | 'high'

export const COSMOS_QUALITIES: readonly CosmosQuality[] = [
  'low',
  'medium',
  'high',
]

export const QUALITY_LABEL: Record<CosmosQuality, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
}

const VIEW_KEY = 'aerona.cosmos.view'
const QUALITY_KEY = 'aerona.cosmos.quality'
const DEFAULT_VIEW: CosmosViewMode = '3d'
const DEFAULT_QUALITY: CosmosQuality = 'medium'
const SOFTWARE_QUALITY: CosmosQuality = 'low'

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    return
  }
}

const SOFTWARE_RENDERER = /swiftshader|llvmpipe|softpipe|software|basic render/i

type WebGLProbe = { available: boolean; software: boolean }

let webglProbe: WebGLProbe | null = null

function probeWebGL(): WebGLProbe {
  if (webglProbe !== null) return webglProbe
  try {
    const gl = document.createElement('canvas').getContext('webgl2')
    if (gl === null) {
      webglProbe = { available: false, software: false }
    } else {
      const debug = gl.getExtension('WEBGL_debug_renderer_info')
      const renderer = String(
        gl.getParameter(debug ? debug.UNMASKED_RENDERER_WEBGL : gl.RENDERER)
      )
      gl.getExtension('WEBGL_lose_context')?.loseContext()
      webglProbe = {
        available: true,
        software: SOFTWARE_RENDERER.test(renderer),
      }
    }
  } catch {
    webglProbe = { available: false, software: false }
  }
  return webglProbe
}

export function hasWebGL2(): boolean {
  return probeWebGL().available
}

export function rendersInSoftware(): boolean {
  return probeWebGL().software
}

export { useReducedMotion } from '@/hooks/useReducedMotion'

function isView(value: string | null): value is CosmosViewMode {
  return value === '3d' || value === '2d'
}

function isQuality(value: string | null): value is CosmosQuality {
  return value === 'low' || value === 'medium' || value === 'high'
}

export function useCosmosViewSettings() {
  const [view, setViewState] = useState<CosmosViewMode>(() => {
    const stored = read(VIEW_KEY)
    return isView(stored) ? stored : DEFAULT_VIEW
  })
  const [quality, setQualityState] = useState<CosmosQuality>(() => {
    const stored = read(QUALITY_KEY)
    if (isQuality(stored)) return stored
    return rendersInSoftware() ? SOFTWARE_QUALITY : DEFAULT_QUALITY
  })
  const [failure, setFailure] = useState<string | null>(() =>
    hasWebGL2() ? null : 'WebGL 2 is not available in this browser'
  )

  const setView = useCallback((next: CosmosViewMode) => {
    write(VIEW_KEY, next)
    setViewState(next)
  }, [])

  const setQuality = useCallback((next: CosmosQuality) => {
    write(QUALITY_KEY, next)
    setQualityState(next)
  }, [])

  return {
    view: failure === null ? view : '2d',
    preferredView: view,
    quality,
    failure,
    setView,
    setQuality,
    reportFailure: setFailure,
  }
}
