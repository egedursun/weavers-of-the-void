import { useState } from 'react'
import {
  ChefHat,
  CookingPot,
  GitBranch,
  Heart,
  ListOrdered,
  Package,
  Plus,
  Smile,
  Trash2,
  Utensils,
  Wheat,
} from 'lucide-react'
import { techniqueValues } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { KpiTile, StatBar } from '@/components/domain'
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
import { useKinds } from '@/features/kinds/api'
import { type Dish, useLever } from './api'
import {
  COURSE,
  DISH_FOODS,
  FOOD_ICON,
  METHOD,
  INGREDIENT_ROLE,
  MEAL,
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
type Step = Dish['steps'][number]

const TECHNIQUES = wordTable(techniqueValues)
const WORLDS = ['world'] as const
const GODS = ['son', 'creator', 'foreign_god'] as const
const YES_NO = { true: 'Yes', false: 'No' }
const KEEPS_MAX = 20
const DURATION_MAX = 1000
const NO_GOOD = 'none'
const FLAVOUR_KEYS = [
  'sweet',
  'sour',
  'saline',
  'bitter',
  'savoury',
  'pungent',
  'cooling',
  'numbing',
  'smoky',
  'fermented',
  'astringent',
  'rich',
] as const

function useGoodNames(worldId: number | null) {
  const goods = useKinds('good', worldId)
  return {
    [NO_GOOD]: 'No good named',
    ...Object.fromEntries(
      (goods.data ?? []).map((good) => [String(good.id), good.name])
    ),
  }
}

function useParentDishes(worldId: number | null, dishId: number) {
  const dishes = useKinds('dish', worldId)
  return {
    none: 'No dish before it',
    ...Object.fromEntries(
      (dishes.data ?? [])
        .filter((dish) => dish.id !== dishId)
        .map((dish) => [String(dish.id), dish.name])
    ),
  }
}

function IngredientRow({
  row,
  dishId,
  goods,
  blocked,
}: {
  row: Ingredient
  dishId: number
  goods: Record<string, string>
  blocked: string | null
}) {
  const [share, setShare] = useState(String(row.share))
  const [role, setRole] = useState<string>(row.role)
  const [good, setGood] = useState(
    row.good_kind_id === null ? NO_GOOD : String(row.good_kind_id)
  )
  const set = useLever(
    'dish_ingredient:set',
    (_: void) => ({
      dish_id: dishId,
      commodity: row.commodity,
      share: Number(share),
      role: role as Ingredient['role'],
      good_kind_id: good === NO_GOOD ? null : Number(good),
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
  const unchanged =
    share === String(row.share) &&
    role === row.role &&
    good === (row.good_kind_id === null ? NO_GOOD : String(row.good_kind_id))
  const problem =
    numberProblem(share, 1, SPAN) ??
    (unchanged ? settled(share, row.share) : null)
  return (
    <li className='flex min-w-0 flex-wrap items-end gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <Chip icon={FOOD_ICON[row.commodity] ?? Wheat}>
        {COMMODITY[row.commodity].label}
      </Chip>
      <Chip icon={INGREDIENT_ROLE[row.role].icon}>
        {INGREDIENT_ROLE[row.role].label}
      </Chip>
      {row.good_name && <Chip icon={Package}>{row.good_name}</Chip>}
      <NumberField
        label='Share (%)'
        value={share}
        min={1}
        max={SPAN}
        blocked={busy}
        onChange={setShare}
      />
      <MindPicker
        label='Role in the dish'
        value={role}
        table={namedTable(INGREDIENT_ROLE)}
        blocked={busy}
        onPick={setRole}
      />
      <MindPicker
        label='Good it is'
        value={good}
        table={goods}
        blocked={busy}
        onPick={setGood}
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

function StepRow({ row, blocked }: { row: Step; blocked: string | null }) {
  const action = useKindRow(
    'dish_step:edit',
    'dish_step:delete',
    { record_id: row.id },
    blocked
  )
  const method = METHOD[row.method]
  return (
    <Held
      icon={method.icon}
      tone={method.tone}
      title={`Step ${row.step}: ${method.label}`}
      caption={`Step ${row.step} · takes ${plural(row.duration, 'hour', 'hours')}`}
      removeLabel='Take the step out'
      editTitle='Set the step'
      note='The steps of a dish run in order; the first step is the method the dish is known by.'
      fields={[
        {
          key: 'method',
          label: 'How this step is done',
          kind: 'pick',
          table: namedTable(METHOD),
        },
        {
          key: 'duration',
          label: 'Hours it takes',
          kind: 'number',
          min: 0,
          max: DURATION_MAX,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function StepAdd({ row, blocked }: { row: Dish; blocked: string | null }) {
  const [method, setMethod] = useState('')
  const [duration, setDuration] = useState('1')
  const next =
    row.steps.reduce((most, item) => Math.max(most, item.step), 0) + 1
  const add = useLever(
    'dish_step:set',
    (_: void) => ({
      dish_id: row.id,
      step: next,
      method: method as Step['method'],
      duration: Number(duration),
    }),
    'The step is added'
  )
  const busy = why(blocked, add.isPending)
  const problem =
    busy ??
    (method ? null : 'Pick how the step is done') ??
    numberProblem(duration, 0, DURATION_MAX)
  return (
    <ForgeCard
      icon={ListOrdered}
      tone='gold'
      title={`Add step ${next}`}
      note='Add a further step to how the dish is made.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={problem !== null}
          disabledReason={problem ?? undefined}
          onClick={() => add.mutate()}
        >
          <Plus />
          Add the step
        </Button>
      }
    >
      <MindPicker
        label='How it is done'
        value={method}
        table={namedTable(METHOD)}
        blocked={busy}
        onPick={setMethod}
      />
      <NumberField
        label='Hours it takes'
        value={duration}
        min={0}
        max={DURATION_MAX}
        blocked={busy}
        onChange={setDuration}
      />
    </ForgeCard>
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
      caption={`Popularity ${row.popularity} · cooked ${plural(row.cooked, 'time', 'times')} · since epoch ${row.since_epoch}${row.short_epochs ? ` · short for ${plural(row.short_epochs, 'epoch', 'epochs')}` : ''}`}
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
        {
          key: 'short_epochs',
          label: 'Epochs gone short',
          kind: 'number',
          min: 0,
        },
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
  const slot = MEAL[row.category]
  const goods = useGoodNames(row.world_id)
  const parents = useParentDishes(row.world_id, row.id)
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
            <Chip icon={slot.icon}>{slot.label}</Chip>
            <Chip
              icon={CookingPot}
            >{`Cooked in ${plural(row.cooked_in.length, 'place', 'places')}`}</Chip>
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
          <KpiTile
            label='Skill to make'
            value={row.prep_skill}
            icon={ChefHat}
            tone='warning'
            meter={{ value: row.prep_skill, max: SPAN, label: 'Skill to make' }}
          />
        </div>
      </div>
      <section
        aria-label='Taste of the dish'
        className='@container min-w-0 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'
      >
        <div className='grid min-w-0 grid-cols-1 gap-3 @sm:grid-cols-2'>
          {row.flavours.map((item) => (
            <StatBar
              key={item.flavour}
              label={item.label}
              value={item.value}
              max={SPAN}
            />
          ))}
        </div>
      </section>
      <Facts
        items={[
          ['Made by', <Ref key='origin' node={row.origin} empty='no maker' />],
          [
            'Technique it needs',
            row.technique ? TECHNIQUES[row.technique] : 'none',
          ],
          [
            'Made from',
            row.derived_from_name ? (
              <Chip key='parent' icon={GitBranch}>
                {row.derived_from_name}
              </Chip>
            ) : (
              'a dish of its own'
            ),
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
              key: 'category',
              label: 'Meal it belongs to',
              kind: 'pick',
              table: namedTable(MEAL),
            },
            {
              key: 'prep_skill',
              label: 'Skill to make',
              kind: 'number',
              min: 0,
              max: SPAN,
            },
            ...FLAVOUR_KEYS.map((flavour) => ({
              key: flavour,
              label: `${flavour[0].toUpperCase()}${flavour.slice(1)} taste`,
              kind: 'number' as const,
              min: 0,
              max: SPAN,
            })),
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
            {
              key: 'derived_from_id',
              label: 'Made from the dish',
              kind: 'pick',
              table: parents,
            },
            {
              key: 'built_in',
              label: 'Known to every world',
              kind: 'pick',
              table: YES_NO,
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
        title='Steps'
        items={row.steps}
        empty='It has no steps yet.'
        noun={['step', 'steps']}
        itemKey={(item) => item.id}
      >
        {(item) => <StepRow row={item} blocked={blocked} />}
      </Listed>
      <StepAdd row={row} blocked={blocked} />
      <Listed
        title='Foods'
        items={row.ingredients}
        empty='It is made of nothing yet.'
        noun={['food', 'foods']}
        itemKey={(item) => item.commodity}
      >
        {(item) => (
          <IngredientRow
            row={item}
            dishId={row.id}
            goods={goods}
            blocked={blocked}
          />
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
