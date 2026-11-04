import {
  ACCEPTED_ACTION,
  callsTo,
  failure,
  onApi,
  renderApp,
  resetApi,
} from '@/test-utils/fakeApi'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Button } from '@/components/ui/button'
import { type EntityContext } from './actions/context'
import { fixedCost, useLoreGate } from './actions/gate'
import { useLoreMutation } from './api/mutations'
import { useRuleLookup } from './api/rules'
import { scrollToSection } from './scrollToSection'
import {
  curseBlock,
  interventionCost,
  miracleBlock,
} from './sections/handOfGod'

vi.mock('@/api/client', async () => {
  const { createFakeClient } = await import('@/test-utils/fakeApi')
  return { api: createFakeClient() }
})

function Runner({ cost }: { cost?: number }) {
  const gate = useLoreGate()
  const mutation = useLoreMutation({
    run: () =>
      fetch('/api/ping', { method: 'POST' }).then(async (response) => {
        if (!response.ok) throw new Error((await response.json()).detail)
        return response.json()
      }),
    success: 'Ping done',
  })
  const reason = gate.reason({ cost, world: true })
  return (
    <Button
      disabled={reason !== null || mutation.isPending}
      disabledReason={reason ?? undefined}
      onClick={() => mutation.mutate()}
    >
      Ping
    </Button>
  )
}

function stub(response: () => Response) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => response())
  )
}

function serveState(essence: number, running = false, readOnly = false) {
  onApi('GET', '/api/state', {
    creator: { essence },
    epoch_running: running,
    read_only: readOnly,
    llm_enabled: true,
    world: { epoch: 4 },
  })
}

describe('lore action gate and runner', () => {
  beforeEach(() => {
    resetApi()
    vi.unstubAllGlobals()
  })

  it('reads the cost of a catalogue entry only when it is fixed', () => {
    expect(fixedCost('Free')).toBe(0)
    expect(fixedCost('30 essence')).toBe(30)
    expect(fixedCost('60 + 5 per power level')).toBeNull()
    expect(fixedCost(undefined)).toBeNull()
  })

  it('explains the missing essence, the running epoch and the read-only world', async () => {
    serveState(5)
    const poor = await renderApp(<Runner cost={30} />)
    await expect
      .element(poor.screen.getByRole('button', { name: 'Ping' }))
      .toHaveAttribute('aria-description', '30 essence needed; you have 5.')
    resetApi()
    serveState(500, true)
    const busy = await renderApp(<Runner cost={30} />)
    await expect
      .element(busy.screen.getByRole('button', { name: 'Ping' }).last())
      .toHaveAttribute(
        'aria-description',
        'An epoch is running; this opens when it ends.'
      )
    resetApi()
    serveState(500, false, true)
    const guest = await renderApp(<Runner />)
    await expect
      .element(guest.screen.getByRole('button', { name: 'Ping' }).last())
      .toHaveAttribute('aria-description', 'A guest world is open read-only.')
  })

  it('locks the button while it runs, then shows the success toast', async () => {
    serveState(500)
    stub(() => Response.json(ACCEPTED_ACTION))
    const { screen } = await renderApp(<Runner cost={10} />)
    await screen.getByRole('button', { name: 'Ping' }).click()
    await expect.element(screen.getByText('Ping done')).toBeInTheDocument()
  })

  it('shows the API error text as an error toast', async () => {
    serveState(500)
    stub(() =>
      Response.json(failure(409, 'The tide is wrong.').body, { status: 409 })
    )
    const { screen } = await renderApp(<Runner />)
    await screen.getByRole('button', { name: 'Ping' }).click()
    await expect
      .element(screen.getByText('The tide is wrong.'))
      .toBeInTheDocument()
  })

  it('offers undo when the ledger recorded the action', async () => {
    serveState(500)
    onApi('POST', '/api/ledger/12/undo', {
      entry_id: 12,
      applied: ['entity:7.legitimacy'],
      conflicts: [],
    })
    stub(() => Response.json({ ...ACCEPTED_ACTION, ledger_entry_id: 12 }))
    const { screen } = await renderApp(<Runner />)
    await screen.getByRole('button', { name: 'Ping' }).click()
    const undo = screen.getByRole('button', { name: 'Undo' })
    await expect.element(undo).toBeVisible()
    await expect
      .poll(async () => {
        if (callsTo('POST', '/api/ledger/12/undo').length === 0)
          await undo.click()
        return callsTo('POST', '/api/ledger/12/undo').length
      })
      .toBe(1)
    await expect
      .element(screen.getByText('Undone', { exact: true }))
      .toBeInTheDocument()
  })
})

function RuleProbe() {
  const lookup = useRuleLookup()
  return (
    <p>{`value ${lookup('cosmic_horror.clouding_threshold')} missing ${lookup('x.y')}`}</p>
  )
}

describe('rule lookup', () => {
  beforeEach(resetApi)

  it('resolves rules by namespace and key and reports unknown ones as undefined', async () => {
    onApi('GET', '/api/rules', [
      { namespace: 'cosmic_horror', key: 'clouding_threshold', value: 40 },
    ])
    const { screen } = await renderApp(<RuleProbe />)
    await expect
      .element(screen.getByText('value 40 missing undefined'))
      .toBeInTheDocument()
  })
})

describe('section scrolling and intervention rules', () => {
  it('scrolls the target section into view and ignores unknown ids', () => {
    const target = document.createElement('div')
    target.id = 'section-probe'
    const scroll = vi.fn()
    target.scrollIntoView = scroll
    document.body.append(target)
    scrollToSection('section-probe')
    expect(scroll).toHaveBeenCalledWith({ behavior: 'smooth', block: 'start' })
    expect(() => scrollToSection('missing')).not.toThrow()
    target.remove()
  })

  it('reads intervention costs from the catalogue text', () => {
    const text = 'miracle 15, disaster 20, curse 15, teaching 12'
    expect(interventionCost(text, 'miracle')).toBe(15)
    expect(interventionCost(text, 'teach_knowledge')).toBe(12)
    expect(interventionCost(undefined, 'curse')).toBeNull()
  })

  function context(overrides: Partial<Record<string, unknown>>): EntityContext {
    return {
      type: 'settlement',
      entity: { name: 'Velmora', stats: { prosperity: 100, defense: 100 } },
      detail: { tags: [] },
      bonds: [],
      flags: new Set<string>(),
      ...overrides,
    } as unknown as EntityContext
  }

  it('blocks a miracle that would change nothing, with the reason', () => {
    expect(miracleBlock(context({}), 'peace')).toBe(
      'Velmora is not hostile to anyone.'
    )
    expect(miracleBlock(context({}), 'bounty')).toBe(
      'Velmora is already at its fullest.'
    )
    expect(
      miracleBlock(
        context({ flags: new Set(['protected_from_disaster']) }),
        'protection'
      )
    ).toBe('Velmora is already protected.')
    const hostile = context({
      bonds: [{ state: 'active', kind: 'enemy', war_id: null }],
    })
    expect(miracleBlock(hostile, 'peace')).toBeNull()
  })

  it('blocks a curse on a record already cursed with no stat left', () => {
    const cursed = context({
      flags: new Set(['cursed']),
      entity: { name: 'Velmora', stats: { prosperity: 0, defense: 0 } },
    })
    expect(curseBlock(cursed)).toBe(
      'Velmora is already cursed and has no stat left to lower.'
    )
    expect(curseBlock(context({}))).toBeNull()
  })
})
