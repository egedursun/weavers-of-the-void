import { describe, expect, it } from 'vitest'
import sheet from './index.css?raw'

const SOURCES = import.meta.glob('/src/**/*.tsx', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

function classesWhere(test: (body: string) => boolean): string[] {
  const found: string[] = []
  for (const match of sheet.matchAll(/\.([a-z][\w-]*)\s*\{([^}]*)\}/g))
    if (test(match[2])) found.push(match[1])
  return found
}

const TRANSFORM_FRAMES = new Set(
  [...sheet.matchAll(/@keyframes\s+([\w-]+)\s*\{([\s\S]*?)\n\}/g)]
    .filter((match) => match[2].includes('transform'))
    .map((match) => match[1])
)

const SLIDING = classesWhere((body) => /transition:[^;]*transform/.test(body))

const MOVING = classesWhere((body) =>
  [...body.matchAll(/animation:\s*([\w-]+)/g)].some((match) =>
    TRANSFORM_FRAMES.has(match[1])
  )
)

function elementsOf(source: string): string[] {
  return [...source.matchAll(/className=\{?([^>]*)/g)].map((match) => match[1])
}

describe('motion on one element', () => {
  it('never puts a transform animation on an element whose transform slides by transition', () => {
    expect(SLIDING.length).toBeGreaterThan(0)
    const clashes: string[] = []
    for (const [path, source] of Object.entries(SOURCES))
      for (const element of elementsOf(source))
        for (const sliding of SLIDING)
          for (const moving of MOVING)
            if (
              new RegExp(`\\b${sliding}\\b`).test(element) &&
              new RegExp(`\\b${moving}\\b`).test(element)
            )
              clashes.push(`${path}: ${sliding} with ${moving}`)
    expect(clashes).toEqual([])
  })
})
