import { useState } from 'react'
import {
  CookingPot,
  Heart,
  Plus,
  Smile,
  Trash2,
  Utensils,
  Wheat,
} from 'lucide-react'
import { techniqueValues } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard } from '@/features/cosmography/parts'
import { SPAN } from '@/features/cycles/model'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { COMMODITY } from '@/features/entity/economy/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type Dish, useLever } from './api'
import {
  COURSE,
  DISH_FOODS,
  FOOD_ICON,
  METHOD,
  namedTable,
  wordTable,
} from './labels'
import {
  COMMUNITY_TYPES,
  OWNER_TYPES,
  numberProblem,
  settled,
  useKindRow,
  useKindStep,
} from './model'
import { KindHeader } from './parts'

type Ingredient = Dish['ingredients'][number]
type Cooking = Dish['cooked_in'][number]

const TECHNIQUES = wordTable(techniqueValues)
const WORLDS = ['world'] as const
const GODS = ['son', 'creator', 'foreign_god'] as const
const YES_NO = { true: 'Yes', false: 'No' }
const KEEPS_MAX = 20

function IngredientRow({
  row,
  dishId,
  blocked,
}: {
  row: Ingredient
  dishId: number
  blocked: string | null
}) {
  const [share, setShare] = useState(String(row.share))
  const set = useLever(
    'dish_ingredient:set',
    (_: void) => ({
      dish_id: dishId,
      commodity: row.commodity,
      share: Number(share),
    }),
    'The ingredient is set'
  )
  const remove = useKindStep(
    'dish_ingredient:delete',
    { dish_id: dishId, commodity: row.commodity },
    blocked,
    'The ingredient is left out'
  )
  const busy = why(remove.busy, set.isPending)
  const problem = numberProblem(share, 1, SPAN) ?? settled(share, row.share)
  return (
    <li className='flex min-w-0 flex-wrap items-end gap-2 rounded-lg border bg-muted/30 p-2'>
      <Chip icon={FOOD_ICON[row.commodity] ?? Wheat}>
        {COMMODITY[row.commodity].label}
      </Chip>
      <NumberField
        label='Share (%)'
        value={share}
        min={1}
        max={SPAN}
        blocked={busy}
        onChange={setShare}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={(busy ?? problem) !== null}
        disabledReason={busy ?? problem ?? undefined}
        onClick={() => set.mutate()}
      >
        Set
      </Button>
      <Button
        size='sm'
        variant='ghost'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={remove.run}
      >
        <Trash2 />
        Leave it out
      </Button>
    </li>
  )
}

export function CookingCard({
  row,
  blocked,
}: {
  row: Cooking
  blocked: string | null
}) {
  const action = useKindRow(
    'community_dish:edit',
    'community_dish:delete',
    { community_id: row.community.id, dish_id: row.dish_id },
    blocked
  )
  return (
    <Held
      icon={CookingPot}
      tone='gold'
      title={`${row.dish_name} in ${row.community.name}`}
      caption={`Popularity ${row.popularity} · cooked ${row.cooked} times · since epoch ${row.since_epoch}`}
      removeLabel='Stop cooking it'
      editTitle='Set how it is cooked there'
      note='A popular dish is cooked from the town’s stores each epoch; it calms, nourishes or gives prestige by its kind, gains favour while cooked and loses it when the stores run short.'
      fields={[
        {
          key: 'popularity',
          label: 'Popularity',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        { key: 'cooked', label: 'Times cooked', kind: 'number', min: 0 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function Additions({ row, blocked }: { row: Dish; blocked: string | null }) {
  const [food, setFood] = useState('')
  const [town, setTown] = useState<number | null>(null)
  const addFood = useLever(
    'dish_ingredient:set',
    (_: void) => ({ dish_id: row.id, commodity: food as never, share: 20 }),
    'The ingredient is added'
  )
  const cook = useLever(
    'community_dish:set',
    (_: void) => ({ community_id: town ?? 0, dish_id: row.id, popularity: 50 }),
    'The community cooks it now'
  )
  const busy = why(blocked, addFood.isPending, cook.isPending)
  const have = new Set(row.ingredients.map((item) => item.commodity as string))
  const foods = Object.fromEntries(
    DISH_FOODS.filter((item) => !have.has(item)).map((item) => [
      item,
      COMMODITY[item].label,
    ])
  )
  return (
    <ForgeCard
      icon={Utensils}
      tone='gold'
      title='Add a food or a kitchen'
      note='Add a food it is made of, or have a town or people cook it.'
      columns={2}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={(busy ?? (food ? null : 'Pick a food')) !== null}
            disabledReason={busy ?? (food ? undefined : 'Pick a food')}
            onClick={() => addFood.mutate()}
          >
            <Plus />
            Add the food
          </Button>
          <Button
            size='sm'
            disabled={(busy ?? (town ? null : 'Pick a community')) !== null}
            disabledReason={busy ?? (town ? undefined : 'Pick a community')}
            onClick={() => cook.mutate()}
          >
            <Plus />
            Cook it there
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Food'
        value={food}
        table={foods}
        blocked={
          Object.keys(foods).length ? busy : 'Every food is in it already'
        }
        onPick={setFood}
      />
      <NodePicker
        label='Community'
        value={town}
        onChange={setTown}
        blocked={busy}
        types={COMMUNITY_TYPES}
      />
    </ForgeCard>
  )
}

export function DishPage({
  row,
  blocked = null,
}: {
  row: Dish
  blocked?: string | null
}) {
  const action = useKindRow(
    'dish:edit',
    'dish:delete',
    { record_id: row.id },
    blocked
  )
  const course = COURSE[row.course]
  const method = METHOD[row.method]
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <KindHeader
        icon={course.icon}
        tone={row.retired ? 'muted' : course.tone}
        overline='Dish'
        title={row.name}
        caption={`${course.label}, ${method.label.toLowerCase()}, of ${row.origin?.name ?? 'no maker'} · first cooked in epoch ${row.created_epoch}${row.retired ? ' · forgotten' : ''}`}
        chips={
          <>
            <Chip icon={method.icon}>{method.label}</Chip>
            <Chip icon={course.icon}>{course.label}</Chip>
            <Chip
              icon={CookingPot}
            >{`Cooked in ${row.cooked_in.length} places`}</Chip>
          </>
        }
      />
      {row.description && <Muted variant='caption'>{row.description}</Muted>}
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @2xl/tiles:grid-cols-4'>
          <KpiTile
            label='Nourishment'
            value={row.nourishment}
            icon={Heart}
            tone='success'
            meter={{ value: row.nourishment, max: SPAN, label: 'Nourishment' }}
          />
          <KpiTile
            label='Delight'
            value={row.delight}
            icon={Smile}
            tone='gold'
            meter={{ value: row.delight, max: SPAN, label: 'Delight' }}
          />
          <KpiTile
            label='Prestige'
            value={row.prestige}
            icon={CookingPot}
            tone='verdigris'
            meter={{ value: row.prestige, max: SPAN, label: 'Prestige' }}
          />
          <KpiTile
            label='Keeps (epochs)'
            value={row.keeps}
            icon={Wheat}
            tone='info'
          />
        </div>
      </div>
      <Facts
        items={[
          ['Made by', <Ref key='origin' node={row.origin} empty='no maker' />],
          [
            'Technique it needs',
            row.technique ? TECHNIQUES[row.technique] : 'none',
          ],
          [
            'Foods',
            row.ingredients.length
              ? row.ingredients
                  .map((item) => COMMODITY[item.commodity].label)
                  .join(', ')
              : 'none',
          ],
        ]}
      />
      <ul className='flex min-w-0 flex-col gap-2'>
        <Held
          icon={course.icon}
          tone={course.tone}
          title='The whole dish'
          caption='Every value of the dish, held as you set it'
          removeLabel='Forget the dish'
          editTitle='Set the dish'
          note='How it is made sets how long it keeps; its course sets what it does for those who eat it.'
          fields={[
            { key: 'name', label: 'Name of the dish', kind: 'text' },
            {
              key: 'description',
              label: 'What sets it apart',
              kind: 'text',
              long: true,
            },
            {
              key: 'world_id',
              label: 'World',
              kind: 'node',
              types: [],
              kinds: WORLDS,
            },
            {
              key: 'origin_node_id',
              label: 'Made by',
              kind: 'node',
              types: OWNER_TYPES,
              kinds: GODS,
            },
            {
              key: 'method',
              label: 'How it is made',
              kind: 'pick',
              table: namedTable(METHOD),
            },
            {
              key: 'course',
              label: 'When it is eaten',
              kind: 'pick',
              table: namedTable(COURSE),
            },
            {
              key: 'nourishment',
              label: 'Nourishment',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'delight',
              label: 'Delight',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'keeps',
              label: 'Keeps (epochs)',
              kind: 'number',
              min: 0,
              max: KEEPS_MAX,
            },
            {
              key: 'prestige',
              label: 'Prestige',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            {
              key: 'technique',
              label: 'Technique it needs',
              kind: 'pick',
              table: TECHNIQUES,
            },
            { key: 'retired', label: 'Forgotten', kind: 'pick', table: YES_NO },
          ]}
          locked={row.locked}
          blocked={action.busy}
          onEdit={action.onEdit}
          onRemove={action.onRemove}
        />
      </ul>
      <Listed
        title='Foods'
        items={row.ingredients}
        empty='It is made of nothing yet.'
        noun={['food', 'foods']}
        itemKey={(item) => item.commodity}
      >
        {(item) => (
          <IngredientRow row={item} dishId={row.id} blocked={blocked} />
        )}
      </Listed>
      <Listed
        title='Cooked in'
        items={row.cooked_in}
        empty='No community cooks it.'
        noun={['kitchen', 'kitchens']}
        itemKey={(item) => item.community.id}
      >
        {(item) => <CookingCard row={item} blocked={blocked} />}
      </Listed>
      <Additions row={row} blocked={blocked} />
    </div>
  )
}
