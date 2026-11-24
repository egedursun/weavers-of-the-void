import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DishPage } from './DishPage'
import { type Dish } from './api'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const PEOPLE = { id: 40, kind: 'entity' as const, name: 'Varo' }
const FLAVOURS = [
  'sweet',
  'sour',
  'saline',
  'bitter',
  'savoury',
  'pungent',
  'cooling',
  'numbing',
  'smoky',
  'fermented',
  'astringent',
  'rich',
].map((flavour, index) => ({
  flavour,
  label: `${flavour[0].toUpperCase()}${flavour.slice(1)}`,
  value: index * 5,
}))

const DISH: Dish = {
  id: 7,
  entity_id: null,
  name: 'Long Loaf',
  description: null,
  world_id: 1,
  origin: PEOPLE,
  method: 'baked',
  course: 'festive',
  category: 'feast',
  nourishment: 40,
  delight: 30,
  keeps: 1,
  prestige: 20,
  prep_skill: 35,
  technique: null,
  created_epoch: 2,
  retired: false,
  derived_from_id: 3,
  derived_from_name: 'Old Loaf',
  flavours: FLAVOURS,
  steps: [{ id: 11, step: 1, method: 'baked', duration: 2, locked: [] }],
  ingredients: [
    {
      commodity: 'grain',
      share: 80,
      role: 'base',
      good_kind_id: 21,
      good_name: 'Grain',
    },
  ],
  cooked_in: [],
  locked: [],
}

const GOODS = [
  {
    id: 21,
    concept: 'good',
    name: 'Grain',
    description: null,
    category: 'grain',
    category_label: 'Grain',
    world: null,
    origin: null,
    derived_from_id: null,
    derived_from_name: null,
    built_in: true,
    retired: false,
    created_epoch: 0,
    locked: [],
    values: [],
    holders: [],
  },
]

describe('a dish page', () => {
  beforeEach(() => {
    resetApi()
    onApi('GET', '/api/kinds/good', GOODS)
    onApi('POST', '/api/actions/dish_step:set', ACCEPTED_ACTION)
    onApi('POST', '/api/actions/dish_ingredient:set', ACCEPTED_ACTION)
  })

  it('shows the steps, the taste, the meal and where the dish came from', async () => {
    const { screen } = await renderApp(<DishPage row={DISH} />)
    await expect.element(screen.getByText('Step 1: Baked')).toBeVisible()
    await expect
      .element(screen.getByRole('region', { name: 'Taste of the dish' }))
      .toBeVisible()
    await expect.element(screen.getByText('Feast').first()).toBeVisible()
    await expect.element(screen.getByText('Old Loaf')).toBeVisible()
    await expect.element(screen.getByText('Skill to make')).toBeVisible()
  })

  it('adds the next step to how the dish is made', async () => {
    const { screen } = await renderApp(<DishPage row={DISH} />)
    await screen.getByRole('combobox', { name: 'How it is done' }).click()
    await screen.getByRole('option', { name: 'Aged' }).click()
    await screen.getByRole('button', { name: 'Add the step' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/dish_step:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/dish_step:set')[0].body).toEqual({
      dish_id: 7,
      step: 2,
      method: 'aged',
      duration: 1,
    })
  })

  it('sets the role an ingredient plays and the good it is', async () => {
    const { screen } = await renderApp(<DishPage row={DISH} />)
    await screen.getByRole('combobox', { name: 'Role in the dish' }).click()
    await screen.getByRole('option', { name: 'Binder' }).click()
    await screen.getByRole('button', { name: 'Set', exact: true }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/dish_ingredient:set'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/dish_ingredient:set')[0].body).toEqual(
      {
        dish_id: 7,
        commodity: 'grain',
        share: 80,
        role: 'binder',
        good_kind_id: 21,
      }
    )
  })
})
