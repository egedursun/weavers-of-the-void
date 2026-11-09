import { expect, it } from 'vitest'

const SOURCES = import.meta.glob(
  [
    '../cosmography/**/*.{ts,tsx}',
    '../cosmos/**/*.{ts,tsx}',
    '../atlas/**/*.{ts,tsx}',
  ],
  { query: '?raw', import: 'default', eager: true }
) as Record<string, string>

const NUMBERED = /(?:`|[A-Za-z] )#\$\{(?!pair\()/

it('names every node of the heavens, the cosmos and the atlas instead of numbering it', () => {
  const numbered = Object.entries(SOURCES)
    .filter(([path]) => !path.includes('.test.'))
    .flatMap(([path, text]) =>
      text
        .split('\n')
        .filter((line) => NUMBERED.test(line))
        .map((line) => `${path}: ${line.trim()}`)
    )
  expect(numbered).toEqual([])
})
