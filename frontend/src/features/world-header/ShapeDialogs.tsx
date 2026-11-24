import { type ReactNode, useId, useState } from 'react'
import {
  Church,
  Crown,
  Dices,
  Ghost,
  Landmark,
  type LucideIcon,
  MapPin,
  Moon,
  Mountain,
  RotateCcw,
  Scale,
  ScrollText,
  Skull,
  SlidersHorizontal,
  Sparkles,
  UserPlus,
} from 'lucide-react'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  type components,
  domainValues,
  mortalRoleValues,
  naturalLawValues,
  rarityValues,
  sexKindValues,
} from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { RARITY_LABEL } from '@/constants/rarity'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  FieldTile,
  FormRow,
  Medallion,
  RangeField,
  ShapeFields,
  useShape,
} from '@/components/domain'
import { useGlobalWorld } from '@/components/layout/worldFilter'
import { Muted, Text } from '@/components/typography'
import { NodePicker as GodPicker } from '@/features/dominion/parts'
import { valueTable } from '@/features/entity/affairs/labels'
import { MindPicker, NodePicker } from '@/features/entity/mind/parts'
import { useWorldState } from '@/features/pantheon/api'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  ABILITIES,
  LAND,
  type Measure,
  PASSIONS,
  POWER,
  RECORD_MEASURES,
  SETTLERS,
  YEARS,
  bandOf,
  rolled,
  startsOf,
} from './shapeModel'

const COMMUNITIES = ['settlement', 'people']
const PEOPLES = ['people']
const REGIONS = ['region']
const PLACES = ['region', 'place', 'settlement']
const GODS = ['creator', 'son', 'foreign_god'] as const
const ANY = 'fate'
const WORKING = 'Working…'
const LAWS = naturalLawValues.filter((law) => law !== 'none')

const NATURE = [
  'appearance',
  'temperament',
  'obsession',
  'fear',
  'speech_style',
  'secret',
] as const
const NATURE_LABEL: Record<(typeof NATURE)[number], string> = {
  appearance: 'Appearance',
  temperament: 'Temperament',
  obsession: 'Obsession',
  fear: 'Fear',
  speech_style: 'Way of speaking',
  secret: 'Secret',
}

type SummonBody = components['schemas']['PostSonsSummonBody']
type Values = Record<string, number>

function useMeasures(measures: Measure[]) {
  const [values, setValues] = useState<Values>(() => startsOf(measures))
  return {
    values,
    set: (key: string, value: number) =>
      setValues((current) => ({ ...current, [key]: value })),
    roll: () => setValues(rolled(measures)),
    even: () => setValues(startsOf(measures)),
  }
}

function Step({
  number,
  title,
  hint,
  icon,
  tools,
  children,
}: {
  number: number
  title: string
  hint: string
  icon: LucideIcon
  tools?: ReactNode
  children: ReactNode
}) {
  return (
    <section
      aria-label={title}
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-sheen border-gild/50 bg-card p-4'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <Medallion icon={icon} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold'>{`${number}. ${title}`}</Text>
          <Muted variant='caption'>{hint}</Muted>
        </div>
        {tools}
      </div>
      {children}
    </section>
  )
}

function MeasureTools({
  onRoll,
  onEven,
  blocked,
}: {
  onRoll: () => void
  onEven: () => void
  blocked: string | null
}) {
  return (
    <div className='flex shrink-0 gap-2'>
      <Button
        size='sm'
        variant='outline'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={onRoll}
      >
        <Dices />
        Roll
      </Button>
      <Button
        size='sm'
        variant='ghost'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={onEven}
      >
        <RotateCcw />
        Even out
      </Button>
    </div>
  )
}

function MeasureGrid({
  measures,
  values,
  onChange,
  blocked,
}: {
  measures: Measure[]
  values: Values
  onChange: (key: string, value: number) => void
  blocked: string | null
}) {
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
      {measures.map((measure) => (
        <MeasureField
          key={measure.key}
          measure={measure}
          value={values[measure.key] ?? measure.start}
          onChange={(value) => onChange(measure.key, value)}
          blocked={blocked}
        />
      ))}
    </div>
  )
}

function MeasureField({
  measure,
  value,
  onChange,
  blocked,
}: {
  measure: Measure
  value: number
  onChange: (value: number) => void
  blocked: string | null
}) {
  return (
    <RangeField
      label={measure.label}
      icon={measure.icon}
      value={value}
      min={measure.min}
      max={measure.max}
      level={bandOf(measure, value)}
      lowLabel={measure.low}
      highLabel={measure.high}
      onChange={onChange}
      disabledReason={blocked}
    />
  )
}

function ShapeDialog({
  run: send,
  icon: Icon,
  trigger,
  title,
  description,
  missing,
  summary,
  gate = null,
  onDone,
  children,
}: {
  run: () => Promise<unknown>
  icon: LucideIcon
  trigger: string
  title: string
  description: string
  missing: string | null
  summary: string
  gate?: string | null
  onDone: () => void
  children: (blocked: string | null) => ReactNode
}) {
  const [open, setOpen] = useState(false)
  const { reason } = useGodGate()
  const run = useGodAction({
    run: send,
    onDone: () => {
      setOpen(false)
      onDone()
    },
  })
  const blocked = reason() ?? (run.isPending ? WORKING : null)
  const held = gate ?? blocked
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant='outline' size='sm'>
          <Icon />
          {trigger}
        </Button>
      </DialogTrigger>
      <DialogContent className='flex max-h-dvh flex-col gap-0 p-0 sm:max-w-4xl'>
        <DialogHeader className='border-b border-gild/40 p-5'>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={Icon} tone='gold' />
            <div className='flex min-w-0 flex-col gap-1'>
              <DialogTitle>{title}</DialogTitle>
              <DialogDescription>{description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <div className='flex min-h-0 min-w-0 flex-1 flex-col gap-3 overflow-y-auto p-5'>
          {children(blocked)}
        </div>
        <DialogFooter className='flex-col items-stretch gap-2 border-t border-gild/40 p-4 sm:flex-row sm:items-center'>
          <Muted variant='caption' className='min-w-0 flex-1'>
            {gate ?? missing ?? summary}
          </Muted>
          <Button
            disabled={held !== null || missing !== null}
            disabledReason={held ?? missing ?? undefined}
            onClick={() => run.mutate(undefined)}
          >
            <Icon />
            {trigger}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function useWorldChoice(required: boolean) {
  const state = useWorldState()
  const chosen = useGlobalWorld()
  const worlds = state.data?.worlds ?? []
  const [picked, setWorld] = useState<string | null>(null)
  const first = worlds[0]?.id
  const fallback = required ? (chosen ?? first) : undefined
  const world =
    picked ??
    (fallback === undefined || fallback === null ? ANY : String(fallback))
  const table = Object.fromEntries(
    worlds.map((item) => [String(item.id), item.name])
  )
  return {
    world,
    setWorld,
    table: required ? table : { [ANY]: 'Let Fate choose', ...table },
    name: worlds.find((item) => String(item.id) === world)?.name ?? null,
  }
}

function WorldPicker({
  choice,
  blocked,
}: {
  choice: ReturnType<typeof useWorldChoice>
  blocked: string | null
}) {
  return (
    <MindPicker
      label='World'
      value={choice.world}
      table={choice.table}
      blocked={blocked}
      placeholder='Choose a world'
      onPick={choice.setWorld}
    />
  )
}

function WaterTile({
  water,
  onChange,
  blocked,
}: {
  water: boolean
  onChange: (value: boolean) => void
  blocked: string | null
}) {
  const id = useId()
  return (
    <FieldTile id={id} label='A water region'>
      <Switch
        id={id}
        checked={water}
        disabled={blocked !== null}
        onCheckedChange={onChange}
      />
    </FieldTile>
  )
}

function named(name: string, fallback: string): string {
  return name.trim() || fallback
}

export function ShapeMortalDialog() {
  const naming = useShape()
  const [community, setCommunity] = useState<number | null>(null)
  const [role, setRole] = useState<string>('commoner')
  const [sex, setSex] = useState(ANY)
  const power = useMeasures([POWER])
  const abilities = useMeasures(ABILITIES)
  const years = useMeasures(YEARS)
  const roles = valueTable(mortalRoleValues)
  return (
    <ShapeDialog
      icon={UserPlus}
      trigger='Shape a mortal'
      title='Shape a mortal'
      description='Set who they are, where they are born and every gift they carry; each value starts even and can be rolled.'
      missing={
        community === null ? 'Choose a people or town to be born among' : null
      }
      summary={`${named(naming.shape.name, 'A newborn the world will name')}, ${roles[role].toLowerCase()}, ${years.values.age} years of ${years.values.lifespan}`}
      run={() =>
        postAction('mortal:shape', {
          community_id: community ?? 0,
          role: role as ActionBody<'mortal:shape'>['role'],
          sex: sex === ANY ? null : (sex as ActionBody<'mortal:shape'>['sex']),
          power: power.values.power,
          ...abilities.values,
          ...years.values,
          ...naming.body,
        })
      }
      onDone={() => {
        naming.reset()
        abilities.even()
        years.even()
      }}
    >
      {(blocked) => (
        <>
          <Step
            number={1}
            title='Who they are'
            hint='A name, a title and a story; leave any of them to the world.'
            icon={ScrollText}
          >
            <ShapeFields
              shape={naming.shape}
              onChange={naming.setShape}
              titled
              blocked={blocked}
            />
          </Step>
          <Step
            number={2}
            title='Where and what they are'
            hint='The people or town they are born among, their place and how much they matter.'
            icon={MapPin}
          >
            <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
              <NodePicker
                label='Born among'
                types={COMMUNITIES}
                value={community}
                onChange={setCommunity}
                blocked={blocked}
              />
              <MindPicker
                label='Role'
                value={role}
                table={roles}
                blocked={blocked}
                onPick={setRole}
              />
              <MindPicker
                label='Sex'
                value={sex}
                table={{
                  [ANY]: 'Let the world choose',
                  ...valueTable(sexKindValues),
                }}
                blocked={blocked}
                onPick={setSex}
              />
            </div>
            <MeasureField
              measure={POWER}
              value={power.values.power}
              onChange={(value) => power.set('power', value)}
              blocked={blocked}
            />
          </Step>
          <Step
            number={3}
            title='Gifts'
            hint='Ten gifts from 0 to 100; roll them for a life the world might have dealt.'
            icon={SlidersHorizontal}
            tools={
              <MeasureTools
                onRoll={abilities.roll}
                onEven={abilities.even}
                blocked={blocked}
              />
            }
          >
            <MeasureGrid
              measures={ABILITIES}
              values={abilities.values}
              onChange={abilities.set}
              blocked={blocked}
            />
          </Step>
          <Step
            number={4}
            title='Years'
            hint='How old they are when they enter the world and how long they may live.'
            icon={Sparkles}
          >
            <MeasureGrid
              measures={YEARS}
              values={years.values}
              onChange={years.set}
              blocked={blocked}
            />
          </Step>
        </>
      )}
    </ShapeDialog>
  )
}

export function ShapeSonDialog() {
  const naming = useShape()
  const rule = useRuleLookup()
  const cost = rule('costs.summon_son')
  const { reason } = useGodGate()
  const choice = useWorldChoice(false)
  const [rarity, setRarity] = useState(ANY)
  const [first, setFirst] = useState(ANY)
  const [second, setSecond] = useState(ANY)
  const [nature, setNature] = useState<Record<string, string>>({})
  const [choosePassions, setChoosePassions] = useState(true)
  const passions = useMeasures(PASSIONS)
  const [wish, setWish] = useState('')
  const domains: Record<string, string> = {
    [ANY]: 'Let the summoning choose',
    ...valueTable(domainValues),
  }
  return (
    <ShapeDialog
      gate={reason({ cost, world: true, llm: true })}
      icon={Crown}
      trigger='Summon a son as you shape them'
      title='Summon a son'
      description='Set any of their name, domains, nature and passions; the summoning writes the rest to fit what you chose.'
      missing={null}
      summary={`${named(naming.shape.name, 'A son the summoning will name')}${rarity === ANY ? '' : `, ${RARITY_LABEL[rarity as keyof typeof RARITY_LABEL].toLowerCase()}`}${first === ANY ? '' : `, ${domains[first].toLowerCase()}`}`}
      run={() => {
        const body: SummonBody = {
          world_id: choice.world === ANY ? null : Number(choice.world),
          rarity: rarity === ANY ? null : (rarity as SummonBody['rarity']),
          domain_1: first === ANY ? null : (first as SummonBody['domain_1']),
          domain_2: second === ANY ? null : (second as SummonBody['domain_2']),
          name: naming.body.name,
          title: naming.body.title,
          appearance: nature.appearance?.trim() || null,
          temperament: nature.temperament?.trim() || null,
          obsession: nature.obsession?.trim() || null,
          fear: nature.fear?.trim() || null,
          speech_style: nature.speech_style?.trim() || null,
          secret: nature.secret?.trim() || null,
          ...(choosePassions ? passions.values : {}),
          inspiration: wish.trim(),
        }
        return unwrap(api.POST('/api/sons/summon', { body }))
      }}
      onDone={() => {
        naming.reset()
        setNature({})
        passions.even()
        setWish('')
      }}
    >
      {(blocked) => (
        <>
          <Step
            number={1}
            title='Who they are'
            hint='A name and a title; leave them to the summoning if you wish.'
            icon={ScrollText}
          >
            <ShapeFields
              shape={naming.shape}
              onChange={naming.setShape}
              titled
              described={false}
              blocked={blocked}
            />
          </Step>
          <Step
            number={2}
            title='Their place in the pantheon'
            hint='The world they are sent to, their rarity and their two domains.'
            icon={Crown}
          >
            <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
              <WorldPicker choice={choice} blocked={blocked} />
              <MindPicker
                label='Rarity'
                value={rarity}
                table={{
                  [ANY]: 'Let the summoning roll',
                  ...Object.fromEntries(
                    rarityValues.map((key) => [key, RARITY_LABEL[key]])
                  ),
                }}
                blocked={blocked}
                onPick={setRarity}
              />
              <MindPicker
                label='First domain'
                value={first}
                table={domains}
                blocked={blocked}
                onPick={setFirst}
              />
              <MindPicker
                label='Second domain'
                value={second}
                table={domains}
                blocked={blocked}
                onPick={setSecond}
              />
            </div>
          </Step>
          <Step
            number={3}
            title='Their nature'
            hint='Write any part of their nature; what you leave empty the summoning writes.'
            icon={Sparkles}
          >
            <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
              {NATURE.map((key) => (
                <FormRow key={key} label={NATURE_LABEL[key]}>
                  {(id) => (
                    <Textarea
                      id={id}
                      value={nature[key] ?? ''}
                      disabled={blocked !== null}
                      onChange={(event) =>
                        setNature({ ...nature, [key]: event.target.value })
                      }
                    />
                  )}
                </FormRow>
              ))}
            </div>
          </Step>
          <Step
            number={4}
            title='Passions'
            hint='How loyal, ambitious, wrathful and merciful they are, from 0 to 100.'
            icon={SlidersHorizontal}
            tools={
              <div className='flex shrink-0 items-center gap-3'>
                <FieldTile label='Set them myself' framed={false}>
                  <Switch
                    aria-label='Set the passions myself'
                    checked={choosePassions}
                    disabled={blocked !== null}
                    onCheckedChange={setChoosePassions}
                  />
                </FieldTile>
                <MeasureTools
                  onRoll={passions.roll}
                  onEven={passions.even}
                  blocked={
                    blocked ??
                    (choosePassions
                      ? null
                      : 'The summoning chooses the passions')
                  }
                />
              </div>
            }
          >
            <MeasureGrid
              measures={PASSIONS}
              values={passions.values}
              onChange={passions.set}
              blocked={
                blocked ??
                (choosePassions ? null : 'The summoning chooses the passions')
              }
            />
          </Step>
          <Step
            number={5}
            title='Anything else'
            hint='Free words the summoning reads beside the values you set.'
            icon={ScrollText}
          >
            <FormRow label='For the summoning'>
              {(id) => (
                <Textarea
                  id={id}
                  value={wish}
                  disabled={blocked !== null}
                  onChange={(event) => setWish(event.target.value)}
                />
              )}
            </FormRow>
          </Step>
        </>
      )}
    </ShapeDialog>
  )
}

export function RaiseRegionDialog() {
  const naming = useShape()
  const choice = useWorldChoice(true)
  const [near, setNear] = useState<number | null>(null)
  const [water, setWater] = useState(false)
  const land = useMeasures(LAND)
  return (
    <ShapeDialog
      icon={Mountain}
      trigger='Raise a region'
      title='Raise a region'
      description='A new region of a world, beside another if you choose one, with the breadth, danger, fertility and magic you set.'
      missing={choice.world === ANY ? 'Choose the world it rises in' : null}
      summary={`${named(naming.shape.name, 'A new land')}${water ? ', water' : ''} in ${choice.name ?? 'a world'}`}
      run={() =>
        postAction('region:shape', {
          world_id: Number(choice.world),
          near_id: near,
          water,
          ...land.values,
          ...naming.body,
        })
      }
      onDone={() => {
        naming.reset()
        land.even()
      }}
    >
      {(blocked) => (
        <>
          <Step
            number={1}
            title='Its name and story'
            hint='Leave them empty and the world names and tells it.'
            icon={ScrollText}
          >
            <ShapeFields
              shape={naming.shape}
              onChange={naming.setShape}
              blocked={blocked}
            />
          </Step>
          <Step
            number={2}
            title='Where it rises'
            hint='The world, the region it lies beside and whether it is land or water.'
            icon={MapPin}
          >
            <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
              <WorldPicker choice={choice} blocked={blocked} />
              <NodePicker
                label='Beside the region'
                types={REGIONS}
                value={near}
                onChange={setNear}
                blocked={blocked}
              />
              <WaterTile water={water} onChange={setWater} blocked={blocked} />
            </div>
          </Step>
          <Step
            number={3}
            title='Its land'
            hint='Four measures from 0 to 100.'
            icon={SlidersHorizontal}
            tools={
              <MeasureTools
                onRoll={land.roll}
                onEven={land.even}
                blocked={blocked}
              />
            }
          >
            <MeasureGrid
              measures={LAND}
              values={land.values}
              onChange={land.set}
              blocked={blocked}
            />
          </Step>
        </>
      )}
    </ShapeDialog>
  )
}

export function FoundSettlementDialog() {
  const naming = useShape()
  const [people, setPeople] = useState<number | null>(null)
  const settlers = useMeasures([SETTLERS])
  return (
    <ShapeDialog
      icon={Landmark}
      trigger='Found a settlement'
      title='Found a settlement'
      description='Settlers leave a people to found a new town in its land; name it and choose how many go.'
      missing={
        people === null ? 'Choose the people who send the settlers' : null
      }
      summary={`${named(naming.shape.name, 'A new town')}, ${plural(settlers.values.settlers, 'settler', 'settlers')}`}
      run={() =>
        postAction('people:village', {
          people_id: people ?? 0,
          settlers: settlers.values.settlers,
          ...naming.body,
        })
      }
      onDone={naming.reset}
    >
      {(blocked) => (
        <>
          <Step
            number={1}
            title='Its name and story'
            hint='Leave them empty and the world names and tells it.'
            icon={ScrollText}
          >
            <ShapeFields
              shape={naming.shape}
              onChange={naming.setShape}
              blocked={blocked}
            />
          </Step>
          <Step
            number={2}
            title='Who founds it'
            hint='The people who send the settlers and how many of them go.'
            icon={MapPin}
          >
            <NodePicker
              label='The people who send them'
              types={PEOPLES}
              value={people}
              onChange={setPeople}
              blocked={blocked}
            />
            <MeasureField
              measure={SETTLERS}
              value={settlers.values.settlers}
              onChange={(value) => settlers.set('settlers', value)}
              blocked={blocked}
            />
          </Step>
        </>
      )}
    </ShapeDialog>
  )
}

type RecordKind = 'celestial' | 'spirit' | 'natural_law' | 'cult'

const RECORD: Record<
  RecordKind,
  { icon: LucideIcon; trigger: string; description: string; noun: string }
> = {
  celestial: {
    icon: Moon,
    trigger: 'Set a body in the sky',
    description:
      'A body in the sky of a world, with its brightness, influence, visibility and the length of its cycle.',
    noun: 'A body in the sky',
  },
  spirit: {
    icon: Ghost,
    trigger: 'Raise a spirit',
    description:
      'A spirit of your making, where you place it, with the strength and unrest you set.',
    noun: 'A spirit',
  },
  natural_law: {
    icon: Scale,
    trigger: 'Lay down a law of nature',
    description:
      'A law of nature of a world, working by the mechanism you choose.',
    noun: 'A law of nature',
  },
  cult: {
    icon: Church,
    trigger: 'Raise a faith',
    description:
      'A faith that worships the god you choose, with its followers, zeal and influence.',
    noun: 'A faith',
  },
}

export function ShapeRecordDialog({ kind }: { kind: RecordKind }) {
  const spec = RECORD[kind]
  const measures = RECORD_MEASURES[kind]
  const naming = useShape()
  const choice = useWorldChoice(true)
  const [place, setPlace] = useState<number | null>(null)
  const [god, setGod] = useState<number | null>(null)
  const [law, setLaw] = useState<string>(LAWS[0])
  const power = useMeasures([POWER])
  const values = useMeasures(measures)
  const missing =
    naming.shape.name.trim() === ''
      ? 'Name it first'
      : kind === 'cult' && god === null
        ? 'Choose the god it worships'
        : null
  return (
    <ShapeDialog
      icon={spec.icon}
      trigger={spec.trigger}
      title={spec.trigger}
      description={spec.description}
      missing={missing}
      summary={`${named(naming.shape.name, spec.noun)} in ${choice.name ?? 'a world'}, power ${power.values.power}`}
      run={() =>
        postAction('record:shape', {
          entity_type: kind,
          world_id: choice.world === ANY ? null : Number(choice.world),
          location_id: place,
          power: power.values.power,
          natural_law:
            kind === 'natural_law'
              ? (law as ActionBody<'record:shape'>['natural_law'])
              : null,
          god_id: kind === 'cult' ? god : null,
          ...values.values,
          ...naming.body,
        })
      }
      onDone={() => {
        naming.reset()
        values.even()
      }}
    >
      {(blocked) => (
        <>
          <Step
            number={1}
            title='Its name and story'
            hint='It needs a name; the rest the world can tell.'
            icon={ScrollText}
          >
            <ShapeFields
              shape={naming.shape}
              onChange={naming.setShape}
              titled
              blocked={blocked}
            />
          </Step>
          <Step
            number={2}
            title='Where it stands and what it is'
            hint='The world, the place it belongs to and how much it weighs.'
            icon={MapPin}
          >
            <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
              <WorldPicker choice={choice} blocked={blocked} />
              <NodePicker
                label='Where it stands'
                types={PLACES}
                value={place}
                onChange={setPlace}
                blocked={blocked}
              />
              {kind === 'natural_law' && (
                <MindPicker
                  label='Mechanism'
                  value={law}
                  table={valueTable(LAWS)}
                  blocked={blocked}
                  onPick={setLaw}
                />
              )}
              {kind === 'cult' && (
                <GodPicker
                  label='The god it worships'
                  kinds={GODS}
                  value={god}
                  onChange={setGod}
                  blocked={blocked}
                />
              )}
            </div>
            <MeasureField
              measure={POWER}
              value={power.values.power}
              onChange={(value) => power.set('power', value)}
              blocked={blocked}
            />
          </Step>
          {measures.length > 0 && (
            <Step
              number={3}
              title='Its measures'
              hint='Each starts in the middle; roll them or set them yourself.'
              icon={SlidersHorizontal}
              tools={
                <MeasureTools
                  onRoll={values.roll}
                  onEven={values.even}
                  blocked={blocked}
                />
              }
            >
              <MeasureGrid
                measures={measures}
                values={values.values}
                onChange={values.set}
                blocked={blocked}
              />
            </Step>
          )}
        </>
      )}
    </ShapeDialog>
  )
}

export function SummonOuterBeingDialog() {
  const naming = useShape()
  const choice = useWorldChoice(true)
  return (
    <ShapeDialog
      icon={Skull}
      trigger='Summon an outer being'
      title='Summon an outer being'
      description='A being from outside takes shape in the world you choose; name it and tell what it is if you wish.'
      missing={choice.world === ANY ? 'Choose the world it enters' : null}
      summary={`${named(naming.shape.name, 'A being from outside')} entering ${choice.name ?? 'a world'}`}
      run={() =>
        postAction('horror:outer_being', {
          world_id: Number(choice.world),
          ...naming.body,
        })
      }
      onDone={naming.reset}
    >
      {(blocked) => (
        <>
          <Step
            number={1}
            title='Its name and story'
            hint='Leave them empty and the world names and tells it.'
            icon={ScrollText}
          >
            <ShapeFields
              shape={naming.shape}
              onChange={naming.setShape}
              titled
              blocked={blocked}
            />
          </Step>
          <Step
            number={2}
            title='Where it enters'
            hint='The world that receives it.'
            icon={MapPin}
          >
            <WorldPicker choice={choice} blocked={blocked} />
          </Step>
        </>
      )}
    </ShapeDialog>
  )
}
