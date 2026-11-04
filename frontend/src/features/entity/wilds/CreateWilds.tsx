import { type ReactNode, useId, useState } from 'react'
import { Dna, Footprints, Plus, Sparkles, Wand2 } from 'lucide-react'
import {
  beastTemperValues,
  bodyPlanValues,
  creatureTraitValues,
  dietValues,
  sizeClassValues,
  socialityValues,
  yieldProductValues,
} from '@/api/generated/schema'
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
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Medallion } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { PLANS } from '../body/labels'
import { busyOf } from '../lore/model'
import { useWildAction } from './api'
import {
  DIET,
  type Named,
  SIZE,
  SOCIALITY,
  TEMPER,
  TRAIT,
  named,
  titled,
} from './labels'
import { NumberField, SwitchField } from './parts'

const SPECIES_STATS = [
  ['hp', 'Health', 1, 100000],
  ['strength', 'Strength', 0, 100],
  ['agility', 'Agility', 0, 100],
  ['intelligence', 'Intelligence', 0, 100],
  ['danger', 'Danger', 0, 100],
  ['might', 'Might', 0, 100],
  ['abundance', 'Abundance', 0, 100],
] as const
const BEAST_STATS = [
  ['hp', 'Health', 1, 100000],
  ['strength', 'Strength', 0, 100],
  ['agility', 'Agility', 0, 100],
  ['danger', 'Danger', 0, 100],
  ['cunning', 'Cunning', 0, 100],
  ['renown', 'Renown', 0, 100],
  ['terror', 'Terror', 0, 100],
  ['endurance', 'Endurance', 0, 100],
  ['perception', 'Perception', 0, 100],
  ['willpower', 'Willpower', 0, 100],
  ['intelligence', 'Intelligence', 0, 100],
] as const
const POWER_MAX = 10

function numbers(
  fields: readonly (readonly [string, string, number, number])[],
  values: Record<string, string>
): Record<string, number> {
  return Object.fromEntries(
    fields
      .filter(([key]) => (values[key] ?? '') !== '')
      .map(([key, , low, high]) => [
        key,
        Math.min(high, Math.max(low, Math.round(Number(values[key]) || 0))),
      ])
  )
}

export function ChoiceGrid({
  label,
  values,
  table,
  chosen,
  onPick,
}: {
  label: string
  values: readonly string[]
  table: Record<string, Named>
  chosen: readonly string[]
  onPick: (value: string) => void
}) {
  return (
    <div
      className='flex min-w-0 flex-col gap-1.5'
      role='group'
      aria-label={label}
    >
      <Label variant='overline'>{label}</Label>
      <div className='grid min-w-0 grid-cols-2 gap-1.5 sm:grid-cols-3 md:grid-cols-4'>
        {values.map((value) => {
          const spec = named(table, value)
          const picked = chosen.includes(value)
          return (
            <Button
              key={value}
              type='button'
              size='sm'
              variant={picked ? 'default' : 'outline'}
              aria-pressed={picked}
              onClick={() => onPick(value)}
              className='min-w-0 justify-start'
            >
              <spec.icon />
              <span className='min-w-0 truncate'>{spec.label}</span>
            </Button>
          )
        })}
      </div>
    </div>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: (id: string) => ReactNode
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label as='label' htmlFor={id}>
        {label}
      </Label>
      {children(id)}
    </div>
  )
}

function StatFields({
  fields,
  values,
  onChange,
}: {
  fields: readonly (readonly [string, string, number, number])[]
  values: Record<string, string>
  onChange: (key: string, value: string) => void
}) {
  return (
    <div className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4'>
      {fields.map(([key, label, low, high]) => (
        <NumberField
          key={key}
          label={label}
          value={values[key] ?? ''}
          min={low}
          max={high}
          onChange={(value) => onChange(key, value)}
        />
      ))}
    </div>
  )
}

function toggled(list: string[], value: string): string[] {
  return list.includes(value)
    ? list.filter((item) => item !== value)
    : [...list, value]
}

const PRODUCTS: Record<string, Named> = Object.fromEntries(
  yieldProductValues.map((key) => [
    key,
    { label: titled(key), icon: Sparkles, tone: 'gold' as const },
  ])
)

export function CreateSpeciesDialog({ regionId }: { regionId?: number }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [region, setRegion] = useState<number | null>(regionId ?? null)
  const [plan, setPlan] = useState('quadruped')
  const [size, setSize] = useState('medium')
  const [diet, setDiet] = useState('herbivore')
  const [social, setSocial] = useState('herd')
  const [nocturnal, setNocturnal] = useState(false)
  const [migratory, setMigratory] = useState(false)
  const [products, setProducts] = useState<string[]>([])
  const [traits, setTraits] = useState<string[]>([])
  const [stats, setStats] = useState<Record<string, string>>({
    abundance: '40',
  })
  const [power, setPower] = useState('2')
  const { reason } = useGodGate()
  const create = useWildAction<void>(
    'species:create',
    () => ({
      name: name.trim(),
      description: description.trim(),
      region_id: region,
      body_plan: plan,
      size_class: size,
      diet,
      sociality: social,
      nocturnal,
      migratory,
      products,
      traits,
      power: Math.min(POWER_MAX, Math.max(1, Math.round(Number(power) || 1))),
      ...numbers(SPECIES_STATS, stats),
    }),
    () => {
      setOpen(false)
      setName('')
      setDescription('')
    }
  )
  const busy = busyOf(reason(), create.isPending)
  const missing =
    name.trim() === ''
      ? 'Name the kind'
      : region === null
        ? 'Choose the land it first lives in'
        : null
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant='outline' size='sm'>
          <Dna />
          Create a kind
        </Button>
      </DialogTrigger>
      <DialogContent className='max-h-dvh overflow-y-auto sm:max-w-3xl'>
        <DialogHeader>
          <DialogTitle>Create a kind</DialogTitle>
          <DialogDescription>
            Choose its body, size, diet and habits. The world reads them as you
            set them: what it hunts, where it thrives, what it yields and
            whether it can be tamed.
          </DialogDescription>
        </DialogHeader>
        <div data-surface='SpeciesForm' className='flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
            <Field label='Name'>
              {(id) => (
                <Input
                  id={id}
                  value={name}
                  placeholder='Ashwing, Glimmerdeer…'
                  onChange={(event) => setName(event.target.value)}
                />
              )}
            </Field>
            <div className='flex min-w-0 flex-col gap-1'>
              <Label>First land</Label>
              <EntityPicker
                types={['region']}
                value={region}
                onChange={setRegion}
                placeholder='Choose a land…'
              />
            </div>
          </div>
          <Field label='What it is like'>
            {(id) => (
              <Textarea
                id={id}
                value={description}
                placeholder='How it looks and moves; the world never reads its nature from these words.'
                onChange={(event) => setDescription(event.target.value)}
              />
            )}
          </Field>
          <ChoiceGrid
            label='Body'
            values={bodyPlanValues.filter(
              (value) => value !== 'divine_manifest'
            )}
            table={PLANS}
            chosen={[plan]}
            onPick={setPlan}
          />
          <ChoiceGrid
            label='Size'
            values={sizeClassValues}
            table={SIZE}
            chosen={[size]}
            onPick={setSize}
          />
          <ChoiceGrid
            label='Diet'
            values={dietValues}
            table={DIET}
            chosen={[diet]}
            onPick={setDiet}
          />
          <ChoiceGrid
            label='Lives'
            values={socialityValues}
            table={SOCIALITY}
            chosen={[social]}
            onPick={setSocial}
          />
          <div className='grid min-w-0 grid-cols-2 gap-3'>
            <SwitchField
              label='Wakes at night'
              checked={nocturnal}
              onChange={setNocturnal}
            />
            <SwitchField
              label='Migrates with the seasons'
              checked={migratory}
              onChange={setMigratory}
            />
          </div>
          <ChoiceGrid
            label='Yields beyond meat, hide and bone'
            values={yieldProductValues}
            table={PRODUCTS}
            chosen={products}
            onPick={(value) => setProducts((before) => toggled(before, value))}
          />
          <ChoiceGrid
            label='Traits'
            values={creatureTraitValues.filter(
              (value) => value !== 'sacred_animal'
            )}
            table={TRAIT}
            chosen={traits}
            onPick={(value) => setTraits((before) => toggled(before, value))}
          />
          <div className='flex min-w-0 flex-col gap-1.5'>
            <Label variant='overline'>Its numbers</Label>
            <Muted variant='caption'>
              Leave a number empty and the world sets it.
            </Muted>
            <StatFields
              fields={SPECIES_STATS}
              values={stats}
              onChange={(key, value) =>
                setStats((before) => ({ ...before, [key]: value }))
              }
            />
            <div className='max-w-40'>
              <NumberField
                label='Power'
                value={power}
                min={1}
                max={POWER_MAX}
                onChange={setPower}
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() => create.mutate()}
          >
            <Plus />
            Let it walk the land
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function CreateBeastDialog({
  regionId,
  speciesId,
}: {
  regionId?: number
  speciesId?: number
}) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [species, setSpecies] = useState<number | null>(speciesId ?? null)
  const [lair, setLair] = useState<number | null>(regionId ?? null)
  const [size, setSize] = useState('huge')
  const [temper, setTemper] = useState('sleeping')
  const [stats, setStats] = useState<Record<string, string>>({
    strength: '80',
    terror: '20',
    renown: '20',
  })
  const [power, setPower] = useState('3')
  const { reason } = useGodGate()
  const create = useWildAction<void>(
    'beast:create',
    () => ({
      name: name.trim(),
      description: description.trim(),
      species_id: species,
      lair_id: lair,
      size_class: size,
      temper,
      power: Math.min(POWER_MAX, Math.max(1, Math.round(Number(power) || 1))),
      ...numbers(BEAST_STATS, stats),
    }),
    () => {
      setOpen(false)
      setName('')
      setDescription('')
    }
  )
  const busy = busyOf(reason(), create.isPending)
  const missing =
    name.trim() === ''
      ? 'Name the beast'
      : lair === null && species === null
        ? 'Choose its lair or its kind'
        : null
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant='outline' size='sm'>
          <Footprints />
          Call forth a beast
        </Button>
      </DialogTrigger>
      <DialogContent className='max-h-dvh overflow-y-auto sm:max-w-3xl'>
        <DialogHeader>
          <DialogTitle>Call forth a beast</DialogTitle>
          <DialogDescription>
            A named beast sleeps, wakes, raids, hoards and is remembered. Its
            endurance, perception and willpower shape how far it ranges, how
            easily it wakes and whether it can ever be tamed.
          </DialogDescription>
        </DialogHeader>
        <div data-surface='BeastForm' className='flex min-w-0 flex-col gap-4'>
          <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
            <Field label='Name'>
              {(id) => (
                <Input
                  id={id}
                  value={name}
                  placeholder='Vharrun the Ash-Maw…'
                  onChange={(event) => setName(event.target.value)}
                />
              )}
            </Field>
            <div className='flex min-w-0 flex-col gap-1'>
              <Label>Greatest of the kind (optional)</Label>
              <EntityPicker
                types={['species']}
                value={species}
                onChange={setSpecies}
                placeholder='A kind of its own…'
              />
            </div>
            <div className='flex min-w-0 flex-col gap-1'>
              <Label>Lair</Label>
              <EntityPicker
                types={['place', 'region']}
                value={lair}
                onChange={setLair}
                placeholder='Choose a place…'
              />
            </div>
          </div>
          <Field label='What it is like'>
            {(id) => (
              <Textarea
                id={id}
                value={description}
                placeholder='Its look and its legend.'
                onChange={(event) => setDescription(event.target.value)}
              />
            )}
          </Field>
          <ChoiceGrid
            label='Size'
            values={sizeClassValues}
            table={SIZE}
            chosen={[size]}
            onPick={setSize}
          />
          <ChoiceGrid
            label='Temper'
            values={beastTemperValues}
            table={TEMPER}
            chosen={[temper]}
            onPick={setTemper}
          />
          <div className='flex min-w-0 flex-col gap-1.5'>
            <Label variant='overline'>Its might and mind</Label>
            <Muted variant='caption'>
              Leave a number empty and the world sets it from its kind.
            </Muted>
            <StatFields
              fields={BEAST_STATS}
              values={stats}
              onChange={(key, value) =>
                setStats((before) => ({ ...before, [key]: value }))
              }
            />
            <div className='max-w-40'>
              <NumberField
                label='Power'
                value={power}
                min={1}
                max={POWER_MAX}
                onChange={setPower}
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button
            disabled={busy !== null || missing !== null}
            disabledReason={busy ?? missing ?? undefined}
            onClick={() => create.mutate()}
          >
            <Wand2 />
            Call it forth
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function WildsCreateBar({ regionId }: { regionId: number }) {
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border border-dashed bg-muted/20 p-3'>
      <Medallion icon={Sparkles} tone='success' size='sm' />
      <div className='flex min-w-0 flex-1 basis-60 flex-col'>
        <Text weight='semibold'>Fill this land with life</Text>
        <Muted variant='caption'>
          Create a new kind with a nature you choose, or call forth a named
          beast to haunt or guard it.
        </Muted>
      </div>
      <CreateSpeciesDialog regionId={regionId} />
      <CreateBeastDialog regionId={regionId} />
    </div>
  )
}
