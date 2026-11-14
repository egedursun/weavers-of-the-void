import { useState } from 'react'
import { Clock, Dices, Hash, Plus, Telescope } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type CraftsNodeView, useCraftsAction } from './api'
import { AIDS, CLOCKS, GAME_KINDS, GAME_RULES, NOTATIONS } from './labels'
import { MANY, PEOPLE_TYPES, SPAN, useCraftsRow, useCraftsStep } from './model'

type View = CraftsNodeView
type Aid = View['aids'][number]
type ClockRow = NonNullable<View['clock']>
type Following = View['followings'][number]
type Numbers = NonNullable<View['numbers']>

const BASE_MIN = 2
const BASE_MAX = 60

function AidCard({
  holder,
  row,
  blocked,
}: {
  holder: number
  row: Aid
  blocked: string | null
}) {
  const action = useCraftsRow(
    'assistive_aid:edit',
    'assistive_aid:delete',
    { holder_id: holder, kind: row.kind },
    blocked
  )
  const aid = AIDS[row.kind]
  return (
    <Held
      icon={aid.icon}
      tone={aid.tone}
      title={aid.label}
      caption={`Quality ${row.quality} · since epoch ${row.since_epoch}`}
      removeLabel='Take the aid away'
      editTitle='Set the aid'
      note='Spectacles let the weak-sighted read, a magnifier sharpens fine craft, a hearing horn restores hearing, a cane restores walking and a telescope trains the eye on the sky.'
      fields={[
        { key: 'quality', label: 'Quality', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Quality (${row.quality} of ${SPAN})`}
        value={row.quality}
        tone='info'
        icon={aid.icon}
      />
    </Held>
  )
}

function ClockCard({
  town,
  row,
  blocked,
}: {
  town: number
  row: ClockRow
  blocked: string | null
}) {
  const action = useCraftsRow(
    'public_clock:edit',
    'public_clock:delete',
    { settlement_id: town },
    blocked
  )
  const clock = CLOCKS[row.kind]
  return (
    <Held
      icon={clock.icon}
      tone={clock.tone}
      title={`A public ${clock.label.toLowerCase()}`}
      caption={`Precision ${row.precision} · set up in epoch ${row.built_epoch}`}
      removeLabel='Take the clock down'
      editTitle='Set the clock'
      note='A public clock raises the output of its town and breeds the unrest of labour by the hour; a precise one speeds the levy and makes the sea roads of its port safer.'
      fields={[
        { key: 'kind', label: 'Clock', kind: 'pick', table: table(CLOCKS) },
        {
          key: 'precision',
          label: 'Precision',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'built_epoch',
          label: 'Set up in epoch',
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
      <Meter
        label={`Precision (${row.precision} of ${SPAN})`}
        value={row.precision}
        tone='warning'
        icon={Clock}
      />
    </Held>
  )
}

function FollowingCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: Following
  blocked: string | null
}) {
  const following = useCraftsRow(
    'game_following:edit',
    'game_following:delete',
    { people_id: people, game_id: row.game.id },
    blocked
  )
  const game = useCraftsRow(
    'game:edit',
    'game:delete',
    { record_id: row.game.id },
    blocked
  )
  const kind = GAME_KINDS[row.game.kind]
  return (
    <Held
      icon={kind.icon}
      tone={kind.tone}
      title={row.game.name}
      caption={`${kind.label} of ${GAME_RULES[row.game.rule].label.toLowerCase()} · popularity ${row.popularity} · taken up in epoch ${row.adopted_epoch}`}
      removeLabel='Leave the game'
      editTitle='Set how much they play it'
      note='Strategy games train nobles and officers in tactics, games of chance drain prosperity and breed crime, and ball games ease unrest; games spread to neighbouring peoples.'
      fields={[
        {
          key: 'popularity',
          label: 'Popularity',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'adopted_epoch',
          label: 'Taken up in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={following.busy}
      onEdit={following.onEdit}
      onRemove={following.onRemove}
    >
      <Meter
        label={`Popularity (${row.popularity} of ${SPAN})`}
        value={row.popularity}
        tone='success'
        icon={Dices}
      />
      <Held
        icon={kind.icon}
        tone='muted'
        title='The game itself'
        caption={`Made in epoch ${row.game.created_epoch}`}
        removeLabel='Forget the game everywhere'
        editTitle='Set the game'
        note='The game is the same wherever it is played; changing it changes it for every people that plays it.'
        fields={[
          { key: 'name', label: 'Game name', kind: 'text' },
          {
            key: 'kind',
            label: 'Game of',
            kind: 'pick',
            table: table(GAME_KINDS),
          },
          {
            key: 'rule',
            label: 'Won by',
            kind: 'pick',
            table: table(GAME_RULES),
          },
          {
            key: 'origin_entity_id',
            label: 'First played by',
            kind: 'node',
            types: PEOPLE_TYPES,
          },
        ]}
        locked={row.game.locked}
        blocked={game.busy}
        onEdit={game.onEdit}
        onRemove={game.onRemove}
      >
        <Facts
          items={[
            [
              'First played by',
              <Ref key='origin' node={row.game.origin} empty='no people' />,
            ],
          ]}
        />
      </Held>
    </Held>
  )
}

function NumbersCard({
  people,
  row,
  blocked,
}: {
  people: number
  row: Numbers
  blocked: string | null
}) {
  const action = useCraftsRow(
    'number_system:edit',
    'number_system:delete',
    { people_id: people },
    blocked
  )
  return (
    <Held
      icon={Hash}
      tone='verdigris'
      title={`Counting in base ${row.base}`}
      caption={`${NOTATIONS[row.notation].label}${row.zero ? ' · with a zero' : ''} · numeracy ${row.numeracy}`}
      removeLabel='Strike the number system'
      editTitle='Set the number system'
      note='Numeracy sharpens the taxes of their realm, the building of their works and the gaps their merchants trade on; a zero and writing by place each speed astronomy, architecture, trade and seafaring.'
      fields={[
        {
          key: 'base',
          label: 'Base',
          kind: 'number',
          min: BASE_MIN,
          max: BASE_MAX,
        },
        {
          key: 'notation',
          label: 'Written',
          kind: 'pick',
          table: table(NOTATIONS),
        },
        { key: 'zero', label: 'A zero', kind: 'pick', table: YES_NO },
        {
          key: 'numeracy',
          label: 'Numeracy',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Numeracy (${row.numeracy} of ${SPAN})`}
        value={row.numeracy}
        tone='warning'
        icon={Hash}
      />
    </Held>
  )
}

export function LearningPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: View
  blocked: string | null
}) {
  const mortal = kind === 'mortal'
  const town = kind === 'settlement'
  const people = data.people?.id ?? null
  const [aid, setAid] = useState('spectacles')
  const [clock, setClock] = useState('sundial')
  const [name, setName] = useState('')
  const [gameKind, setGameKind] = useState('board')
  const [rule, setRule] = useState('strategy')
  const [taken, setTaken] = useState(
    data.games[0] ? String(data.games[0].id) : ''
  )
  const giving = useCraftsAction(
    'assistive_aid:set',
    (_: void) => ({ holder_id: nodeId, kind: aid as Aid['kind'] }),
    'The aid is given'
  )
  const timing = useCraftsAction(
    'public_clock:set',
    (_: void) => ({ settlement_id: nodeId, kind: clock as ClockRow['kind'] }),
    'The town keeps its hours'
  )
  const making = useCraftsAction(
    'game:create',
    (_: void) => ({
      name: name.trim(),
      kind: gameKind as Following['game']['kind'],
      rule: rule as Following['game']['rule'],
      origin_entity_id: people,
    }),
    'The game is played'
  )
  const following = useCraftsAction(
    'game_following:set',
    (_: void) => ({ people_id: people ?? 0, game_id: Number(taken || '0') }),
    'The people take up the game'
  )
  const counting = useCraftsAction(
    'number_system:set',
    (_: void) => ({ people_id: people ?? 0 }),
    'The people count so'
  )
  const reading = useCraftsStep(
    'learning_aids:run',
    {},
    blocked,
    'Aids, games and numbers are read'
  )
  const aidBusy = why(
    blocked ??
      (!mortal
        ? 'Only a mortal takes an aid'
        : data.aids.some((row) => row.kind === aid)
          ? 'It has that aid already; adjust it above'
          : null),
    giving.isPending
  )
  const clockBusy = why(
    blocked ??
      (!town
        ? 'Only a town keeps a public clock'
        : data.clock
          ? 'It keeps a clock already; adjust it above'
          : null),
    timing.isPending
  )
  const makeBusy = why(
    blocked ?? (!name.trim() ? 'Name the game' : null),
    making.isPending
  )
  const followBusy = why(
    blocked ??
      (people === null
        ? 'Only a people takes up a game'
        : !taken
          ? 'No game is known yet'
          : null),
    following.isPending
  )
  const countBusy = why(
    blocked ??
      (people === null
        ? 'It belongs to no people'
        : data.numbers
          ? 'Its people counts already; adjust it above'
          : null),
    counting.isPending
  )
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div data-surface='AidsPanel' className='flex min-w-0 flex-col gap-4'>
        <Bars
          chart='chart-aids'
          title='Aids and their quality'
          legend={[{ text: 'Quality', variant: 'success' }]}
          rows={data.aids.map((row) => ({
            key: row.kind,
            caption: `${AIDS[row.kind].label}: quality ${row.quality}`,
            segments: [
              { value: Math.min(SPAN, row.quality), fill: 'fill-success' },
            ],
          }))}
          max={SPAN}
          noun={['aid', 'aids']}
          empty='It uses no aids.'
        />
        <Listed
          title='Aids'
          items={data.aids}
          empty='It uses no aids.'
          noun={['aid', 'aids']}
          itemKey={(item) => item.kind}
        >
          {(item) => <AidCard holder={nodeId} row={item} blocked={blocked} />}
        </Listed>
        {data.clock ? (
          <ClockCard town={nodeId} row={data.clock} blocked={blocked} />
        ) : (
          <Muted variant='caption'>No public clock keeps the hours here.</Muted>
        )}
        <ForgeCard
          icon={Telescope}
          tone='info'
          title='Aids and hours'
          note='Give a mortal an aid, or set up a public clock in a town.'
          columns={2}
          action={
            <div className='flex min-w-0 flex-wrap gap-2'>
              <StepButton
                icon={Telescope}
                label='Read aids, games and numbers now'
                busy={reading.busy}
                onClick={reading.run}
              />
              <Button
                size='sm'
                variant='outline'
                disabled={aidBusy !== null}
                disabledReason={aidBusy ?? undefined}
                onClick={() => giving.mutate()}
              >
                <Plus />
                Give the aid
              </Button>
              <Button
                size='sm'
                disabled={clockBusy !== null}
                disabledReason={clockBusy ?? undefined}
                onClick={() => timing.mutate()}
              >
                <Clock />
                Set up the clock
              </Button>
            </div>
          }
        >
          <MindPicker
            label='Aid'
            value={aid}
            table={table(AIDS)}
            placeholder='Choose'
            blocked={blocked}
            onPick={setAid}
          />
          <MindPicker
            label='Clock'
            value={clock}
            table={table(CLOCKS)}
            placeholder='Choose'
            blocked={blocked}
            onPick={setClock}
          />
        </ForgeCard>
      </div>
      <div data-surface='GamesPanel' className='flex min-w-0 flex-col gap-4'>
        <Bars
          chart='chart-games'
          title='Games and how much they are played'
          legend={[{ text: 'Popularity', variant: 'success' }]}
          rows={data.followings.map((row) => ({
            key: String(row.game.id),
            caption: `${row.game.name}: popularity ${row.popularity}`,
            segments: [
              { value: Math.min(SPAN, row.popularity), fill: 'fill-success' },
            ],
          }))}
          max={SPAN}
          noun={['game', 'games']}
          empty='Its people play no games yet.'
        />
        <Listed
          title='Games of its people'
          items={data.followings}
          empty='Its people play no games yet.'
          noun={['game', 'games']}
          itemKey={(item) => item.game.id}
        >
          {(item) => (
            <FollowingCard people={people ?? 0} row={item} blocked={blocked} />
          )}
        </Listed>
        <Bars
          chart='chart-numeracy'
          title='Numeracy of its people'
          legend={[{ text: 'Numeracy', variant: 'warning' }]}
          rows={
            data.numbers
              ? [
                  {
                    key: 'numeracy',
                    caption: `Base ${data.numbers.base}: numeracy ${data.numbers.numeracy}`,
                    segments: [
                      {
                        value: Math.min(SPAN, data.numbers.numeracy),
                        fill: 'fill-warning',
                      },
                    ],
                  },
                ]
              : []
          }
          max={SPAN}
          noun={['number system', 'number systems']}
          empty='Its people keeps no number system yet.'
        />
        {data.numbers && people !== null ? (
          <NumbersCard people={people} row={data.numbers} blocked={blocked} />
        ) : (
          <Muted variant='caption'>
            Its people keeps no number system yet.
          </Muted>
        )}
        <ForgeCard
          icon={Dices}
          tone='warning'
          title='Games and numbers'
          note='Make a game, let its people take up a known game, or read how its people count.'
          columns={2}
          action={
            <div className='flex min-w-0 flex-wrap gap-2'>
              <Button
                size='sm'
                variant='outline'
                disabled={makeBusy !== null}
                disabledReason={makeBusy ?? undefined}
                onClick={() => making.mutate()}
              >
                <Plus />
                Make the game
              </Button>
              <Button
                size='sm'
                variant='outline'
                disabled={followBusy !== null}
                disabledReason={followBusy ?? undefined}
                onClick={() => following.mutate()}
              >
                <Dices />
                Take it up
              </Button>
              <Button
                size='sm'
                disabled={countBusy !== null}
                disabledReason={countBusy ?? undefined}
                onClick={() => counting.mutate()}
              >
                <Hash />
                Read how they count
              </Button>
            </div>
          }
        >
          <TextField
            label='Game name'
            value={name}
            blocked={blocked}
            onChange={setName}
          />
          <MindPicker
            label='Game of'
            value={gameKind}
            table={table(GAME_KINDS)}
            placeholder='Choose'
            blocked={blocked}
            onPick={setGameKind}
          />
          <MindPicker
            label='Won by'
            value={rule}
            table={table(GAME_RULES)}
            placeholder='Choose'
            blocked={blocked}
            onPick={setRule}
          />
          <MindPicker
            label='Known game'
            value={taken}
            table={Object.fromEntries(
              data.games.map((row) => [String(row.id), row.name])
            )}
            placeholder={data.games.length ? 'Choose' : 'No game is known yet'}
            blocked={blocked}
            onPick={setTaken}
          />
        </ForgeCard>
      </div>
    </div>
  )
}
