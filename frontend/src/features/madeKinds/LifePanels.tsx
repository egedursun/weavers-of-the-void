import { useState } from 'react'
import { Brain, CookingPot, Heart, Plus } from 'lucide-react'
import { mortalSexValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { Listed } from '@/features/collective/parts'
import { ForgeCard } from '@/features/cosmography/parts'
import { SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { CookingCard } from './DishPage'
import { type Dish, type ThingKinds, useLever } from './api'
import { wordTable } from './labels'
import { ListEditor } from './parts'

const SEXES = wordTable(mortalSexValues)
const DECLINE_MAX = 5

export function KitchenPanel({
  nodeId,
  data,
  dishes,
  blocked,
}: {
  nodeId: number
  data: ThingKinds
  dishes: Dish[]
  blocked: string | null
}) {
  const [dish, setDish] = useState('')
  const cook = useLever(
    'community_dish:set',
    (_: void) => ({
      community_id: nodeId,
      dish_id: Number(dish),
      popularity: 50,
    }),
    'The dish is cooked here now'
  )
  const busy = why(blocked, cook.isPending)
  const cooked = new Set(data.cooking.map((item) => item.dish_id))
  const table = Object.fromEntries(
    dishes
      .filter((item) => !cooked.has(item.id))
      .map((item) => [String(item.id), item.name])
  )
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Muted variant='caption'>
        Only a town or a people keeps a kitchen; its dishes are cooked from its
        stores and feed, calm or honour its folk.
      </Muted>
      <Listed
        title='Dishes cooked here'
        items={data.cooking}
        empty='No dish of a name is cooked here.'
        noun={['dish', 'dishes']}
        itemKey={(item) => item.dish_id}
      >
        {(item) => <CookingCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={CookingPot}
        tone='gold'
        title='Cook a dish here'
        note='Have its kitchens take up a dish known in its world.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={(busy ?? (dish ? null : 'Pick a dish')) !== null}
            disabledReason={busy ?? (dish ? undefined : 'Pick a dish')}
            onClick={() => cook.mutate()}
          >
            <Plus />
            Cook it here
          </Button>
        }
      >
        <MindPicker
          label='Dish'
          value={dish}
          table={table}
          blocked={
            Object.keys(table).length
              ? busy
              : 'Every dish of this world is cooked here, or none is known'
          }
          onPick={setDish}
        />
      </ForgeCard>
    </div>
  )
}

export function LeaningsPanel({
  nodeId,
  data,
  blocked,
}: {
  nodeId: number
  data: ThingKinds
  blocked: string | null
}) {
  const leaning = data.attraction
  const [strength, setStrength] = useState(String(leaning?.attraction ?? 0))
  const set = useLever(
    'mortal:attraction',
    (values: { drawn_to?: string[]; attraction?: number }) =>
      ({ mortal_id: nodeId, ...values, hold: true }) as never,
    'Whom the mortal is drawn to is set'
  )
  const release = useLever(
    'mortal:attraction',
    (_: void) => ({
      mortal_id: nodeId,
      drawn_to: (leaning?.drawn_to ?? []) as never,
      attraction: leaning?.attraction ?? 0,
      hold: false,
    }),
    'The engine may change it again'
  )
  const busy = why(blocked, set.isPending, release.isPending)
  if (!leaning) return null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Muted variant='caption'>
        Only a mortal has leanings of the heart and a mind that can fail with
        age.
      </Muted>
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @lg/tiles:grid-cols-2'>
          <KpiTile
            label='Strength of attraction'
            value={leaning.attraction}
            icon={Heart}
            tone='danger'
            meter={{
              value: leaning.attraction,
              max: SPAN,
              label: 'Attraction',
            }}
          />
          <KpiTile
            label='Decline of the mind'
            value={`${leaning.decline} of ${DECLINE_MAX}`}
            icon={Brain}
            tone={
              leaning.decline > 2
                ? 'danger'
                : leaning.decline > 0
                  ? 'warning'
                  : 'success'
            }
            meter={{
              value: leaning.decline,
              max: DECLINE_MAX,
              label: 'Decline',
            }}
          />
        </div>
      </div>
      <Muted variant='caption'>
        {leaning.drawn_to === null
          ? 'Not yet settled; the engine settles it from the rules of its world.'
          : leaning.drawn_to.length === 0
            ? 'Drawn to no one.'
            : `Drawn to ${leaning.drawn_to.map((item) => SEXES[item]?.toLowerCase() ?? item).join(', ')}.`}
        {leaning.decline > 0
          ? ' Its memory fails: it forgets what it learned, teaches less and may lose its office. Set the decline as a lasting condition of its body.'
          : ''}
      </Muted>
      <ListEditor
        field={{
          key: 'drawn_to',
          label: 'Drawn to',
          note: 'Whom this mortal is drawn to; it courts and bonds only with those it is drawn to.',
        }}
        options={SEXES}
        value={leaning.drawn_to ?? []}
        held={leaning.held.includes('drawn_to')}
        blocked={busy}
        onSet={(next) => set.mutate({ drawn_to: next })}
      />
      <div className='@container/form min-w-0'>
        <div className='grid min-w-0 grid-cols-1 items-end gap-2 @lg/form:grid-cols-3'>
          <NumberField
            label='Strength of attraction'
            value={strength}
            min={0}
            max={SPAN}
            blocked={busy}
            onChange={setStrength}
          />
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => set.mutate({ attraction: Number(strength) })}
          >
            Hold the strength
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={
              (busy ?? (leaning.held.length ? null : 'Nothing is held')) !==
              null
            }
            disabledReason={
              busy ?? (leaning.held.length ? undefined : 'Nothing is held')
            }
            onClick={() => release.mutate()}
          >
            Release to the engine
          </Button>
        </div>
      </div>
    </div>
  )
}
