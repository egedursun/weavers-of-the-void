import { worldState } from '@/test-utils/fixtures'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { MissingModelsBanner, ModelNeeded } from './ModelNeeded'
import { MODELS_OFF_REASON, modelBlock, rolesNamed } from './modelReadiness'

const NONE = [
  { role: 'world_agents', model: '' },
  { role: 'writing', model: '' },
  { role: 'conversation', model: '' },
  { role: 'images', model: '' },
]

describe('a world with roles that have no model', () => {
  it('names the roles and points to the models for a blocked control', () => {
    const empty = worldState({ role_models: NONE }) as never
    expect(rolesNamed(['writing', 'conversation', 'images'])).toBe(
      'writing, conversation and images'
    )
    expect(modelBlock(empty, 'writing')).toBe(
      'No model is set for writing; choose one under Models in the workspace settings.'
    )
    expect(modelBlock(worldState() as never, 'writing')).toBeNull()
    expect(
      modelBlock(worldState({ llm_enabled: false }) as never, 'writing')
    ).toBe(MODELS_OFF_REASON)
  })

  it('warns across the app with a way to the models page', async () => {
    const { screen } = await renderScreen(<MissingModelsBanner />, {
      'GET /api/state': worldState({ role_models: NONE }),
    })
    await expect
      .element(
        screen.getByText(
          'No model is set for world agents, writing, conversation and images. What needs them waits until you choose one.'
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Choose the models' }))
      .toHaveAttribute('href', '/workspace?part=providers')
  })

  it('tells a chat why it waits', async () => {
    const empty = await renderScreen(
      <ModelNeeded role='conversation' what='The Divine Will' />,
      { 'GET /api/state': worldState({ role_models: NONE }) }
    )
    await expect
      .element(empty.screen.getByText('No model is set for conversation'))
      .toBeVisible()
    await expect
      .element(
        empty.screen.getByText(
          /The Divine Will waits until this workspace or the server default puts a model in the conversation chain/
        )
      )
      .toBeVisible()
  })

  it('shows nothing once the role has a model', async () => {
    const ready = await renderScreen(
      <ModelNeeded role='conversation' what='The Divine Will' />,
      { 'GET /api/state': worldState() }
    )
    await expect
      .element(ready.screen.getByText('No model is set for conversation'))
      .not.toBeInTheDocument()
  })
})
