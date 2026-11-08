import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HerdsSection } from './BeastSection'
import { PetsSection } from './PetsSection'
import { FOLK, KIND, PETS, SPECIES, serveBasics } from './wildsFixtures'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

describe('pets and herd training', () => {
  beforeEach(resetApi)

  it('shows a mortal’s companion and sets it free', async () => {
    serveBasics()
    onApi('GET', '/api/entities/60/pets', PETS)
    onApi('POST', '/api/actions/pet:set', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PetsSection mortalId={60} />)
    await expect.element(screen.getByText('Grey of Tilla')).toBeVisible()
    await expect.element(screen.getByText('Hunts at their side')).toBeVisible()
    await expect
      .element(screen.getByRole('button', { name: 'Give the pet' }))
      .toBeDisabled()
    await screen.getByRole('button', { name: 'Set it free' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/pet:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/pet:set')[0].body).toEqual({
      beast_id: 61,
      owner_id: null,
    })
  })

  it('gives a pet of any animal kind even when their people keep none', async () => {
    serveBasics()
    onApi('GET', '/api/entities/60/pets', {
      ...PETS,
      pets: [],
      kinds: [],
    })
    onApi('POST', '/api/actions/pet:give', ACCEPTED_ACTION)
    const { screen } = await renderApp(<PetsSection mortalId={60} />)
    await expect
      .element(screen.getByRole('button', { name: 'Make it their pet' }))
      .toBeDisabled()
    await screen
      .getByRole('combobox', { name: 'A new pet of any animal kind' })
      .click()
    await screen.getByRole('option', { name: 'Dune Hare' }).click()
    await screen.getByRole('button', { name: 'Give the pet' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/pet:give'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/pet:give')[0].body).toEqual({
      owner_id: 60,
      species_id: 40,
    })
  })

  it('trains a herd for war', async () => {
    serveBasics()
    onApi('GET', '/api/entities/50/herds', [
      { ...SPECIES.herds[0], community: FOLK, species: KIND },
    ])
    onApi('POST', '/api/actions/herd:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<HerdsSection communityId={50} />)
    await expect
      .element(screen.getByText('Not in training').first())
      .toBeVisible()
    await screen.getByRole('button', { name: 'Adjust this herd' }).click()
    await screen.getByRole('combobox', { name: 'Trained for' }).click()
    await screen.getByRole('option', { name: 'War' }).click()
    await screen.getByRole('spinbutton', { name: 'Head trained' }).fill('5')
    await screen.getByRole('button', { name: 'Set the herd' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/herd:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/herd:edit')[0].body).toMatchObject({
      values: { training: 'war', trained: 5 },
    })
  })
})
