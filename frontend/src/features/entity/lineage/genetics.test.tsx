import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LineageSection } from '../sections/LineageSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const NODE = 41

const MUSCLE_LOCUS = {
  locus: 'muscle',
  label: 'Muscle',
  group: 'body',
  group_label: 'Body and constitution',
  alleles: [
    { key: 'low', label: 'light of muscle', frequency: null, effects: [] },
    { key: 'common', label: 'of common muscle', frequency: null, effects: [] },
    {
      key: 'high',
      label: 'heavily muscled',
      frequency: null,
      effects: ['Strength +5 at birth'],
    },
  ],
}

const SIGHT_LOCUS = {
  locus: 'sight',
  label: 'Sight',
  group: 'sense',
  group_label: 'Senses',
  alleles: [
    { key: 'low', label: 'dim-sighted', frequency: null, effects: [] },
    { key: 'common', label: 'of common sight', frequency: null, effects: [] },
    { key: 'high', label: 'sharp-sighted', frequency: null, effects: [] },
  ],
}

function lineage() {
  return {
    node_id: NODE,
    node_kind: 'mortal',
    can_hold_genome: true,
    can_hold_pool: false,
    can_hold_likeness: false,
    reason: null,
    pool: null,
    resemblance: null,
    loci: [MUSCLE_LOCUS, SIGHT_LOCUS],
    stances: [],
    genome: {
      genes: [
        {
          locus: 'muscle',
          label: 'Muscle',
          group: 'body',
          group_label: 'Body and constitution',
          first: 'high',
          second: 'high',
          shown: 'high',
          shown_label: 'heavily muscled',
          effects: ['Strength +5 at birth'],
        },
        {
          locus: 'sight',
          label: 'Sight',
          group: 'sense',
          group_label: 'Senses',
          first: 'common',
          second: 'common',
          shown: 'common',
          shown_label: 'of common sight',
          effects: [],
        },
      ],
      gifts: [],
      appearance: 'heavily muscled',
      marks: [],
      beauty: 50,
      inbreeding: 0,
      recognisability: 20,
      potential: {},
      divine_son: null,
      likeness: [],
      tied_traits: [
        {
          trait: 'hardy',
          trait_label: 'Hardy',
          locus: 'stamina',
          locus_label: 'Stamina',
          held: false,
        },
      ],
      carried: [
        {
          locus: 'madness',
          locus_label: 'Madness',
          allele: 'touched',
          allele_label: 'prone to madness',
          harmful: true,
        },
      ],
      blood_effects: [
        {
          effect: 'healing',
          label: 'Chance a wound heals',
          amount: 20,
          per_epoch: false,
        },
        {
          effect: 'cold',
          label: 'Health in cold lands',
          amount: 3,
          per_epoch: true,
        },
      ],
      epoch: 3,
      held: [],
    },
  }
}

function serve() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 51 },
  })
  onApi('GET', `/api/lineage/${NODE}`, lineage())
  onApi('POST', '/api/actions/genome:gene', ACCEPTED_ACTION)
}

describe('the genetics of a mortal', () => {
  beforeEach(resetApi)

  it('groups loci by kind and shows what each allele does', async () => {
    serve()
    const { screen } = await renderApp(<LineageSection nodeId={NODE} />)
    await expect
      .element(screen.getByRole('group', { name: 'Body and constitution' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('group', { name: 'Senses' }))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText(/Strength \+5 at birth/).first())
      .toBeInTheDocument()
  })

  it('shows the leanings, the tied traits and the hidden alleles of the blood', async () => {
    serve()
    const { screen } = await renderApp(<LineageSection nodeId={NODE} />)
    await expect.element(screen.getByText('Healing: +20%')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Cold lands: +3 health each epoch'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Hardy · Stamina · not taken'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Madness: prone to madness'))
      .toBeInTheDocument()
  })

  it('sets a pair of alleles on a new locus through the god action', async () => {
    serve()
    const { screen } = await renderApp(<LineageSection nodeId={NODE} />)
    await screen
      .getByRole('button', { name: /Muscle alleles/ })
      .first()
      .click()
    await expect
      .element(screen.getByText(/heavily muscled: Strength \+5 at birth/))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Set this pair' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/genome:gene').length)
      .toBe(1)
    expect(callsTo('POST', '/api/actions/genome:gene')[0]?.body).toMatchObject({
      mortal_id: NODE,
      locus: 'muscle',
      first: 'high',
      second: 'high',
    })
  })
})
