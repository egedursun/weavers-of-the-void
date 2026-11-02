import { worldState } from '@/test-utils/fixtures'
import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { describe, expect, it } from 'vitest'
import { userEvent } from 'vitest/browser'
import { ContextBlocksView } from './ContextBlocksView'
import { PromptCatalogueView } from './PromptCatalogueView'
import { SonPromptView } from './SonPromptView'
import { TiredMotifsView } from './TiredMotifsView'
import { type PromptEntry } from './api'
import { budgetTone, matchesPrompt } from './promptModel'
import { validatePromptsSearch } from './promptsSearch'

const NAMES = [
  { kind: 'son', id: 7, name: 'Ithren', type: 'Rare' },
  { kind: 'world', id: 3, name: 'Velmora', type: 'world' },
  { kind: 'entity', id: 42, name: 'The Glass Ossuary', type: 'structure' },
]

const BASE = {
  'GET /api/state': worldState(),
  'GET /api/names': NAMES,
}

const ENTRY: PromptEntry = {
  prompt_id: 'fate_judgment_user',
  area: 'fate',
  template_path: 'fate/judgment_user.j2',
  context: 'FateJudgmentContext',
  variables: [{ name: 'creations', type: 'list', required: true }],
  output: 'FateVerdicts',
  has_constraints: true,
}

const PREVIEW = {
  son_id: 7,
  son_name: 'Ithren',
  epoch: 6,
  action_points: 4,
  system_prompt: 'SON: Ithren',
  user_prompt: 'EPOCH 6',
  system_characters: 11,
  user_characters: 7,
  total_characters: 21_000,
  token_estimate: 5_250,
  prompt_limit: 20_000,
  over_limit: true,
  tool_names: ['create_place', 'inspect_entity'],
  paid_tools: ['create_place'],
  free_tools: ['inspect_entity'],
  summary_sections: [{ section: 'events', characters: 900, limit: 1_000 }],
  summary_characters: 900,
  summary_limit: 9_000,
  memory_characters: 100,
  memory_limit: 4_000,
}

const MOTIFS = {
  world_id: null,
  motifs: [{ key: 'weeping moon', percent: 34, pinned: false }],
  foreign_images: [],
  overrides: [{ id: 1, world_id: null, motif: 'silver tide', mode: 'allowed' }],
}

describe('prompt model', () => {
  it('colours budgets by how full they are', () => {
    expect(budgetTone(10, 100)).toBe('default')
    expect(budgetTone(90, 100)).toBe('warning')
    expect(budgetTone(120, 100)).toBe('destructive')
    expect(budgetTone(1, 0)).toBe('muted')
  })

  it('searches prompts by id, template and variable', () => {
    expect(matchesPrompt(ENTRY, 'judgment')).toBe(true)
    expect(matchesPrompt(ENTRY, 'creations')).toBe(true)
    expect(matchesPrompt(ENTRY, 'chronicler')).toBe(false)
    expect(matchesPrompt(ENTRY, '')).toBe(true)
  })

  it('keeps only valid search params', () => {
    expect(validatePromptsSearch({ son: '7', view: 'motifs' })).toEqual({
      son: 7,
      view: 'motifs',
    })
    expect(validatePromptsSearch({ son: 'x', view: 'nowhere' })).toEqual({})
  })
})

describe('son prompt', () => {
  it('shows the budget, tools and both prompts', async () => {
    const { screen } = await renderScreen(<SonPromptView initialSon={7} />, {
      ...BASE,
      'GET /api/prompt-context/son-prompt/{son_id}': PREVIEW,
    })
    await expect
      .element(screen.getByText('Over the limit', { exact: true }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('create_place')).toBeInTheDocument()
    await expect.element(screen.getByText('SON: Ithren')).toBeInTheDocument()
    await expect.element(screen.getByText('EPOCH 6')).toBeInTheDocument()
  })

  it('asks for a son first', async () => {
    const { screen } = await renderScreen(
      <SonPromptView initialSon={null} />,
      BASE
    )
    await expect
      .element(screen.getByText('Pick a son', { exact: true }).last())
      .toBeInTheDocument()
  })
})

describe('context blocks', () => {
  it('renders a block and asks for the record it needs', async () => {
    const { screen, server } = await renderScreen(<ContextBlocksView />, {
      ...BASE,
      'GET /api/prompt-context/blocks': [
        {
          kind: 'world-header',
          needs_son: false,
          needs_entity: false,
          audience: 'every agent',
          rows: [],
        },
        {
          kind: 'entity-detail',
          needs_son: false,
          needs_entity: true,
          audience: 'Fate',
          rows: [],
        },
      ],
      'GET /api/prompt-context/{kind}': {
        kind: 'world-header',
        text: 'WORLD: Velmora',
        characters: 14,
        token_estimate: 4,
        world_id: 3,
        son_id: null,
        entity_id: null,
      },
    })
    await expect.element(screen.getByText('WORLD: Velmora')).toBeInTheDocument()
    await screen.getByLabelText('Short form').click()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/prompt-context/{kind}')
          .some((call) => call.query.get('short') === 'true')
      )
      .toBe(true)
    const entityDetail = screen
      .getByRole('radiogroup', { name: 'Block' })
      .getByRole('radio', { name: /^Entity detail/ })
    await entityDetail.click()
    await expect.element(entityDetail).toHaveAttribute('aria-checked', 'true')
    await expect
      .element(screen.getByText('This block describes one record. Pick it.'))
      .toBeInTheDocument()
  })
})

describe('prompt catalogue', () => {
  it('opens a prompt with its template and schema', async () => {
    const { screen } = await renderScreen(<PromptCatalogueView />, {
      ...BASE,
      'GET /api/prompt-context/catalogue': {
        prompts: [ENTRY],
        son_tools: [],
        mortal_tools: [],
      },
      'GET /api/prompt-context/catalogue/{prompt_id}': {
        ...ENTRY,
        template_source: 'Epoch {{ epoch }}',
        output_schema: { type: 'object' },
      },
    })
    await screen.getByRole('button', { name: 'fate_judgment_user' }).click()
    await expect
      .element(screen.getByText('Epoch {{ epoch }}'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Output schema')).toBeInTheDocument()
    await userEvent.fill(
      screen.getByLabelText('Search prompts'),
      'nothing like it'
    )
    await expect
      .element(screen.getByText('No prompt matches'))
      .toBeInTheDocument()
  })

  it('shows the error of a failed catalogue', async () => {
    const { screen } = await renderScreen(<PromptCatalogueView />, {
      ...BASE,
      'GET /api/prompt-context/catalogue': failure(
        500,
        'The catalogue is sealed.'
      ),
    })
    await expect
      .element(screen.getByText('The catalogue is sealed.'))
      .toBeInTheDocument()
  })
})

describe('tired motifs', () => {
  it('pins a motif and clears an override', async () => {
    const { screen, server } = await renderScreen(<TiredMotifsView />, {
      ...BASE,
      'GET /api/prompt-context/tired-motifs': MOTIFS,
      'PUT /api/prompt-context/tired-motifs/overrides': MOTIFS,
      'POST /api/prompt-context/tired-motifs/overrides/clear': MOTIFS,
    })
    await screen.getByRole('radio', { name: 'Pinned' }).click()
    await expect
      .poll(
        () =>
          server.callsTo('PUT /api/prompt-context/tired-motifs/overrides')
            .length
      )
      .toBe(1)
    expect(
      server.callsTo('PUT /api/prompt-context/tired-motifs/overrides')[0].body
    ).toEqual({
      motif: 'weeping moon',
      mode: 'pinned',
      world_id: null,
    })
    await screen.getByRole('button', { name: 'Clear' }).click()
    await expect
      .poll(
        () =>
          server.callsTo(
            'POST /api/prompt-context/tired-motifs/overrides/clear'
          ).length
      )
      .toBe(1)
  })
})
