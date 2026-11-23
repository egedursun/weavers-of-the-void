import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TonguesSection } from './TonguesSection'
import { BASES, MODALITIES, STAGES } from './labels'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

const TONGUE = { id: 30, kind: 'entity' as const, name: 'Velari' }
const SON = { id: 7, kind: 'son' as const, name: 'Thalen' }
const REALM = { id: 40, kind: 'entity' as const, name: 'Crown' }
const SCHOLAR = { id: 41, kind: 'entity' as const, name: 'Vesh' }

const EMPTY = { held_policies: [], divine_tongue: null, known_divine: [] }

const SCRIPT = {
  id: 3,
  name: 'Velari logographic',
  system: 'logographic' as const,
  parent_script_id: 2,
  origin_language: TONGUE,
  signs: 2400,
  cause: 'simplification' as const,
  epoch: 5,
  locked: [],
}

function serveBase() {
  onApi('GET', '/api/state', {
    creator: { essence: 500 },
    epoch_running: false,
    read_only: false,
    world: { epoch: 6 },
  })
  onApi('GET', '/api/names', [
    { kind: 'entity', id: 30, name: 'Velari', type: 'language', world_id: 1 },
    { kind: 'entity', id: 40, name: 'Crown', type: 'polity', world_id: 1 },
  ])
  onApi('GET', '/api/tongues/scripts', [SCRIPT])
}

describe('tongues', () => {
  beforeEach(() => resetApi())

  it('shows a tongue’s sounds, grammar, script, decipherment, policies and shifts and undoes a change', async () => {
    serveBase()
    onApi('GET', '/api/tongues/of/30', {
      ...EMPTY,
      node: TONGUE,
      language: {
        modality: 'vocal',
        stage: 'natural',
        numeral_base: 'decimal',
        ancestor: null,
        writing_system: 'logographic',
        script: SCRIPT,
        lineage: [
          SCRIPT,
          {
            ...SCRIPT,
            id: 2,
            name: 'Velari pictographic',
            system: 'pictographic',
            parent_script_id: null,
          },
        ],
        grammar: {
          word_order: 'sov',
          morphology: 'agglutinative',
          cases: 4,
          noun_classes: 2,
          evidentiality: true,
          honorific_levels: 1,
          number_system: 'dual',
          updated_epoch: 3,
          locked: [],
        },
        changes: [
          {
            id: 9,
            kind: 'lenition',
            source: 't',
            target: 's',
            environment: 'between_vowels',
            cause: 'prestige',
            position: 0,
            epoch: 4,
            locked: [],
          },
        ],
        decipher: {
          progress: 40,
          corpus: 12,
          bilingual: true,
          errors: 1,
          scholar: SCHOLAR,
          started_epoch: 2,
          updated_epoch: 5,
          locked: [],
        },
        policies: [
          {
            holder: REALM,
            language: TONGUE,
            policy: 'official',
            strength: 60,
            since_epoch: 3,
            locked: [],
          },
        ],
        shifts: [
          {
            id: 11,
            lexeme_id: 5,
            word: 'Amar',
            shift: 'broadened',
            old_meaning: 'river',
            new_meaning: 'river; also road',
            absorbed_word: 'Vey',
            cause: null,
            epoch: 5,
          },
        ],
        sacred_to: null,
      },
    })
    onApi('POST', '/api/actions/sound_change:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TonguesSection nodeId={30} />)
    await expect
      .element(screen.getByRole('list', { name: 'How its sounds changed' }))
      .toBeVisible()
    await expect.element(screen.getByText('1. t → s')).toBeVisible()
    await expect.element(screen.getByText('Velari logographic')).toBeVisible()
    await expect.element(screen.getByText('A bilingual text')).toBeVisible()
    await expect.element(screen.getByText('river; also road')).toBeVisible()
    await screen.getByRole('button', { name: 'Undo' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/sound_change:delete'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/sound_change:delete')[0].body).toEqual(
      { change_id: 9 }
    )
  })

  it('shows a revived tongue’s ancestor and counting base and changes the base', async () => {
    serveBase()
    onApi('GET', '/api/tongues/of/30', {
      ...EMPTY,
      node: TONGUE,
      language: {
        modality: 'tactile',
        stage: 'revived',
        numeral_base: 'vigesimal',
        ancestor: { id: 31, kind: 'entity', name: 'Old Velari' },
        writing_system: null,
        script: null,
        lineage: [],
        grammar: null,
        changes: [],
        decipher: null,
        policies: [],
        shifts: [],
        sacred_to: null,
      },
    })
    onApi('POST', '/api/actions/tongue:edit', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TonguesSection nodeId={30} />)
    await expect
      .element(
        screen.getByText(
          `${MODALITIES.tactile.label} · ${STAGES.revived.label}`
        )
      )
      .toBeVisible()
    await expect
      .element(screen.getByText(`${BASES.vigesimal.label} · Unwritten`))
      .toBeVisible()
    await expect.element(screen.getByText('Old Velari')).toBeVisible()
    await screen.getByRole('button', { name: 'Adjust' }).first().click()
    await expect
      .element(
        screen.getByRole('button', { name: 'Hold these values' }).first()
      )
      .toBeDisabled()
    await screen.getByRole('combobox', { name: 'Counting base' }).click()
    await screen.getByRole('option', { name: BASES.duodecimal.label }).click()
    await screen
      .getByRole('button', { name: 'Hold these values' })
      .first()
      .click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/tongue:edit'))
      .toHaveLength(1)
    expect(callsTo('POST', '/api/actions/tongue:edit')[0].body).toEqual({
      language_id: 30,
      values: { numeral_base: 'duodecimal' },
    })
  })

  it('shows a god’s sacred tongue and takes it away', async () => {
    serveBase()
    onApi('GET', '/api/tongues/of/7', {
      node: SON,
      language: null,
      held_policies: [],
      divine_tongue: { god: SON, language: TONGUE, since_epoch: 2, locked: [] },
      known_divine: [],
    })
    onApi('POST', '/api/actions/divine_tongue:delete', ACCEPTED_ACTION)
    const { screen } = await renderApp(<TonguesSection nodeId={7} />)
    await expect.element(screen.getByText('Spoken since epoch 2')).toBeVisible()
    await screen.getByRole('button', { name: 'Take away' }).click()
    await expect
      .poll(() => callsTo('POST', '/api/actions/divine_tongue:delete'))
      .toHaveLength(1)
    expect(
      callsTo('POST', '/api/actions/divine_tongue:delete')[0].body
    ).toEqual({ god_id: 7 })
  })

  it('says why the tongues could not be read', async () => {
    serveBase()
    onApi('GET', '/api/tongues/of/30', failure(500, 'The heavens are silent.'))
    const { screen } = await renderApp(<TonguesSection nodeId={30} />)
    await expect
      .element(screen.getByText('The tongues could not be read'))
      .toBeVisible()
  })
})
