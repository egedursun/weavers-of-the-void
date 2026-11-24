import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import type { components } from '@/api/generated/schema'
import { AnatomyFigure } from './AnatomyFigure'

type Part = components['schemas']['PartView']

function part(key: string, label: string, changes: Partial<Part> = {}): Part {
  return {
    key,
    label,
    region: 'torso',
    functions: [],
    severable: false,
    internal: false,
    vital: false,
    counted: 0,
    loss: 0,
    state: null,
    prosthesis: null,
    ...changes,
  }
}

const CORE_PLANS = new Set(['tentacled', 'radial'])

describe('anatomy figure', () => {
  it('draws the killing wound and labels every wounded part', async () => {
    const parts = [
      part('heart', 'Heart', { state: 'lethal', vital: true }),
      part('left_eye', 'Left eye', { state: 'permanent', loss: 100 }),
      part('torso', 'Torso'),
    ]
    const { screen } = await renderScreen(
      <AnatomyFigure
        plan='humanoid'
        parts={parts}
        describe={(item) => item.label}
      />
    )
    await expect
      .element(screen.getByRole('img', { name: /2 parts marked/ }))
      .toBeVisible()
    await expect
      .element(screen.getByText('FATAL', { exact: true }))
      .toBeVisible()
    await expect
      .element(screen.getByText('LOST', { exact: true }))
      .toBeVisible()
    const figure = screen.getByRole('img', { name: /parts marked/ }).element()
    const texts = [...figure.querySelectorAll('text')].map(
      (node) => node.textContent
    )
    expect(texts).toEqual(expect.arrayContaining(['Heart', 'Left eye']))
    expect(figure.querySelectorAll('[filter*="glow"]').length).toBeGreaterThan(
      0
    )
  })

  it.each([
    'quadruped',
    'avian',
    'serpentine',
    'insectoid',
    'aquatic',
    'amorphous',
    'arboreal',
    'incorporeal',
    'colossal',
    'construct',
    'divine_manifest',
    'tentacled',
    'centauroid',
    'radial',
    'colonial',
    'hexapod',
    'rooted',
  ])('draws the %s plan', async (plan) => {
    const { screen } = await renderScreen(
      <AnatomyFigure
        plan={plan}
        parts={[
          part(CORE_PLANS.has(plan) ? 'core' : 'torso', 'Torso', {
            state: 'fresh',
          }),
        ]}
        describe={(item) => item.label}
      />
    )
    await expect
      .element(screen.getByRole('img', { name: /1 part marked/ }))
      .toBeVisible()
    await expect
      .element(screen.getByText('OPEN WOUND', { exact: true }))
      .toBeVisible()
  })
})
