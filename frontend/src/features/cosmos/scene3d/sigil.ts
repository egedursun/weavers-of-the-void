import { CanvasTexture } from 'three'
import { fnv1a, seededRandom } from '../model/hash'

const TEXTURE_SIZE = 512
const STROKES = 7

export function sigilTexture(name: string): CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = TEXTURE_SIZE
  canvas.height = TEXTURE_SIZE
  const context = canvas.getContext('2d')
  const random = seededRandom(fnv1a(name) + 1)
  const center = TEXTURE_SIZE / 2
  if (context) {
    context.strokeStyle = 'white'
    context.lineCap = 'round'
    context.lineWidth = TEXTURE_SIZE * 0.018
    context.beginPath()
    context.arc(center, center, TEXTURE_SIZE * 0.42, 0, Math.PI * 2)
    context.stroke()
    context.lineWidth = TEXTURE_SIZE * 0.012
    context.beginPath()
    context.arc(center, center, TEXTURE_SIZE * 0.36, 0, Math.PI * 2)
    context.stroke()
    const points = Array.from({ length: STROKES }, () => {
      const angle = random() * Math.PI * 2
      const reach = TEXTURE_SIZE * (0.08 + random() * 0.26)
      return [
        center + Math.cos(angle) * reach,
        center + Math.sin(angle) * reach,
      ] as const
    })
    context.lineWidth = TEXTURE_SIZE * 0.022
    context.beginPath()
    context.moveTo(points[0][0], points[0][1])
    for (const point of points.slice(1)) context.lineTo(point[0], point[1])
    context.stroke()
    for (const point of points) {
      context.beginPath()
      context.arc(point[0], point[1], TEXTURE_SIZE * 0.02, 0, Math.PI * 2)
      context.stroke()
    }
  }
  return new CanvasTexture(canvas)
}
