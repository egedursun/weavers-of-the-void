import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MaterialForge } from './MaterialsTab'
import {
  CoinForge,
  CurrencyCards,
  DebtLaws,
  LoanCard,
  LoanForge,
} from './MoneyTab'
import { WorkshopDesigns } from './WorkshopDesigns'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const WORLD = 4

const IRON = {
  kind: 'iron',
  world_material_id: null,
  label: 'Iron',
  family: 'metal',
  origin: 'catalog',
  source: 'world',
  edited: false,
  hardness: 60,
  toughness: 55,
  weight: 60,
  edge: 55,
  conductivity: 40,
  sanctity: 10,
  corruption: 5,
  rarity: 30,
  base_value: 40,
  decay: 45,
  branch: 'metallurgy',
  level: 3,
  gate: null,
  description: null,
  deposit_id: null,
  held: false,
  base_kind: null,
  price_premium_pct: 96,
  worth_pct: 98,
  melting_point: 68,
  ignition_point: 100,
  boiling_point: 90,
  density: 72,
  impact_yield: 60,
  impact_fracture: 70,
  shear_yield: 58,
  shear_fracture: 68,
  elasticity: 30,
  thermal_conductivity: 60,
  solid_density: 75,
  max_edge: 65,
} as const

const LOAN = {
  id: 5,
  lender_id: 32,
  lender_name: 'Nevrahim',
  borrower_id: 46,
  borrower_name: 'Hesmarak',
  currency_id: 3,
  principal: 500,
  interest_pct: 10,
  repaid: 100,
  owed: 450,
  issued_epoch: 40,
  due_epoch: 60,
  status: 'open',
  purpose: 'war',
  held: false,
  borrower_type: 'polity',
  currency_name: 'Silver Crowns',
} as const

const LAW = {
  law_id: 900,
  name: 'Law of the Seventh Year',
  holders: [32],
  holder_names: ['Nevrahim'],
  remedy: 'jubilee',
  jubilee_epochs: 7,
  enforcement: 60,
} as const

const DESIGN = {
  id: 12,
  world_id: WORLD,
  base_kind: 'forge',
  label: 'Forge',
  name: 'Bellows forge',
  description: 'Twin bellows drive the fire hotter.',
  output_pct: 140,
  capacity_pct: 100,
  store_pct: 100,
  quality_bonus: 10,
  held: true,
  workshops: 2,
} as const

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { id: 1, epoch: 51, primary_world_id: WORLD },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 32, name: 'Nevrahim', type: 'people', world_id: 4 },
    { kind: 'entity', id: 46, name: 'Hesmarak', type: 'polity', world_id: 4 },
  ])
  onApi('GET', `/api/worlds/${WORLD}/materials`, { materials: [IRON] })
  onApi('GET', '/api/currencies', [])
  onApi('GET', '/api/ledger/debt-laws', [LAW])
  onApi('GET', `/api/worlds/${WORLD}/workshop-designs`, [DESIGN])
  for (const action of [
    'currency:create',
    'material:create',
    'loan:edit',
    'loan:grant',
    'law:edit',
    'workshop_design:create',
    'workshop_design:release',
  ])
    onApi('POST', `/api/actions/${action}`, ACCEPTED_ACTION)
}

describe('economy forms', () => {
  beforeEach(resetApi)

  it('strikes no coin until its metal is chosen, then strikes it in that metal', async () => {
    serve()
    const { screen } = await renderApp(<CoinForge worldId={WORLD} />)
    await screen.getByRole('combobox', { name: 'Struck by' }).click()
    await screen.getByRole('option', { name: /Nevrahim/ }).click()
    await screen.getByRole('textbox', { name: 'Coin name' }).fill('Tallyroll')
    const strike = screen.getByRole('button', { name: 'Strike it' })
    await expect.element(strike).toHaveAttribute('aria-disabled', 'true')
    await expect
      .element(strike)
      .toHaveAttribute(
        'aria-description',
        'Choose the metal it is struck in first.'
      )
    await screen.getByRole('combobox', { name: 'Metal' }).click()
    await screen.getByRole('option', { name: 'Iron' }).click()
    await strike.click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/currency:create').length)
      .toBe(1)
    expect(
      callsTo('POST', '/api/actions/currency:create')[0]?.body
    ).toMatchObject({
      issuer_id: 32,
      name: 'Tallyroll',
      metal: 'iron',
    })
  })

  it('forges a material akin to a catalog one with every value', async () => {
    serve()
    const { screen } = await renderApp(
      <MaterialForge worldId={WORLD} materials={[IRON]} />
    )
    await screen.getByRole('textbox', { name: 'Name' }).fill('Moonsilver')
    await screen.getByRole('combobox', { name: 'Akin to' }).click()
    await screen.getByRole('option', { name: 'Iron' }).click()
    await screen
      .getByRole('spinbutton', { name: 'New material sanctity' })
      .fill('90')
    await screen.getByRole('button', { name: 'Forge it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/material:create').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/material:create')[0]?.body).toEqual({
      world_id: WORLD,
      name: 'Moonsilver',
      family: 'metal',
      base_kind: 'iron',
      values: {
        hardness: 60,
        toughness: 55,
        weight: 60,
        edge: 55,
        conductivity: 40,
        sanctity: 90,
        corruption: 5,
        rarity: 30,
        base_value: 40,
        decay: 45,
        boiling_point: 90,
        density: 72,
        elasticity: 30,
        ignition_point: 100,
        impact_fracture: 70,
        impact_yield: 60,
        max_edge: 65,
        melting_point: 68,
        shear_fracture: 68,
        shear_yield: 58,
        solid_density: 75,
        thermal_conductivity: 60,
      },
      branch: null,
      level: 0,
      description: null,
      place_id: null,
    })
  })

  it('shows a realm loan in its coin and edits it', async () => {
    serve()
    const { screen } = await renderApp(
      <ul>
        <LoanCard loan={LOAN} />
      </ul>
    )
    await expect.element(screen.getByText('Realm')).toBeVisible()
    await expect.element(screen.getByText(/in Silver Crowns/)).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust the loan' }).click()
    await screen.getByRole('spinbutton', { name: 'Loan 5 interest' }).fill('20')
    await screen.getByRole('button', { name: 'Set the loan' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/loan:edit').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/loan:edit')[0]?.body).toEqual({
      loan_id: 5,
      principal: 500,
      interest_pct: 20,
      due_epoch: 60,
      repaid: 100,
      status: 'open',
      hold: false,
    })
  })

  it('makes a loan between two parties', async () => {
    serve()
    const { screen } = await renderApp(<LoanForge />)
    await screen.getByRole('combobox', { name: 'Lender' }).click()
    await screen.getByRole('option', { name: /Nevrahim/ }).click()
    await screen.getByRole('combobox', { name: 'Borrower' }).click()
    await screen.getByRole('option', { name: /Hesmarak/ }).click()
    await screen
      .getByRole('spinbutton', { name: 'New loan principal' })
      .fill('800')
    await screen.getByRole('button', { name: 'Lend it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/loan:grant').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/loan:grant')[0]?.body).toEqual({
      lender_id: 32,
      borrower_id: 46,
      principal: 800,
      interest_pct: 10,
      term_epochs: 5,
      currency_id: null,
      purpose: 'trade',
    })
  })

  it('reads a debt law and rewrites its remedy', async () => {
    serve()
    const { screen } = await renderApp(<DebtLaws />)
    await expect
      .element(screen.getByText('Every debt is wiped clean after 7 epochs.'))
      .toBeVisible()
    await screen.getByRole('button', { name: 'Adjust the law' }).click()
    await screen.getByRole('combobox', { name: 'Remedy' }).click()
    await screen.getByRole('option', { name: "Debtors' prison" }).click()
    await screen.getByRole('button', { name: 'Set the law' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/law:edit').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/law:edit')[0]?.body).toEqual({
      law_id: 900,
      params: { remedy: 'prison', jubilee_epochs: 7 },
    })
  })

  it('lists workshop designs, releases a held one and draws a new one', async () => {
    serve()
    const { screen } = await renderApp(<WorkshopDesigns worldId={WORLD} />)
    await expect.element(screen.getByText('Bellows forge')).toBeVisible()
    await expect.element(screen.getByText('Held')).toBeVisible()
    await screen.getByRole('button', { name: 'Release' }).click()
    await expect
      .poll(
        () => callsTo('POST', '/api/actions/workshop_design:release').length
      )
      .toBe(1)
    await screen
      .getByRole('button', { name: 'Draw a new workshop design' })
      .click()
    await screen
      .getByRole('textbox', { name: 'Design name' })
      .fill('Terraced mill')
    await screen.getByRole('button', { name: 'Draw it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/workshop_design:create').length)
      .toBe(1)
    expect(
      callsTo('POST', '/api/actions/workshop_design:create')[0]?.body
    ).toEqual({
      world_id: WORLD,
      base_kind: 'forge',
      name: 'Terraced mill',
      values: {
        output_pct: 100,
        capacity_pct: 100,
        store_pct: 100,
        quality_bonus: 0,
      },
      description: null,
    })
  })
  it('shows a network ledger as money with no metal', async () => {
    serve()
    onApi('GET', '/api/currencies', [
      {
        id: 9,
        name: 'the ledger of Coast Relay',
        issuer_id: 46,
        issuer_name: 'Coast Relay',
        item_id: null,
        metal: null,
        purity: 100,
        trust: 55,
        supply: 0,
        minted_epoch: 12,
        debased_epoch: null,
        users: [32],
        held: false,
        form: 'ledger',
        backing: 'trust',
        convertible: false,
        issuer_kind: 'community',
      },
    ])
    const { screen } = await renderApp(<CurrencyCards worldId={WORLD} />)
    await expect.element(screen.getByText(/^Ledger money of/)).toBeVisible()
    await expect
      .element(screen.getByText(/, a community, since epoch 12/))
      .toBeVisible()
    await expect
      .element(screen.getByText('Backed by trust alone'))
      .toBeVisible()
  })
})
