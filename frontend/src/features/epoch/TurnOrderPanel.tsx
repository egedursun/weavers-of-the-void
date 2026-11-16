import { useState } from 'react'
import { ListOrdered, Pin, PinOff } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { cn } from '@/lib/utils'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  EntityLink,
  Paged,
  Portrait,
  Section,
} from '@/components/domain'
import { Label, Stat } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { type SonRecord, type WorldState } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { mediaUrl } from '@/features/pantheon/media'
import { orderedSons } from './turnOrder'

const FIRST_PLACE = 1

type TurnRankRowProps = {
  son: SonRecord
  cover: string | null
  position: number
  places: number
}

function TurnRankRow({ son, cover, position, places }: TurnRankRowProps) {
  const [place, setPlace] = useState(String(son.turn_rank ?? position))
  const { reason } = useGodGate()
  const rank = useGodAction({
    run: (value: number | null) =>
      unwrap(
        api.POST('/api/actions/son:turn_rank', {
          body: { son_id: son.id, rank: value },
        })
      ),
  })
  const parsed = Number(place)
  const invalid =
    !Number.isInteger(parsed) || parsed < FIRST_PLACE
      ? 'Give a place of 1 or more.'
      : null
  const pinned = typeof son.turn_rank === 'number'
  return (
    <li className='flex min-w-0 items-center gap-3 rounded-md border surface-sheen border-gild/60 bg-card p-2'>
      <span
        className={cn(
          'flex size-control-sm shrink-0 items-center justify-center rounded-full border surface-sheen border-gild/60 bg-card',
          pinned
            ? 'border-primary/40 bg-primary/12 text-primary'
            : 'border-border bg-muted text-muted-foreground'
        )}
      >
        <Stat value={position} />
      </span>
      <Portrait
        name={son.name}
        src={mediaUrl(cover)}
        size='sm'
        rarity={son.rarity}
      />
      <span className='flex min-w-0 flex-1 flex-col'>
        <EntityLink kind='son' id={String(son.id)} rarity={son.rarity}>
          {son.name}
        </EntityLink>
        <Label truncate>
          {pinned ? `Pinned · ${son.turn_rank}` : 'Initiative'}
        </Label>
      </span>
      <Input
        aria-label={`Place in the turn for ${son.name}`}
        type='number'
        size='sm'
        min={FIRST_PLACE}
        max={places}
        value={place}
        className='w-16'
        onChange={(event) => setPlace(event.target.value)}
      />
      {pinned ? (
        <ActionButton
          label='Release'
          icon={PinOff}
          size='sm'
          variant='ghost'
          blocked={reason()}
          pending={rank.isPending}
          onRun={() => rank.mutate(null)}
        />
      ) : (
        <ActionButton
          label='Pin'
          icon={Pin}
          size='sm'
          variant='outline'
          blocked={reason() ?? invalid}
          pending={rank.isPending}
          onRun={() => rank.mutate(parsed)}
        />
      )}
    </li>
  )
}

export function TurnOrderPanel({ state }: { state: WorldState }) {
  const sons = orderedSons(state)
  const covers = new Map(state.sons.map((item) => [item.son.id, item.cover]))
  return (
    <Section
      title="The gods' turn order"
      description='Initiative (agility, half their cunning and a doubled die) orders the sons. Pin a son to fix their place; the rest follow by initiative.'
      surface='card'
    >
      {sons.length === 0 ? (
        <EmptyState
          size='compact'
          icon={ListOrdered}
          title='No son to order'
          description='Summon a son and their place in the turn appears here.'
        />
      ) : (
        <ol className='flex min-w-0 flex-col gap-2'>
          <Paged items={sons} as='li'>
            {(son, index) => (
              <TurnRankRow
                key={`${son.id}:${son.turn_rank ?? 'free'}`}
                son={son}
                cover={covers.get(son.id) ?? null}
                position={index + 1}
                places={sons.length}
              />
            )}
          </Paged>
        </ol>
      )}
    </Section>
  )
}
