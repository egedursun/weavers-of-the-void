import { afterEach, describe, expect, it } from 'vitest'
import { ParticleField } from './particles'

const host = document.createElement('div')

function frames(count: number) {
  return new Promise<void>((resolve) => {
    const step = (left: number) =>
      left === 0 ? resolve() : requestAnimationFrame(() => step(left - 1))
    step(count)
  })
}

function litCentre(canvas: HTMLCanvasElement) {
  const context = canvas.getContext('2d')
  if (!context) throw new Error('no context')
  const { data } = context.getImageData(0, 0, canvas.width, canvas.height)
  let weight = 0
  let sumX = 0
  let sumY = 0
  for (let index = 3; index < data.length; index += 4) {
    const alpha = data[index]
    if (alpha < 8) continue
    const pixel = (index - 3) / 4
    weight += alpha
    sumX += (pixel % canvas.width) * alpha
    sumY += Math.floor(pixel / canvas.width) * alpha
  }
  const ratio = canvas.width / canvas.clientWidth
  return { x: sumX / weight / ratio, y: sumY / weight / ratio }
}

function still(field: ParticleField, x: number, y: number) {
  field.emit(x, y, {
    count: 1,
    colors: ['white'],
    kinds: ['ember'],
    speed: [0, 0],
    size: [3, 3],
    life: [20, 20],
    gravity: 0,
    drag: 1,
  })
}

afterEach(() => {
  host.remove()
  host.replaceChildren()
  host.style.transform = ''
})

describe('particle field', () => {
  it('draws where it is told even when measured mid-transform or resized', async () => {
    const canvas = document.createElement('canvas')
    canvas.style.display = 'block'
    canvas.style.width = '400px'
    canvas.style.height = '200px'
    host.style.transform = 'scale(0.5)'
    host.append(canvas)
    document.body.append(host)
    const field = new ParticleField(canvas)
    host.style.transform = ''
    still(field, 300, 150)
    await frames(2)
    const first = litCentre(canvas)
    expect(first.x).toBeCloseTo(300, -1)
    expect(first.y).toBeCloseTo(150, -1)
    canvas.style.width = '800px'
    canvas.style.height = '400px'
    await frames(30)
    still(field, 600, 300)
    await frames(2)
    const second = litCentre(canvas)
    expect(second.x).toBeCloseTo(600, -1)
    expect(second.y).toBeCloseTo(300, -1)
    field.dispose()
  })
})
