import { failure } from '@/test-utils/mockServer'
import { renderScreen } from '@/test-utils/renderScreen'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { page } from 'vitest/browser'
import {
  type EntryPageProps,
  type EntryPages,
  EntryWindow,
} from '@/components/layout/entry/EntryWindow'
import { ENTRY_KINDS } from '@/components/layout/entry/entryStack'
import { PageTitle } from '@/components/typography'
import { AudiencePanel } from './AudiencePanel'
import { ExchangeList } from './AudienceTranscript'
import { BeginAnewButton } from './BeginAnewButton'
import { PresenceStage } from './PresenceStage'
import { SpeakerRail } from './SpeakerRail'
import { SummonForm } from './SummonForm'
import { audienceSpeaker } from './looks'
import {
  presenceEvent,
  presenceExchange,
  presenceSession,
  speakerCard,
  speakerPage,
  speakerSummary,
  sessionView,
  speakerView,
} from './presenceFixtures'
import { usePresence } from './presenceStore'

function reset() {
  usePresence.setState({ live: {}, drafts: {} })
}

beforeEach(reset)
afterEach(reset)

const SPEAKERS = speakerPage([
  speakerSummary(),
  speakerSummary({
    node_id: 12,
    name: 'Orla Vane',
    kind: 'entity',
    entity_type: 'mortal',
    group: 'mortals',
    open_session_id: 4,
  }),
])

const DEAD = speakerCard({
  dead: true,
  son_status: 'dead',
  death_epoch: 2,
  death_line: 'Ithren fell in the war of the vale.',
  can_act: false,
})

describe('Summon to Presence', () => {
  it('lists the speakers, narrows them by kind and the dead, and picks one', async () => {
    const picked: number[] = []
    const { screen, server } = await renderScreen(
      <SpeakerRail selected={null} onSelect={(id) => picked.push(id)} />,
      { 'GET /api/presence/speakers': SPEAKERS }
    )
    await expect
      .element(screen.getByRole('button', { name: 'Ithren, Sons' }))
      .toBeInTheDocument()
    await expect.element(screen.getByText('In audience')).toBeInTheDocument()
    await screen.getByRole('radio', { name: 'Mortals' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/presence/speakers')
          .some((call) => call.query.get('group') === 'mortals')
      )
      .toBe(true)
    await screen.getByRole('switch', { name: 'Include the dead' }).click()
    await expect
      .poll(() =>
        server
          .callsTo('GET /api/presence/speakers')
          .some((call) => call.query.get('dead') === 'true')
      )
      .toBe(true)
    await screen.getByRole('button', { name: 'Orla Vane, Mortals' }).click()
    expect(picked).toEqual([12])
  })

  it('summons with the chosen guise and record', async () => {
    const { screen, server } = await renderScreen(
      <SummonForm speaker={speakerCard()} modelEnabled />,
      { 'POST /api/presence/sessions': sessionView() }
    )
    await expect
      .element(screen.getByRole('radio', { name: /Creator/ }))
      .toHaveAttribute('aria-checked', 'true')
    for (const label of ['Unnamed power', 'Dream voice', 'Ordinary voice'])
      await expect
        .element(screen.getByRole('radio', { name: new RegExp(label) }))
        .toHaveAttribute('aria-checked', 'false')
    await screen.getByRole('radio', { name: /Dream voice/ }).click()
    await screen.getByRole('radio', { name: /Off the record/ }).click()
    await expect
      .element(screen.getByText('It reads the world but never acts.'))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Summon Ithren' }).click()
    await expect
      .poll(() => server.callsTo('POST /api/presence/sessions'))
      .toHaveLength(1)
    expect(server.callsTo('POST /api/presence/sessions')[0].body).toEqual({
      node_id: 7,
      guise: 'dream_voice',
      record: 'off_record',
    })
  })

  it('tells a speaker that cannot act that it only reads on the record', async () => {
    const { screen } = await renderScreen(
      <SummonForm speaker={speakerCard({ can_act: false })} modelEnabled />
    )
    await expect
      .element(
        screen.getByText(
          'It reads the world only: the dead and foreign gods never act.'
        )
      )
      .toBeInTheDocument()
  })

  it('shows the transcript with its tool calls, the memory kept and a copy button on every message', async () => {
    const exchange = presenceExchange({
      events: [
        presenceEvent('thought', { text: 'The Creator is here.' }),
        presenceEvent(
          'tool_call',
          { call_id: 'c1', arguments: { query: 'the vale' } },
          'read_region'
        ),
        presenceEvent(
          'tool_result',
          { call_id: 'c1', text: 'The vale is quiet.', is_error: false },
          'read_region'
        ),
      ],
    })
    const { screen } = await renderScreen(
      <ExchangeList
        exchanges={[exchange]}
        boundary={1}
        speaker={audienceSpeaker(speakerCard())}
        session={presenceSession()}
      />,
      { 'GET /api/names': [] }
    )
    await expect
      .element(screen.getByText('What do you seek?'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Only your word, Creator.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('The Creator asked what I seek.'))
      .toBeInTheDocument()
    await expect.element(screen.getByText('Read region')).toBeInTheDocument()
    for (const name of [
      'Copy your words',
      'Copy the answer',
      'Copy what it will remember',
    ])
      await expect.element(screen.getByRole('button', { name })).toBeEnabled()
    await screen.getByRole('button', { name: 'Details' }).click()
    await expect
      .element(screen.getByText('The vale is quiet.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Copy what came back' }))
      .toBeEnabled()
  })

  it('streams the words and tools of a running exchange', async () => {
    usePresence.setState({
      live: {
        2: {
          text: 'I hear yo',
          calls: [
            {
              callId: 'c9',
              tool: 'read_region',
              phase: 'preparing',
              error: false,
            },
          ],
        },
      },
    })
    const { screen } = await renderScreen(
      <ExchangeList
        exchanges={[
          presenceExchange({
            id: 2,
            status: 'running',
            reply_text: '',
            remember_text: '',
            finished_at: null,
          }),
        ]}
        boundary={1}
        speaker={audienceSpeaker(speakerCard())}
        session={presenceSession()}
      />,
      { 'GET /api/names': [] }
    )
    await expect.element(screen.getByText('I hear yo')).toBeInTheDocument()
    await expect
      .element(screen.getByText('Choosing its words'))
      .toBeInTheDocument()
  })

  it('draws the dead with the seal on the stage', async () => {
    const { screen } = await renderScreen(
      <PresenceStage view={speakerView({ card: DEAD })} />
    )
    await expect.element(screen.getByText('† Ithren')).toBeInTheDocument()
    await expect
      .poll(() => screen.getByText('Summoned from death').elements().length)
      .toBe(2)
    await expect
      .element(screen.getByText('Ithren fell in the war of the vale.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByText('Reads the world only'))
      .toBeInTheDocument()
  })

  it('keeps Summon disabled with its reason when no model is on', async () => {
    const { screen } = await renderScreen(
      <SummonForm speaker={speakerCard()} modelEnabled={false} />
    )
    await expect
      .element(screen.getByRole('button', { name: 'Summon Ithren' }))
      .toBeDisabled()
  })

  it('seals every reply of a speaker summoned from death', async () => {
    const { screen } = await renderScreen(
      <ExchangeList
        exchanges={[
          presenceExchange(),
          presenceExchange({ id: 2, ordinal: 2 }),
        ]}
        boundary={1}
        speaker={audienceSpeaker(DEAD)}
        session={presenceSession({ dead_when_summoned: true })}
      />,
      { 'GET /api/names': [] }
    )
    await expect
      .poll(() => screen.getByText('Summoned from death').elements().length)
      .toBe(2)
  })

  it('draws the line beyond memory above forgotten exchanges', async () => {
    const { screen } = await renderScreen(
      <ExchangeList
        exchanges={[
          presenceExchange(),
          presenceExchange({ id: 2, ordinal: 2 }),
        ]}
        boundary={2}
        speaker={audienceSpeaker(speakerCard())}
        session={presenceSession()}
      />,
      { 'GET /api/names': [] }
    )
    await expect
      .element(screen.getByRole('separator', { name: 'Beyond memory' }))
      .toBeInTheDocument()
  })

  it('holds an audience: the memory kept, the words sent and the speaker stopped', async () => {
    const done = presenceExchange()
    const running = presenceExchange({
      id: 2,
      ordinal: 2,
      status: 'running',
      reply_text: '',
      remember_text: '',
      finished_at: null,
    })
    let view = sessionView({ exchanges: [done] })
    const { screen, server } = await renderScreen(
      <AudiencePanel
        speaker={speakerCard()}
        session={presenceSession({ exchange_count: 1 })}
        modelEnabled
      />,
      {
        'GET /api/names': [],
        'GET /api/presence/sessions/{session_id}': () => view,
        'POST /api/presence/sessions/{session_id}/exchanges': () => {
          view = sessionView({
            exchanges: [done, running],
            running_exchange_id: 2,
          })
          return { exchange_id: 2, session_id: 3, ordinal: 2 }
        },
        'POST /api/presence/exchanges/{exchange_id}/cancel': () =>
          presenceExchange({ id: 2, ordinal: 2, status: 'cancelled' }),
      }
    )
    await expect
      .element(screen.getByText('Only your word, Creator.'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByLabelText('1 of 10 exchanges in mind'))
      .toBeInTheDocument()
    await expect
      .element(screen.getByRole('button', { name: 'Speak' }))
      .toBeDisabled()
    await screen
      .getByRole('textbox', { name: 'Your words to Ithren' })
      .fill('Tell me of the vale.')
    await screen.getByRole('button', { name: 'Speak' }).click()
    await expect
      .poll(() =>
        server.callsTo('POST /api/presence/sessions/{session_id}/exchanges')
      )
      .toHaveLength(1)
    expect(
      server.callsTo('POST /api/presence/sessions/{session_id}/exchanges')[0]
        .body
    ).toEqual({ text: 'Tell me of the vale.' })
    await screen.getByRole('button', { name: 'Stop' }).click()
    await expect
      .poll(() =>
        server.callsTo('POST /api/presence/exchanges/{exchange_id}/cancel')
      )
      .toHaveLength(1)
  })

  it('asks before beginning anew and says what an off-record audience loses', async () => {
    const session = presenceSession({ record: 'off_record' })
    const { screen, server } = await renderScreen(
      <BeginAnewButton session={session} name='Ithren' busy={false} />,
      {
        'POST /api/presence/sessions/{session_id}/close': {
          session_id: 3,
          node_id: 7,
          kept: false,
        },
      }
    )
    await screen.getByRole('button', { name: 'Begin anew' }).click()
    await expect
      .element(screen.getByRole('alertdialog', { name: 'Begin anew?' }))
      .toBeVisible()
    await expect
      .element(screen.getByText(/every word of it is deleted now/))
      .toBeInTheDocument()
    await screen.getByRole('button', { name: 'Delete and begin anew' }).click()
    await expect
      .poll(() =>
        server.callsTo('POST /api/presence/sessions/{session_id}/close')
      )
      .toHaveLength(1)
    expect(
      server.callsTo('POST /api/presence/sessions/{session_id}/close')[0].path
    ).toBe('/api/presence/sessions/3/close')
  })

  it('keeps Begin anew disabled with its reason while the speaker answers', async () => {
    const { screen } = await renderScreen(
      <BeginAnewButton session={presenceSession()} name='Ithren' busy />
    )
    await expect
      .element(screen.getByRole('button', { name: 'Begin anew' }))
      .toBeDisabled()
  })
})

function NamedPage({ id }: EntryPageProps) {
  if (id === undefined) return null
  return <PageTitle>Ithren</PageTitle>
}

const PAGES = Object.fromEntries(
  ENTRY_KINDS.map((kind) => [kind, NamedPage])
) as EntryPages

describe('Speak with them', () => {
  beforeEach(async () => {
    await page.viewport(1400, 900)
  })

  it('shows in the entry window of a speaker and opens its presence', async () => {
    const { screen } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      { 'GET /api/presence/speakers/{node_id}': speakerView() },
      '/?entry=son:7'
    )
    const link = screen.getByRole('link', { name: 'Speak with them' })
    await expect.element(link).toBeVisible()
    await expect.element(link).toHaveAttribute('href', '/presence?node=7')
  })

  it('stays away from an entry that cannot speak', async () => {
    const { screen, server } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      {
        'GET /api/presence/speakers/{node_id}': failure(
          404,
          'This record cannot speak.'
        ),
      },
      '/?entry=entity:30'
    )
    await expect
      .poll(() => server.callsTo('GET /api/presence/speakers/{node_id}'))
      .toHaveLength(1)
    await expect
      .element(screen.getByRole('button', { name: /God's controls/ }))
      .toBeVisible()
    await expect
      .element(screen.getByRole('link', { name: 'Speak with them' }))
      .not.toBeInTheDocument()
  })

  it('never asks for a world, a star or the Creator', async () => {
    const { screen, server } = await renderScreen(
      <EntryWindow pages={PAGES} />,
      { 'GET /api/presence/speakers/{node_id}': speakerView() },
      '/?entry=world:5'
    )
    await expect
      .element(screen.getByRole('button', { name: /God's controls/ }))
      .toBeVisible()
    expect(server.callsTo('GET /api/presence/speakers/{node_id}')).toHaveLength(
      0
    )
  })
})
