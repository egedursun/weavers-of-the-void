import { useState } from 'react'
import { Dices, Plus, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LoadingBlock } from '@/components/domain'
import { Muted } from '@/components/typography'
import { Listed } from '@/features/collective/parts'
import { ForgeCard } from '@/features/cosmography/parts'
import { TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { KindCard } from '@/features/kinds/KindCard'
import {
  type KindConceptInfo,
  type KindRecord,
  useKindConcepts,
  useKinds,
  useWaysOfLife,
} from '@/features/kinds/api'
import { useMadeAction } from '@/features/minds/api'
import { Bars } from '@/features/sacred/parts'
import { SPAN } from './model'

const TAKEN_UP_STRENGTH = 50

function GameForge({
  people,
  info,
  known,
  playing,
  blocked,
}: {
  people: number | null
  info: KindConceptInfo | undefined
  known: readonly KindRecord[]
  playing: ReadonlySet<number>
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState('board')
  const [taken, setTaken] = useState('')
  const open = known.filter((row) => !row.retired && !playing.has(row.id))
  const making = useMadeAction(
    'authored_kind:create',
    (_: void) => ({
      concept: 'game' as const,
      name: name.trim(),
      category,
      origin_node_id: people,
      world_id: null,
      values: {},
    }),
    'The game is played'
  )
  const following = useMadeAction(
    'authored_kind:spread',
    (_: void) => ({
      concept: 'game' as const,
      kind_id: Number(taken || '0'),
      holder_node_id: people ?? 0,
      stance: 'uses' as const,
      strength: TAKEN_UP_STRENGTH,
    }),
    'The people take up the game'
  )
  const noPeople = people === null ? 'Only a people plays games' : null
  const makeBusy = why(
    blocked ??
      noPeople ??
      (!info ? 'Games are still being read' : null) ??
      (!name.trim() ? 'Name the game' : null),
    making.isPending
  )
  const followBusy = why(
    blocked ??
      noPeople ??
      (!open.length
        ? 'No other game is known yet'
        : !taken
          ? 'Choose a known game'
          : null),
    following.isPending
  )
  return (
    <ForgeCard
      icon={Dices}
      tone='warning'
      title='Games and sports'
      note='Make a game for its people, or let them take up a game another people plays. Edit every property of a game on its card.'
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
            disabled={followBusy !== null}
            disabledReason={followBusy ?? undefined}
            onClick={() => following.mutate()}
          >
            <Users />
            Take it up
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
        label='Sort of game'
        value={category}
        table={Object.fromEntries(
          (info?.categories ?? []).map((item) => [item.key, item.label])
        )}
        placeholder='Choose'
        blocked={blocked}
        onPick={setCategory}
      />
      <MindPicker
        label='Known game'
        value={taken}
        table={Object.fromEntries(
          open.map((row) => [String(row.id), row.name])
        )}
        placeholder={open.length ? 'Choose' : 'No other game is known yet'}
        blocked={blocked}
        onPick={setTaken}
      />
    </ForgeCard>
  )
}

function PeopleGames({
  people,
  info,
  known,
  blocked,
}: {
  people: number
  info: KindConceptInfo | undefined
  known: readonly KindRecord[]
  blocked: string | null
}) {
  const ways = useWaysOfLife(people)
  const played = (ways.data?.holdings ?? []).filter(
    (row) => row.concept === 'game'
  )
  const rows = played
    .map((holding) => ({
      holding,
      game: known.find((row) => row.id === holding.kind_id),
    }))
    .filter(
      (item): item is { holding: typeof item.holding; game: KindRecord } =>
        item.game !== undefined
    )
  if (ways.isPending) return <LoadingBlock label='Reading its games' />
  return (
    <>
      <Bars
        chart='chart-games'
        title='Games and how strongly they are played'
        legend={[{ text: 'Strength', variant: 'success' }]}
        rows={rows.map(({ holding, game }) => ({
          key: String(game.id),
          caption: `${game.name}: ${holding.category_label.toLowerCase()}, strength ${holding.strength}`,
          segments: [
            { value: Math.min(SPAN, holding.strength), fill: 'fill-success' },
          ],
        }))}
        max={SPAN}
        noun={['game', 'games']}
        empty='Its people play no games yet.'
      />
      <Listed
        title='Games of its people'
        items={rows}
        empty='Its people play no games yet.'
        noun={['game', 'games']}
        itemKey={(item) => item.game.id}
      >
        {(item) =>
          info ? (
            <KindCard
              info={info}
              row={item.game}
              siblings={known}
              blocked={blocked}
            />
          ) : null
        }
      </Listed>
      <GameForge
        people={people}
        info={info}
        known={known}
        playing={new Set(rows.map((item) => item.game.id))}
        blocked={blocked}
      />
    </>
  )
}

export function GamesPanel({
  people,
  blocked,
}: {
  people: number | null
  blocked: string | null
}) {
  const concepts = useKindConcepts()
  const games = useKinds('game', null)
  const info = concepts.data?.find((item) => item.concept === 'game')
  const known = games.data ?? []
  return (
    <div data-surface='GamesPanel' className='flex min-w-0 flex-col gap-4'>
      {people === null ? (
        <>
          <Muted variant='caption'>
            It belongs to no people, so it plays no games of its own.
          </Muted>
          <GameForge
            people={null}
            info={info}
            known={known}
            playing={new Set()}
            blocked={blocked}
          />
        </>
      ) : (
        <PeopleGames
          people={people}
          info={info}
          known={known}
          blocked={blocked}
        />
      )}
    </div>
  )
}
