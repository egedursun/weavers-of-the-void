import {
  ACCEPTED_ACTION,
  callsTo,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CouplingsSection } from './CouplingsSection'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TOWN = { id: 20, kind: 'entity' as const, name: 'Orvel' }
const TONGUE = { id: 21, kind: 'entity' as const, name: 'Orvelic' }
const SPIRIT = { id: 22, kind: 'entity' as const, name: 'The Well Voice' }
const CAPTAIN = { id: 23, kind: 'entity' as const, name: 'Dara' }
const FOE = { id: 24, kind: 'entity' as const, name: 'Kesh' }

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 900 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [])
}

function view(overrides: Record<string, unknown> = {}) {
  return {
    node: TOWN,
    is_rite: false,
    rite_parts: [],
    captive_id: null,
    restraints: [],
    is_community: true,
    is_region: false,
    is_teacher: false,
    is_beast: false,
    is_place: true,
    is_fashion: false,
    is_realm: false,
    sociolects: [
      {
        id: 1,
        language: TONGUE,
        holder: TOWN,
        kind: 'guild',
        prestige: 10,
        secret: false,
        salience: 30,
        since_epoch: 4,
        faded_epoch: null,
        locked: [],
      },
    ],
    signs: [
      {
        language: TONGUE,
        community: TOWN,
        cause: 'silence_vow',
        since_epoch: 5,
        locked: [],
      },
    ],
    carrion: null,
    teachings: [
      {
        id: 2,
        teacher: SPIRIT,
        learner: TOWN,
        kind: 'rite',
        subject: null,
        fidelity: 70,
        state: 'taught',
        price: 0,
        epoch: 5,
        locked: [],
      },
    ],
    partners: [SPIRIT],
    memories: [],
    happenings: [],
    agreements: [
      {
        id: 3,
        war_id: 7,
        kind: 'truce',
        state: 'kept',
        commander: CAPTAIN,
        counterpart: FOE,
        place: TOWN,
        term_epoch: 8,
        honour: 5,
        epoch: 6,
        ended_epoch: null,
        locked: [],
      },
    ],
    wars: [{ id: 7, name: 'The Ford War' }],
    seals: [],
    novelty: null,
    sinecures: [],
    ...overrides,
  }
}

describe('couplings', () => {
  beforeEach(() => resetApi())

  it('shows a town’s speech, teachers and terms and lets the god act on each', async () => {
    serveBase()
    onApi('GET', '/api/couplings/of/20', view())
    for (const name of [
      'sociolect:delete',
      'sociolect:create',
      'teaching:block',
      'field_agreement:void',
      'deep_seal:seal',
    ])
      onApi('POST', `/api/actions/${name}`, ACCEPTED_ACTION)
    const { screen } = await renderApp(<CouplingsSection nodeId={20} />)
    await expect
      .element(screen.getByText('Speech of a trade: Orvel').first())
      .toBeVisible()
    await expect.element(screen.getByText('A vow of silence')).toBeVisible()
    await expect
      .element(screen.getByText('The Well Voice to Orvel: a rite').first())
      .toBeVisible()
    await screen.getByRole('button', { name: 'Strike it out' }).first().click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/sociolect:delete'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Give it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/sociolect:create'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Forbid it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/teaching:block'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Void it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/field_agreement:void'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Seal it' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/deep_seal:seal'))
      .toHaveLength(1)
  })

  it('gives a rite its parts, holds a captive and keeps the dead of a region', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/couplings/of/20',
      view({
        is_rite: true,
        rite_parts: ['spoken'],
        captive_id: 5,
        restraints: [],
        is_community: false,
        is_region: true,
        is_place: false,
        sociolects: [],
        signs: [],
        teachings: [],
        partners: [],
        agreements: [],
        wars: [],
        carrion: {
          carrion: 400,
          scavenged: 50,
          preserved: false,
          rest: 'rotting',
          kept: false,
          epoch: 6,
          locked: [],
        },
      })
    )
    for (const name of [
      'rite_component:set',
      'restraint:set',
      'carrion:keep',
      'carrion:clear',
    ])
      onApi('POST', `/api/actions/${name}`, ACCEPTED_ACTION)
    const { screen } = await renderApp(<CouplingsSection nodeId={20} />)
    await screen.getByRole('button', { name: 'Asks for spoken' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/rite_component:set'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Gagged' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/restraint:set'))
      .toHaveLength(1)
    await expect.element(screen.getByText('400')).toBeVisible()
    await expect
      .element(screen.getByText('Rotting where they lie').first())
      .toBeVisible()
    await screen
      .getByRole('button', { name: 'Leave the dead where they lie' })
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/carrion:keep'))
      .toHaveLength(1)
    await screen.getByRole('button', { name: 'Clear away the dead' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/carrion:clear'))
      .toHaveLength(1)
  })

  it('says why nothing here can be forced when the thing is in no war', async () => {
    serveBase()
    onApi(
      'GET',
      '/api/couplings/of/20',
      view({
        agreements: [{ ...view().agreements[0], state: 'broken' }],
        wars: [],
      })
    )
    const { screen } = await renderApp(<CouplingsSection nodeId={20} />)
    await expect
      .element(screen.getByRole('button', { name: 'Force them' }))
      .toBeDisabled()
    await expect
      .element(screen.getByRole('button', { name: 'Void it' }))
      .toBeDisabled()
  })
})
