import { useState } from 'react'
import {
  Armchair,
  Eye,
  Gem,
  HeartPulse,
  Moon,
  PackageOpen,
  PackagePlus,
  Radar,
  Scale,
  ScrollText,
  Skull,
  Swords,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { KpiTile, Medallion, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { COMMODITY } from '../economy/labels'
import { busyOf } from '../lore/model'
import { type BeastCard, useWildAction } from './api'
import { named } from './labels'
import { Card, Group, Name } from './parts'

type Blocked = { id: number; card: BeastCard; blocked: string | null }

const HOLDERS = [
  'mortal',
  'settlement',
  'people',
  'cult',
  'army',
  'place',
] as const
const SLAYERS = ['mortal', 'army', 'settlement', 'people'] as const

export function Abilities({ card }: { card: BeastCard }) {
  return (
    <Card
      title='What its abilities do'
      icon={Radar}
      tone='info'
      hint='Endurance, perception, willpower and size as the world reads them'
      wide
    >
      <div className='grid min-w-0 grid-cols-2 gap-2 @md/card:grid-cols-3'>
        <KpiTile
          label='Raids reach'
          value={`${card.reach} ${card.reach === 1 ? 'land' : 'lands'}`}
          icon={Radar}
          tone='warning'
          hint='Endurance carries it further from its lair'
        />
        <KpiTile
          label='Harm it takes'
          value={`${card.harm_taken_pct}%`}
          icon={HeartPulse}
          tone={card.harm_taken_pct < 60 ? 'success' : 'warning'}
          hint='Endurance turns aside a hero’s blows'
          meter={{
            value: card.harm_taken_pct,
            max: 100,
            label: `${card.harm_taken_pct}%`,
          }}
        />
        <KpiTile
          label='Wakes when disturbed'
          value={`${card.wake_pct}%`}
          icon={Eye}
          tone='info'
          hint='Perception: mining, war or theft near the lair'
          meter={{ value: card.wake_pct, max: 100, label: `${card.wake_pct}%` }}
        />
        <KpiTile
          label='Can be tamed'
          value={`${card.tame_pct}%`}
          icon={Scale}
          tone={card.tame_pct > 50 ? 'success' : 'danger'}
          hint='Willpower resists a would-be master each epoch'
          meter={{ value: card.tame_pct, max: 100, label: `${card.tame_pct}%` }}
        />
        <KpiTile
          label='Rests after a hunt'
          value={`${card.rest_pct}%`}
          icon={Moon}
          tone='verdigris'
          hint='Willpower keeps it hunting'
          meter={{ value: card.rest_pct, max: 100, label: `${card.rest_pct}%` }}
        />
        <KpiTile
          label='Mount'
          value={card.rideable ? 'Can be ridden' : 'Too small to ride'}
          icon={Armchair}
          tone={card.rideable ? 'gold' : 'muted'}
          hint='A tamed great beast lends its rider an edge in battle and swifter roads'
        />
      </div>
    </Card>
  )
}

export function Treasures({ card }: { card: BeastCard }) {
  return (
    <Card
      title='Treasures and tribute'
      icon={Gem}
      tone='gold'
      hint={`${card.treasures.length} treasured ${card.treasures.length === 1 ? 'item' : 'items'} · ${card.tributes.length} ${card.tributes.length === 1 ? 'town pays' : 'towns pay'} tribute`}
      wide
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/card:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Items it owns</Label>
          {card.treasures.length === 0 ? (
            <Muted>No treasured item lies in its hoard.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-col gap-1.5'>
              <Paged items={card.treasures} as='li'>
                {(item) => (
                  <li
                    key={item.id}
                    className='flex min-w-0 items-center gap-2 rounded-lg border bg-muted/30 p-2'
                  >
                    <Medallion icon={Gem} tone='gold' size='sm' />
                    <Name item={item} />
                  </li>
                )}
              </Paged>
            </ul>
          )}
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Tribute treaties</Label>
          {card.tributes.length === 0 ? (
            <Muted>No town has sworn it tribute.</Muted>
          ) : (
            <ul className='flex min-w-0 flex-col gap-1.5'>
              <Paged items={card.tributes} as='li'>
                {(row) => {
                  const goods = named(
                    COMMODITY as Record<string, (typeof COMMODITY)['grain']>,
                    row.commodity
                  )
                  return (
                    <li
                      key={row.treaty?.id}
                      className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'
                    >
                      <Medallion icon={ScrollText} tone='warning' size='sm' />
                      <div className='flex min-w-0 flex-1 flex-col gap-1'>
                        <Name item={row.town} />
                        <div className='flex flex-wrap gap-1'>
                          <Badge size='sm' variant='default'>
                            <goods.icon />
                            {`${row.units} ${goods.label.toLowerCase()} each epoch`}
                          </Badge>
                          <Badge size='sm' variant='secondary'>
                            {row.last_kept_epoch !== null
                              ? `Paid in epoch ${row.last_kept_epoch}`
                              : 'Not yet paid'}
                          </Badge>
                        </div>
                      </div>
                      <Name item={row.treaty} />
                    </li>
                  )
                }}
              </Paged>
            </ul>
          )}
        </div>
      </div>
    </Card>
  )
}

export function TreasureControls({ id, card, blocked }: Blocked) {
  const [item, setItem] = useState<number | null>(null)
  const [taken, setTaken] = useState('')
  const [receiver, setReceiver] = useState<number | null>(null)
  const move = useWildAction(
    'beast:treasure',
    ({
      item: thing,
      into,
      to,
    }: {
      item: number
      into: boolean
      to?: number | null
    }) => ({
      beast_id: id,
      item_id: thing,
      into_hoard: into,
      receiver_id: to ?? null,
    }),
    () => {
      setItem(null)
      setTaken('')
    }
  )
  const busy = busyOf(blocked, move.isPending)
  return (
    <Group title='Treasured items' icon={Gem}>
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label>Lay an item in its hoard</Label>
          <EntityPicker
            types={['item']}
            value={item}
            onChange={setItem}
            placeholder='Choose an item…'
          />
          <Button
            size='sm'
            variant='outline'
            className='self-start'
            disabled={busy !== null || item === null}
            disabledReason={
              busy ?? (item === null ? 'Choose an item' : undefined)
            }
            onClick={() => item !== null && move.mutate({ item, into: true })}
          >
            <PackagePlus />
            Lay it in the hoard
          </Button>
        </div>
        <div className='flex min-w-0 flex-col gap-2'>
          <Label>Take an item out</Label>
          {card.treasures.length === 0 ? (
            <Muted>Its hoard holds no item.</Muted>
          ) : (
            <div className='flex min-w-0 flex-wrap gap-1.5'>
              <Paged items={card.treasures}>
                {(thing) => (
                  <Button
                    key={thing.id}
                    size='sm'
                    variant={taken === String(thing.id) ? 'default' : 'outline'}
                    onClick={() => setTaken(String(thing.id))}
                  >
                    <Gem />
                    {thing.name}
                  </Button>
                )}
              </Paged>
            </div>
          )}
          <EntityPicker
            types={HOLDERS}
            value={receiver}
            onChange={setReceiver}
            placeholder='Who takes it…'
          />
          <Button
            size='sm'
            variant='outline'
            className='self-start'
            disabled={busy !== null || taken === '' || receiver === null}
            disabledReason={
              busy ??
              (taken === ''
                ? 'Choose an item from the hoard'
                : receiver === null
                  ? 'Choose who takes it'
                  : undefined)
            }
            onClick={() =>
              move.mutate({ item: Number(taken), into: false, to: receiver })
            }
          >
            <PackageOpen />
            Give it away
          </Button>
        </div>
      </div>
    </Group>
  )
}

export function SlayControl({
  id,
  blocked,
}: {
  id: number
  blocked: string | null
}) {
  const [slayer, setSlayer] = useState<number | null>(null)
  const slay = useWildAction('beast:slay', (_: void) => ({
    beast_id: id,
    slayer_id: slayer,
  }))
  const busy = busyOf(blocked, slay.isPending)
  return (
    <Group title='Its death' icon={Skull}>
      <Muted variant='caption'>
        A slain beast leaves its corpse to its slayer as trophies, its hoard to
        their market and its land to recover. A named slayer takes its name as a
        title.
      </Muted>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='flex min-w-0 flex-1 basis-60 flex-col gap-1'>
          <Label>Slain by (optional)</Label>
          <EntityPicker
            types={SLAYERS}
            value={slayer}
            onChange={setSlayer}
            placeholder='Let no one claim it…'
          />
        </div>
        <Button
          size='sm'
          variant='destructive'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => slay.mutate()}
        >
          <Swords />
          Slay the beast
        </Button>
      </div>
      <Text as='span' variant='caption'>
        The ledger can undo it.
      </Text>
    </Group>
  )
}
