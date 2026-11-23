import { useState } from 'react'
import {
  Coins,
  Flag,
  Flame,
  Heart,
  Medal,
  PenLine,
  Swords,
  Trophy,
  Users,
} from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { KpiTile, PagedList } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { VALUE_ICONS } from '@/features/entity/mind/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type PursuitsNodeView, usePursuitsAction } from './api'
import { CLUB_KINDS, FANDOM_LINES, MOVEMENT_ICON } from './labels'
import {
  FACTION_TYPES,
  FIXER_TYPES,
  FORM_TYPES,
  LINE_TYPES,
  MANY,
  MAYBE,
  REALM_TYPES,
  SPAN,
  STRUCTURE_TYPES,
  TOWN_TYPES,
  usePursuitsRow,
  withNone,
} from './model'

type ValueAxis = components['schemas']['ValueAxis']
type Movement = NonNullable<PursuitsNodeView['movement']>
type Club = PursuitsNodeView['clubs'][number]
type League = NonNullable<PursuitsNodeView['league']>
type Match = PursuitsNodeView['matches'][number]
type Bet = PursuitsNodeView['bets'][number]

const AXIS_TABLE = table(VALUE_ICONS)

function axisLabel(axis: string): string {
  return VALUE_ICONS[axis]?.label ?? axis
}

function ManifestoEditor({
  row,
  blocked,
}: {
  row: Movement
  blocked: string | null
}) {
  const [axis, setAxis] = useState('')
  const [value, setValue] = useState('')
  const writing = usePursuitsAction(
    'art_movement:manifesto',
    (_: void) => ({
      faction_id: row.faction.id,
      axis: axis as ValueAxis,
      value: value === '' ? null : Number(value),
    }),
    'The manifesto is rewritten'
  )
  const busy = why(
    blocked ?? (axis === '' ? 'Choose a value' : null),
    writing.isPending
  )
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 @md/tiles:grid-cols-3'>
      <MindPicker
        label='Value in the manifesto'
        value={axis}
        table={AXIS_TABLE}
        placeholder='Choose a value'
        blocked={blocked}
        onPick={setAxis}
      />
      <NumberField
        label='How strongly (empty strikes it)'
        value={value}
        min={-SPAN}
        max={SPAN}
        placeholder='Strike it'
        blocked={blocked}
        onChange={setValue}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => writing.mutate()}
      >
        <PenLine />
        Rewrite it
      </Button>
    </div>
  )
}

function MovementCard({
  row,
  blocked,
}: {
  row: Movement
  blocked: string | null
}) {
  const action = usePursuitsRow(
    'art_movement:edit',
    'art_movement:delete',
    { faction_id: row.faction.id },
    blocked
  )
  const lines = Object.entries(row.manifesto)
  return (
    <Held
      icon={MOVEMENT_ICON}
      tone={row.orthodoxy ? 'gold' : 'verdigris'}
      title={row.faction.name}
      caption={`An art movement since epoch ${row.founded_epoch}${row.orthodoxy ? ' · the orthodoxy of its people' : ''}`}
      removeLabel='End the movement'
      editTitle='Set the art movement'
      note='The makers of a town band into a school with a manifesto drawn from the values its founder holds dearest. Patrons who favour its form gather to it; it may scandalise its town and stir the crowds; with enough patrons it becomes the orthodoxy of its people, and its members’ works enter their canon.'
      fields={[
        {
          key: 'art_form_entity_id',
          label: 'Its form',
          kind: 'node',
          types: FORM_TYPES,
        },
        {
          key: 'orthodoxy',
          label: 'The orthodoxy',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'scandals',
          label: 'Scandals',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        { key: 'patrons', label: 'Patrons', kind: 'number', min: 0, max: MANY },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        row.orthodoxy ? (
          <Badge size='sm' variant='warning'>
            Orthodoxy
          </Badge>
        ) : undefined
      }
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <KpiTile
            label='Patrons'
            value={row.patrons}
            icon={Users}
            tone='gold'
          />
          <KpiTile
            label='Scandals'
            value={row.scandals}
            icon={Flame}
            tone={row.scandals > 0 ? 'danger' : 'muted'}
          />
        </div>
      </div>
      <Facts
        items={[
          ['Its form', <Ref key='form' node={row.art_form} empty='any form' />],
        ]}
      />
      {lines.length === 0 ? (
        <Muted variant='caption'>The manifesto holds no value yet.</Muted>
      ) : (
        <PagedList
          items={lines}
          initial={6}
          noun={['value', 'values']}
          as='ul'
          className='flex min-w-0 flex-col gap-1'
          itemKey={(item) => item[0]}
        >
          {([axis, value]) => (
            <li key={axis} className='min-w-0'>
              <Meter
                label={`${axisLabel(axis)} (${value})`}
                value={Math.abs(value)}
                max={SPAN}
                tone={value >= 0 ? 'success' : 'destructive'}
                icon={VALUE_ICONS[axis]?.icon ?? Flag}
              />
            </li>
          )}
        </PagedList>
      )}
      <div className='@container/tiles min-w-0'>
        <ManifestoEditor row={row} blocked={action.busy} />
      </div>
    </Held>
  )
}

export function MovementPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  const [town, setTown] = useState<number | null>(
    kind === 'settlement' ? nodeId : null
  )
  const founding = usePursuitsAction(
    'art_movement:create',
    (_: void) => ({ town_id: town ?? 0 }),
    'The makers band into a movement'
  )
  const busy = why(
    blocked ?? (town === null ? 'Choose a town where makers live' : null),
    founding.isPending
  )
  return (
    <div data-surface='MovementPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-art-movements'
        title='Patrons and scandals of the movement'
        legend={[
          { text: 'Patrons', variant: 'success' },
          { text: 'The mark is its scandals', variant: 'outline' },
        ]}
        rows={
          data.movement
            ? [
                {
                  key: data.movement.faction.id,
                  caption: `${data.movement.faction.name}: ${plural(data.movement.patrons, 'patron', 'patrons')}, ${plural(data.movement.scandals, 'scandal', 'scandals')}`,
                  segments: [
                    { value: data.movement.patrons, fill: 'fill-success' },
                  ],
                  mark: data.movement.scandals,
                },
              ]
            : []
        }
        noun={['movement', 'movements']}
        empty='This is no art movement.'
      />
      {data.movement && <MovementCard row={data.movement} blocked={blocked} />}
      <ForgeCard
        icon={MOVEMENT_ICON}
        tone='verdigris'
        title='Band makers into a movement'
        note='The makers of works who live in the town band into a movement led by the most powerful of them.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => founding.mutate()}
          >
            <Flag />
            Found it
          </Button>
        }
      >
        <NodePicker
          label='Town'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
      </ForgeCard>
    </div>
  )
}

function ClubCard({ row, blocked }: { row: Club; blocked: string | null }) {
  const action = usePursuitsRow(
    'club:edit',
    'club:delete',
    { faction_id: row.faction.id },
    blocked
  )
  const kind = CLUB_KINDS[row.kind]
  const line = FANDOM_LINES[row.line]
  return (
    <Held
      icon={kind.icon}
      tone={row.bought_by ? 'warning' : kind.tone}
      title={row.faction.name}
      caption={`${kind.label} · ${plural(row.wins, 'win', 'wins')}, ${plural(row.losses, 'loss', 'losses')} · founded in epoch ${row.founded_epoch}`}
      removeLabel='Dissolve the club'
      editTitle='Set the club'
      note='A club plays the other clubs of its league each epoch; wins raise its rating and fandom and losses lower them, and the towns that back it wager their wealth. Where its fans split along class, district or faith they give it leverage: a lost match may then spark a riot, and a ruler low in legitimacy may buy its favour and borrow its standing.'
      fields={[
        {
          key: 'kind',
          label: 'What it plays',
          kind: 'pick',
          table: table(CLUB_KINDS),
        },
        {
          key: 'league_entity_id',
          label: 'League',
          kind: 'node',
          types: FACTION_TYPES,
        },
        {
          key: 'arena_entity_id',
          label: 'Arena',
          kind: 'node',
          types: STRUCTURE_TYPES,
        },
        { key: 'wins', label: 'Wins', kind: 'number', min: 0, max: MANY },
        { key: 'losses', label: 'Losses', kind: 'number', min: 0, max: MANY },
        { key: 'rating', label: 'Rating', kind: 'number', min: 0, max: SPAN },
        { key: 'fandom', label: 'Fandom', kind: 'number', min: 0, max: SPAN },
        {
          key: 'line',
          label: 'Fans split by',
          kind: 'pick',
          table: table(FANDOM_LINES),
        },
        {
          key: 'line_entity_id',
          label: 'District or church of the fans',
          kind: 'node',
          types: LINE_TYPES,
        },
        {
          key: 'leverage',
          label: 'Leverage',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'bought_by_entity_id',
          label: 'Bought by',
          kind: 'node',
          types: REALM_TYPES,
        },
        {
          key: 'fixed_by_entity_id',
          label: 'Its next contest fixed by',
          kind: 'node',
          types: FIXER_TYPES,
        },
        {
          key: 'fixed_winner_entity_id',
          label: 'Club the fixing makes win',
          kind: 'node',
          types: FACTION_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={line} />}
    >
      <Meter
        label={`Rating (${row.rating} of ${SPAN})`}
        value={row.rating}
        tone='info'
        icon={Trophy}
      />
      <Meter
        label={`Fandom (${row.fandom} of ${SPAN})`}
        value={row.fandom}
        tone='success'
        icon={Heart}
      />
      <Meter
        label={`Leverage (${row.leverage} of ${SPAN})`}
        value={row.leverage}
        tone='warning'
        icon={Flame}
      />
      <Facts
        items={[
          ['League', <Ref key='league' node={row.league} empty='none' />],
          ['Arena', <Ref key='arena' node={row.arena} empty='none' />],
          ['Fans split by', line.label],
          [
            'District or church of the fans',
            <Ref key='line' node={row.line_node} empty='none' />,
          ],
          [
            'Bought by',
            <Ref key='bought' node={row.bought_by} empty='no ruler' />,
          ],
          [
            'Next contest fixed by',
            <Ref key='fixer' node={row.fixed_by} empty='no one' />,
          ],
          [
            'Fixed to win',
            <Ref key='fixed' node={row.fixed_winner} empty='no club' />,
          ],
        ]}
      />
    </Held>
  )
}

export function ClubPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  const [town, setTown] = useState<number | null>(
    kind === 'settlement' ? nodeId : null
  )
  const [clubKind, setClubKind] = useState('')
  const founding = usePursuitsAction(
    'club:create',
    (_: void) => ({
      town_id: town ?? 0,
      kind: clubKind === '' ? null : (clubKind as Club['kind']),
    }),
    'A club is founded'
  )
  const busy = why(
    blocked ?? (town === null ? 'Choose a town' : null),
    founding.isPending
  )
  return (
    <div data-surface='ClubPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-club-leverage'
        title='Fandom and leverage of each club'
        legend={[
          { text: 'Fandom', variant: 'success' },
          { text: 'The mark is its leverage', variant: 'outline' },
        ]}
        rows={data.clubs.map((row) => ({
          key: row.faction.id,
          caption: `${row.faction.name}: fandom ${row.fandom}, leverage ${row.leverage}, fans split by ${FANDOM_LINES[row.line].label.toLowerCase()}`,
          segments: [{ value: row.fandom, fill: 'fill-success' }],
          mark: row.leverage,
        }))}
        max={SPAN}
        noun={['club', 'clubs']}
        empty='No club touches this.'
      />
      <Listed
        title='Clubs'
        items={data.clubs}
        empty='No club touches this.'
        noun={['club', 'clubs']}
        itemKey={(item) => item.faction.id}
      >
        {(item) => <ClubCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Trophy}
        tone='gold'
        title='Found a club'
        note='A club forms in the town and plays in the arena or stadium there, if it has one.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => founding.mutate()}
          >
            <Trophy />
            Found it
          </Button>
        }
      >
        <NodePicker
          label='Town'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <MindPicker
          label='What it plays'
          value={clubKind}
          table={table(CLUB_KINDS)}
          placeholder='Let it be chosen'
          blocked={blocked}
          onPick={setClubKind}
        />
      </ForgeCard>
    </div>
  )
}

function LeagueCard({ row, blocked }: { row: League; blocked: string | null }) {
  const action = usePursuitsRow(
    'league:edit',
    'league:delete',
    { faction_id: row.faction.id },
    blocked
  )
  return (
    <Held
      icon={Medal}
      tone='info'
      title={row.faction.name}
      caption={`Season begun in epoch ${row.season_epoch}`}
      removeLabel='Dissolve the league'
      editTitle='Set the league'
      note='A league gathers the clubs of a realm. Each epoch its clubs are drawn against each other; when a season ends the club with the best record is named champion.'
      fields={[
        {
          key: 'polity_entity_id',
          label: 'Realm',
          kind: 'node',
          types: REALM_TYPES,
        },
        {
          key: 'champion_entity_id',
          label: 'Champion',
          kind: 'node',
          types: FACTION_TYPES,
        },
        {
          key: 'season_epoch',
          label: 'Season begun in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Realm', <Ref key='realm' node={row.polity} empty='none' />],
          [
            'Champion',
            <Ref key='champion' node={row.champion} empty='none named yet' />,
          ],
        ]}
      />
    </Held>
  )
}

export function LeaguePanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  const [realm, setRealm] = useState<number | null>(
    kind === 'polity' ? nodeId : null
  )
  const [seat, setSeat] = useState<number | null>(null)
  const founding = usePursuitsAction(
    'league:create',
    (_: void) => ({ realm_id: realm ?? 0, town_id: seat }),
    'The realm gains a league'
  )
  const busy = why(
    blocked ??
      (realm === null
        ? 'Choose a realm'
        : data.league && data.league.polity?.id === realm
          ? 'That realm already has a league'
          : null),
    founding.isPending
  )
  const table_ = [...data.clubs].sort(
    (a, b) => b.wins - b.losses - (a.wins - a.losses)
  )
  return (
    <div data-surface='LeaguePanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-league-table'
        title='League table'
        legend={[
          { text: 'Wins', variant: 'success' },
          { text: 'Losses', variant: 'destructive' },
        ]}
        rows={table_.map((row) => ({
          key: row.faction.id,
          caption: `${row.faction.name}: ${plural(row.wins, 'win', 'wins')}, ${plural(row.losses, 'loss', 'losses')}`,
          segments: [
            { value: row.wins, fill: 'fill-success' },
            { value: row.losses, fill: 'fill-destructive' },
          ],
        }))}
        noun={['club', 'clubs']}
        empty='No club here plays in a league.'
      />
      {data.league ? (
        <LeagueCard row={data.league} blocked={blocked} />
      ) : (
        <Muted variant='caption'>No league is tied to this.</Muted>
      )}
      <ForgeCard
        icon={Medal}
        tone='info'
        title='Found a league'
        note='The realm gathers its clubs into a league seated in a town of your choosing.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => founding.mutate()}
          >
            <Medal />
            Found it
          </Button>
        }
      >
        <NodePicker
          label='Realm'
          value={realm}
          onChange={setRealm}
          blocked={blocked}
          types={REALM_TYPES}
        />
        <NodePicker
          label='Seat'
          value={seat}
          onChange={setSeat}
          blocked={blocked}
          types={TOWN_TYPES}
        />
      </ForgeCard>
    </div>
  )
}

function BetCard({
  row,
  matches,
  blocked,
}: {
  row: Bet
  matches: Match[]
  blocked: string | null
}) {
  const action = usePursuitsRow(
    'bet:edit',
    'bet:delete',
    { bet_id: row.id },
    blocked
  )
  const match = matches.find((item) => item.id === row.match_id)
  const outcome = row.won === null ? 'not settled' : row.won ? 'won' : 'lost'
  return (
    <Held
      icon={Coins}
      tone={row.won === null ? 'muted' : row.won ? 'success' : 'danger'}
      title={`${row.settlement.name} wagered ${row.stake} on ${row.club.name}`}
      caption={
        match
          ? `${match.home.name} against ${match.away.name}, epoch ${match.epoch} · ${outcome}`
          : outcome
      }
      removeLabel='Strike the bet'
      editTitle='Set the bet'
      note='A town wagers a share of its wealth on its club, more the keener its fans; it wins the stake back over again or loses it.'
      fields={[
        {
          key: 'club_entity_id',
          label: 'Club backed',
          kind: 'node',
          types: FACTION_TYPES,
        },
        { key: 'stake', label: 'Stake', kind: 'number', min: 0, max: MANY },
        { key: 'won', label: 'Outcome', kind: 'pick', table: MAYBE },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function MatchCard({ row, blocked }: { row: Match; blocked: string | null }) {
  const action = usePursuitsRow(
    'match:edit',
    'match:delete',
    { match_id: row.id },
    blocked
  )
  return (
    <Held
      icon={Swords}
      tone={row.riot ? 'danger' : 'info'}
      title={`${row.home.name} against ${row.away.name}`}
      caption={`Epoch ${row.epoch} · ${row.stake} wagered${row.riot ? ' · a riot followed' : ''}${row.fixing_exposed ? ' · found to be fixed' : ''}`}
      removeLabel='Strike the match'
      editTitle='Set the match'
      note='A match between two clubs: who won, how much the towns wagered, whether the loser’s fans rioted, and whether the contest was fixed and found out, voiding the wagers.'
      fields={[
        {
          key: 'home_entity_id',
          label: 'Home club',
          kind: 'node',
          types: FACTION_TYPES,
        },
        {
          key: 'away_entity_id',
          label: 'Away club',
          kind: 'node',
          types: FACTION_TYPES,
        },
        {
          key: 'winner_entity_id',
          label: 'Winner',
          kind: 'node',
          types: FACTION_TYPES,
        },
        { key: 'stake', label: 'Wagered', kind: 'number', min: 0, max: MANY },
        { key: 'riot', label: 'A riot followed', kind: 'pick', table: YES_NO },
        {
          key: 'fixed_by_entity_id',
          label: 'Fixed by',
          kind: 'node',
          types: FIXER_TYPES,
        },
        {
          key: 'fixing_exposed',
          label: 'The fixing came out',
          kind: 'pick',
          table: YES_NO,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        row.riot || row.fixing_exposed ? (
          <>
            {row.riot && (
              <Badge size='sm' variant='destructive'>
                Riot
              </Badge>
            )}
            {row.fixing_exposed && (
              <Badge size='sm' variant='warning'>
                Fixed
              </Badge>
            )}
          </>
        ) : undefined
      }
    >
      <Facts
        items={[
          ['League', <Ref key='league' node={row.league} empty='a friendly' />],
          ['Winner', <Ref key='winner' node={row.winner} empty='none' />],
          ['Fixed by', <Ref key='fixer' node={row.fixed_by} empty='no one' />],
        ]}
      />
    </Held>
  )
}

export function MatchPanel({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  const own = data.clubs.find((row) => row.faction.id === nodeId)
  const [home, setHome] = useState<number | null>(own ? nodeId : null)
  const [away, setAway] = useState<number | null>(null)
  const [winner, setWinner] = useState('')
  const [match, setMatch] = useState('')
  const [town, setTown] = useState<number | null>(null)
  const [backed, setBacked] = useState('')
  const [stake, setStake] = useState('')
  const playing = usePursuitsAction(
    'match:create',
    (_: void) => ({
      home_id: home ?? 0,
      away_id: away ?? 0,
      winner_id: winner === '' ? null : Number(winner),
    }),
    'The match is played'
  )
  const betting = usePursuitsAction(
    'bet:create',
    (_: void) => ({
      match_id: Number(match),
      town_id: town ?? 0,
      club_id: Number(backed),
      stake: stake === '' ? null : Number(stake),
    }),
    'The town wagers'
  )
  const sides: Record<string, string> = {}
  if (home !== null) sides[String(home)] = 'The home club'
  if (away !== null) sides[String(away)] = 'The away club'
  const chosen = data.matches.find((item) => String(item.id) === match)
  const backing: Record<string, string> = chosen
    ? {
        [String(chosen.home.id)]: chosen.home.name,
        [String(chosen.away.id)]: chosen.away.name,
      }
    : {}
  const matchTable = Object.fromEntries(
    data.matches.map((item) => [
      String(item.id),
      `${item.home.name} against ${item.away.name}, epoch ${item.epoch}`,
    ])
  )
  const playBusy = why(
    blocked ??
      (home === null || away === null
        ? 'Choose both clubs'
        : home === away
          ? 'A club cannot play itself'
          : null),
    playing.isPending
  )
  const betBusy = why(
    blocked ??
      (data.matches.length === 0
        ? 'No match here to wager on'
        : match === ''
          ? 'Choose a match'
          : town === null
            ? 'Choose a town'
            : backed === ''
              ? 'Choose the club it backs'
              : null),
    betting.isPending
  )
  return (
    <div data-surface='MatchPanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Matches'
        items={data.matches}
        empty='No match touches this.'
        noun={['match', 'matches']}
        itemKey={(item) => item.id}
      >
        {(item) => <MatchCard row={item} blocked={blocked} />}
      </Listed>
      <Listed
        title='Wagers'
        items={data.bets}
        empty='No wager touches this.'
        noun={['wager', 'wagers']}
        itemKey={(item) => item.id}
      >
        {(item) => (
          <BetCard row={item} matches={data.matches} blocked={blocked} />
        )}
      </Listed>
      <ForgeCard
        icon={Swords}
        tone='info'
        title='Play a match'
        note='Two clubs meet; leave the winner open to let the match decide, or name it. The towns behind them wager, and the loser’s fans may riot.'
        columns={3}
        action={
          <Button
            size='sm'
            disabled={playBusy !== null}
            disabledReason={playBusy ?? undefined}
            onClick={() => playing.mutate()}
          >
            <Swords />
            Play it
          </Button>
        }
      >
        <NodePicker
          label='Home club'
          value={home}
          onChange={setHome}
          blocked={blocked}
          types={FACTION_TYPES}
        />
        <NodePicker
          label='Away club'
          value={away}
          onChange={setAway}
          blocked={blocked}
          types={FACTION_TYPES}
        />
        <MindPicker
          label='Winner'
          value={winner}
          table={withNone(sides, 'Let the match decide')}
          placeholder='Let the match decide'
          blocked={blocked}
          onPick={(value) => setWinner(value === 'none' ? '' : value)}
        />
      </ForgeCard>
      <ForgeCard
        icon={Coins}
        tone='gold'
        title='Have a town wager'
        note='The town wagers on one of the two clubs: a share of its wealth as keen as its fans, or the stake you name.'
        columns={4}
        action={
          <Button
            size='sm'
            disabled={betBusy !== null}
            disabledReason={betBusy ?? undefined}
            onClick={() => betting.mutate()}
          >
            <Coins />
            Wager
          </Button>
        }
      >
        <MindPicker
          label='Match'
          value={match}
          table={matchTable}
          placeholder='Choose a match'
          blocked={blocked}
          onPick={setMatch}
        />
        <NodePicker
          label='Town'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <MindPicker
          label='Club it backs'
          value={backed}
          table={backing}
          placeholder='Choose a club'
          blocked={blocked}
          onPick={setBacked}
        />
        <NumberField
          label='Stake'
          value={stake}
          min={0}
          max={MANY}
          placeholder='A share of its wealth'
          blocked={blocked}
          onChange={setStake}
        />
      </ForgeCard>
    </div>
  )
}
