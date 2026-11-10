import { useId, useState } from 'react'
import {
  Coins,
  Gem,
  Hammer,
  Lock,
  Pickaxe,
  Plus,
  RotateCcw,
  Save,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import {
  AttributeTile,
  EntityLink,
  IconStat,
  Medallion,
  PagedList,
  LoadingBlock,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import {
  AdjustPanel,
  FIELD_GRID,
  NumberField,
  PartHeader,
} from '@/features/entity/economy/EntityEconomy'
import {
  ECONOMY_REFRESH,
  useWorldMaterials,
} from '@/features/entity/economy/api'
import {
  COMMODITY,
  type CommodityKind,
  GOODS_FAMILY,
  type KnowledgeBranch,
  MATERIAL_FAMILY,
  MATERIAL_ORIGIN,
  MATERIAL_PROPERTIES,
  type MaterialFamily,
  type MaterialKind,
  type Named,
  branch,
} from '@/features/entity/economy/labels'
import {
  FORM_CARD,
  NONE,
  branchChoices,
  materialRef,
  useBusy,
  whole,
} from '@/features/entity/economy/model'
import {
  ChoiceSelect,
  ConfirmButton,
  EntityChoice,
  HeldBadge,
  MaterialSelect,
  NoteField,
  ReleaseButton,
  TextField,
} from '@/features/entity/economy/parts'
import { useGodAction } from '@/features/pantheon/godAction'
import { Opener } from './Opener'

type Material = components['schemas']['MaterialView']
type PropertyKey = (typeof MATERIAL_PROPERTIES)[number]['key']

const PERCENT = 100
const BASE = 100
const MAX_LEVEL = 20
const ALL = 'all'
const PAGE = 12
const PLAIN_VALUE = '50'
const MATERIAL_FAMILIES = Object.keys(MATERIAL_FAMILY) as MaterialFamily[]
const LAND_TYPES = ['region', 'place'] as const
const DEPOSIT_TYPES = ['region', 'place', 'people', 'settlement'] as const
const FAMILY_CHOICES: Record<string, Named> = { ...MATERIAL_FAMILY }
const COMMODITY_CHOICES: Record<string, Named> = Object.fromEntries(
  Object.entries(COMMODITY).map(([key, item]) => [
    key,
    {
      label: item.label,
      icon: item.icon,
      tone: GOODS_FAMILY[item.family].tone,
    },
  ])
)

function propertyTone(key: PropertyKey) {
  if (key === 'corruption' || key === 'decay') return 'destructive'
  if (key === 'sanctity') return 'verdigris'
  return 'default'
}

function premiumWord(pct: number): 'gold' | 'muted' | 'info' {
  if (pct > BASE) return 'gold'
  if (pct < BASE) return 'muted'
  return 'info'
}

function valuesOf(source: Record<PropertyKey, number> | null) {
  return Object.fromEntries(
    MATERIAL_PROPERTIES.map(({ key }) => [
      key,
      source ? String(source[key]) : PLAIN_VALUE,
    ])
  ) as Record<PropertyKey, string>
}

function clampValues(values: Record<string, string>): Record<string, number> {
  return Object.fromEntries(
    Object.entries(values).map(([key, value]) => [key, whole(value, PERCENT)])
  )
}

function PropertyField({
  property,
  value,
  aria,
  onChange,
}: {
  property: (typeof MATERIAL_PROPERTIES)[number]
  value: string
  aria: string
  onChange: (next: string) => void
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <Label
        as='label'
        htmlFor={id}
        className='flex min-w-0 items-center gap-1.5'
      >
        <property.icon
          aria-hidden='true'
          className='size-icon-xs shrink-0 text-muted-foreground'
        />
        {property.label}
      </Label>
      <Input
        id={id}
        type='number'
        inputMode='numeric'
        min={0}
        max={PERCENT}
        value={value}
        aria-label={aria}
        onChange={(event) => onChange(event.target.value)}
      />
      <Muted variant='caption' truncate>
        {property.hint}
      </Muted>
    </div>
  )
}

function PropertyGrid({
  values,
  prefix,
  onChange,
}: {
  values: Record<string, string>
  prefix: string
  onChange: (key: PropertyKey, next: string) => void
}) {
  return (
    <div
      className={cn(
        FIELD_GRID,
        'grid-cols-2 items-start @md/card:grid-cols-3 @md/form:grid-cols-3 @2xl/card:grid-cols-5 @2xl/form:grid-cols-5'
      )}
    >
      {MATERIAL_PROPERTIES.map((property) => (
        <PropertyField
          key={property.key}
          property={property}
          aria={`${prefix} ${property.key}`}
          value={values[property.key]}
          onChange={(next) => onChange(property.key, next)}
        />
      ))}
    </div>
  )
}

function SwitchRow({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string
  checked: boolean
  disabled?: boolean
  onChange: (value: boolean) => void
}) {
  const id = useId()
  return (
    <div className='flex min-w-0 items-center gap-2'>
      <Switch
        id={id}
        checked={checked}
        disabled={disabled}
        onCheckedChange={onChange}
        aria-label={label}
      />
      <Label as='label' htmlFor={id}>
        {label}
      </Label>
    </div>
  )
}

function MaterialCard({
  worldId,
  material,
}: {
  worldId: number
  material: Material
}) {
  const [values, setValues] = useState<Record<string, string>>({
    ...valuesOf(material),
    level: String(material.level),
  })
  const [name, setName] = useState(material.label)
  const [description, setDescription] = useState(material.description ?? '')
  const [family, setFamily] = useState<string>(material.family)
  const [craft, setCraft] = useState<string>(material.branch ?? NONE)
  const [hold, setHold] = useState(material.held)
  const target = {
    world_id: worldId,
    material: material.world_material_id === null ? material.kind : null,
    world_material_id: material.world_material_id,
  }
  const edit = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/material:edit', {
          body: {
            ...target,
            values: {
              ...clampValues(
                Object.fromEntries(
                  Object.entries(values).filter(([key]) => key !== 'level')
                )
              ),
              level: whole(values.level, MAX_LEVEL),
            },
            name: material.world_material_id !== null ? name : null,
            description: description.trim() || null,
            family: family as MaterialFamily,
            branch: craft === NONE ? null : (craft as KnowledgeBranch),
            clear_branch: craft === NONE && material.branch !== null,
            hold,
          },
        })
      ),
  })
  const release = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(api.POST('/api/actions/material:release', { body: target })),
  })
  const remove = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(api.POST('/api/actions/material:delete', { body: target })),
  })
  const keep = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () => unwrap(api.POST('/api/actions/material:hold', { body: target })),
  })
  const busy = useBusy(
    null,
    edit.isPending,
    release.isPending,
    remove.isPending,
    keep.isPending
  )
  const look = MATERIAL_FAMILY[material.family]
  const origin = MATERIAL_ORIGIN[material.origin]
  const needs = material.branch ? branch(material.branch) : null
  const gate = material.gate ? branch(material.gate) : null
  const substance = material.world_material_id !== null
  return (
    <li
      data-material={material.kind ?? material.world_material_id ?? undefined}
      className='@container/card flex h-full min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion icon={look.icon} tone={look.tone} />
        <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
          <Text weight='semibold' truncate>
            {material.label}
          </Text>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Badge size='sm' variant='outline'>
              <look.icon />
              {look.label}
            </Badge>
            {material.origin !== 'catalog' && (
              <Badge size='sm' variant='warning'>
                <origin.icon />
                {origin.label}
              </Badge>
            )}
            {needs && (
              <Badge size='sm' variant='info'>
                <needs.icon />
                {`Needs ${needs.label.toLowerCase()} ${material.level}`}
              </Badge>
            )}
            {gate && (
              <Badge size='sm' variant='info'>
                <gate.icon />
                {`and ${gate.label.toLowerCase()}`}
              </Badge>
            )}
            {material.edited && (
              <Badge size='sm' variant='secondary'>
                <Save />
                Edited in this world
              </Badge>
            )}
            <HeldBadge held={material.held} />
          </div>
        </div>
      </div>
      {material.description && (
        <Muted variant='caption' truncate={2}>
          {material.description}
        </Muted>
      )}
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <IconStat
          icon={Coins}
          label='Price of goods made of it'
          value={`Goods of it sell at ${material.price_premium_pct}%`}
          tone={premiumWord(material.price_premium_pct)}
        />
        <IconStat
          icon={Gem}
          label='Worth of things made of it'
          value={`Things of it are worth ${material.worth_pct}%`}
          tone={premiumWord(material.worth_pct)}
        />
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-1.5 @md/card:grid-cols-3 @2xl/card:grid-cols-5'>
        {MATERIAL_PROPERTIES.map((property) => (
          <AttributeTile
            key={property.key}
            icon={property.icon}
            abbr={property.abbr}
            label={property.label}
            value={material[property.key]}
            max={PERCENT}
            hint={property.hint}
            tone={propertyTone(property.key)}
          />
        ))}
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-3'>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {material.deposit_id !== null &&
            material.deposit_id !== undefined && (
              <EntityLink kind='entity' id={String(material.deposit_id)}>
                Its deposit
              </EntityLink>
            )}
          <ReleaseButton
            held={material.held}
            busy={busy}
            onRelease={() => release.mutate(undefined)}
          />
          {!material.held && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => keep.mutate(undefined)}
            >
              <Lock />
              Hold as it is
            </Button>
          )}
          {!substance && material.edited && (
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => remove.mutate(undefined)}
            >
              <RotateCcw />
              Return to the catalog
            </Button>
          )}
          {substance && (
            <ConfirmButton
              icon={Trash2}
              label='Unmake this substance'
              title={`Unmake ${material.label}?`}
              description='It vanishes from this world: its deposits, goods and coins fall back to their nearest common kin.'
              confirm='Unmake it'
              busy={busy}
              onConfirm={() => remove.mutate(undefined)}
            />
          )}
        </div>
        <AdjustPanel
          label='Adjust the material'
          title={`The physics of ${material.label.toLowerCase()}`}
          note='Every value runs from 0 to 100 and is this world’s law for the material.'
          hold={hold}
          onHold={setHold}
        >
          <div className={cn(FIELD_GRID, '@md/card:grid-cols-3')}>
            {substance && (
              <TextField
                label={`${material.label} name`}
                value={name}
                onChange={setName}
              />
            )}
            <ChoiceSelect
              label='Family'
              value={family}
              table={FAMILY_CHOICES}
              blocked={busy}
              onPick={setFamily}
            />
            <ChoiceSelect
              label='Craft it needs'
              value={craft}
              table={branchChoices('No craft needed')}
              blocked={busy}
              onPick={setCraft}
            />
            <NumberField
              label='Level of that craft (0–20)'
              aria={`${material.label} level`}
              value={values.level}
              max={MAX_LEVEL}
              onChange={(next) =>
                setValues((current) => ({ ...current, level: next }))
              }
            />
          </div>
          <PropertyGrid
            values={values}
            prefix={material.label}
            onChange={(key, next) =>
              setValues((current) => ({ ...current, [key]: next }))
            }
          />
          <NoteField
            label='Description'
            value={description}
            placeholder='What it looks like, where it is found, what the peoples say of it'
            onChange={setDescription}
          />
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => edit.mutate(undefined)}
          >
            <Save />
            Set these properties
          </Button>
        </AdjustPanel>
      </div>
    </li>
  )
}

export function MaterialForge({
  worldId,
  materials,
  onDone,
}: {
  worldId: number
  materials: Material[]
  onDone?: () => void
}) {
  const catalog = materials.filter((row) => row.kind !== null)
  const [name, setName] = useState('')
  const [family, setFamily] = useState<string>('metal')
  const [akin, setAkin] = useState<string>(NONE)
  const [values, setValues] = useState<Record<string, string>>(valuesOf(null))
  const [craft, setCraft] = useState<string>(NONE)
  const [level, setLevel] = useState('0')
  const [description, setDescription] = useState('')
  const [vein, setVein] = useState<string | null>(null)
  const forge = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/material:create', {
          body: {
            world_id: worldId,
            name: name.trim(),
            family: family as MaterialFamily,
            base_kind: akin === NONE ? null : (akin as MaterialKind),
            values: clampValues(values),
            branch: craft === NONE ? null : (craft as KnowledgeBranch),
            level: whole(level, MAX_LEVEL),
            description: description.trim() || null,
            place_id: vein === null ? null : Number(vein),
          },
        })
      ),
    onDone: () => {
      setName('')
      setDescription('')
      setVein(null)
      onDone?.()
    },
  })
  const gate = useBusy(null, forge.isPending)
  const busy = gate ?? (name.trim() ? null : 'Give the material a name first.')
  const akinTable: Record<string, Named> = {
    [NONE]: { label: 'Like nothing else', icon: Sparkles, tone: 'muted' },
    ...Object.fromEntries(
      catalog.map((row) => [
        row.kind as string,
        {
          label: row.label,
          icon: MATERIAL_FAMILY[row.family].icon,
          tone: MATERIAL_FAMILY[row.family].tone,
        },
      ])
    ),
  }
  const pickAkin = (next: string) => {
    setAkin(next)
    const row = catalog.find((item) => item.kind === next)
    if (!row) return
    setValues(valuesOf(row))
    setFamily(row.family)
  }
  return (
    <div data-surface='MaterialForge' className={FORM_CARD}>
      <PartHeader
        icon={Hammer}
        title='Forge a new material'
        note='A substance only this world knows. Start it akin to a known material to borrow its nature, then bend every value.'
      />
      <div className={cn(FIELD_GRID, '@md/form:grid-cols-3')}>
        <TextField
          label='Name'
          value={name}
          placeholder='The material’s name, in this world’s own words'
          onChange={setName}
        />
        <ChoiceSelect
          label='Family'
          value={family}
          table={FAMILY_CHOICES}
          blocked={gate}
          onPick={setFamily}
        />
        <ChoiceSelect
          label='Akin to'
          value={akin}
          table={akinTable}
          blocked={gate}
          onPick={pickAkin}
        />
      </div>
      <PropertyGrid
        values={values}
        prefix='New material'
        onChange={(key, next) =>
          setValues((current) => ({ ...current, [key]: next }))
        }
      />
      <div className={cn(FIELD_GRID, '@md/form:grid-cols-3')}>
        <ChoiceSelect
          label='Craft it needs'
          value={craft}
          table={branchChoices('No craft needed')}
          blocked={gate}
          onPick={setCraft}
        />
        <NumberField
          label='Level of that craft (0–20)'
          aria='New material level'
          value={level}
          max={MAX_LEVEL}
          onChange={setLevel}
        />
        <EntityChoice
          label='Set a vein in'
          types={LAND_TYPES}
          worldId={worldId}
          value={vein}
          blocked={gate}
          placeholder='Nowhere yet'
          onChange={setVein}
        />
      </div>
      <NoteField
        label='Description'
        value={description}
        placeholder='What it looks like and what the peoples say of it'
        onChange={setDescription}
      />
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => forge.mutate(undefined)}
      >
        <Sparkles />
        Forge it
      </Button>
    </div>
  )
}

export function DepositForge({
  worldId,
  onDone,
}: {
  worldId: number
  onDone?: () => void
}) {
  const [place, setPlace] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [commodity, setCommodity] = useState<string>('ore')
  const [material, setMaterial] = useState<string>(NONE)
  const [reserve, setReserve] = useState('1000')
  const [richness, setRichness] = useState('50')
  const [quality, setQuality] = useState('50')
  const [revealed, setRevealed] = useState(true)
  const [craft, setCraft] = useState<string>(NONE)
  const [level, setLevel] = useState('0')
  const create = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/resource:create', {
          body: {
            place_id: Number(place),
            name: name.trim(),
            commodity: commodity as CommodityKind,
            ...materialRef(material),
            reserve: whole(reserve),
            richness: whole(richness, PERCENT, 1),
            quality: whole(quality, PERCENT),
            revealed,
            required_branch: craft === NONE ? null : (craft as KnowledgeBranch),
            required_level: whole(level, MAX_LEVEL),
          },
        })
      ),
    onDone: () => {
      setName('')
      onDone?.()
    },
  })
  const gate = useBusy(null, create.isPending)
  const busy =
    gate ??
    (place === null
      ? 'Choose where the deposit lies first.'
      : name.trim()
        ? null
        : 'Give the deposit a name first.')
  return (
    <div data-surface='DepositForge' className={FORM_CARD}>
      <PartHeader
        icon={Pickaxe}
        title='Set a new deposit'
        note='Lay a seam, a grove or a fishing ground into a land. Peoples who know the craft begin to work it.'
      />
      <div className={cn(FIELD_GRID, '@md/form:grid-cols-3')}>
        <EntityChoice
          label='Where it lies'
          types={DEPOSIT_TYPES}
          worldId={worldId}
          value={place}
          blocked={gate}
          placeholder='Choose a land or settlement'
          onChange={setPlace}
        />
        <TextField
          label='Deposit name'
          value={name}
          placeholder='The Red Seam'
          onChange={setName}
        />
        <ChoiceSelect
          label='It yields'
          value={commodity}
          table={COMMODITY_CHOICES}
          blocked={gate}
          onPick={setCommodity}
        />
        <MaterialSelect
          label='Of the material'
          worldId={worldId}
          value={material}
          blocked={gate}
          none='No particular material'
          onPick={setMaterial}
        />
        <NumberField
          label='Reserve'
          aria='Deposit reserve'
          value={reserve}
          onChange={setReserve}
        />
        <NumberField
          label='Richness (1–100)'
          aria='Deposit richness'
          value={richness}
          min={1}
          max={PERCENT}
          onChange={setRichness}
        />
        <NumberField
          label='Quality (0–100)'
          aria='Deposit quality'
          value={quality}
          max={PERCENT}
          onChange={setQuality}
        />
        <ChoiceSelect
          label='Craft to work it'
          value={craft}
          table={branchChoices('Anyone can work it')}
          blocked={gate}
          onPick={setCraft}
        />
        <NumberField
          label='Level of that craft (0–20)'
          aria='Deposit level'
          value={level}
          max={MAX_LEVEL}
          onChange={setLevel}
        />
      </div>
      <SwitchRow
        label='Known to the peoples'
        checked={revealed}
        disabled={gate !== null}
        onChange={setRevealed}
      />
      <Button
        size='sm'
        className='self-start'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => create.mutate(undefined)}
      >
        <Plus />
        Set the deposit
      </Button>
    </div>
  )
}

export function MaterialsBrowser({ worldId }: { worldId: number }) {
  const view = useWorldMaterials(worldId)
  const [family, setFamily] = useState<string>(ALL)
  if (!view.data) return <LoadingBlock label='Loading the materials' />
  const materials = view.data.materials
  const shown =
    family === ALL
      ? materials
      : materials.filter((item) => item.family === family)
  return (
    <div
      data-surface='MaterialsBrowser'
      className='flex min-w-0 flex-col gap-4'
    >
      <PartHeader
        icon={Gem}
        title='Materials of this world'
        note='Edge and hardness cut, toughness and hardness protect, weight slows armies and burns them in heat, conductivity holds enchantment, sanctity and corruption draw gods and outer beings, decay wears things away.'
      />
      <div className='flex min-w-0 flex-wrap items-start gap-2'>
        <Opener icon={Hammer} label='Forge a new material'>
          {(close) => (
            <MaterialForge
              worldId={worldId}
              materials={materials}
              onDone={close}
            />
          )}
        </Opener>
        <Opener icon={Pickaxe} label='Set a deposit'>
          {(close) => <DepositForge worldId={worldId} onDone={close} />}
        </Opener>
      </div>
      <ToggleGroup
        type='single'
        variant='outline'
        size='sm'
        value={family}
        onValueChange={(next) => setFamily(next || ALL)}
        aria-label='Material family'
      >
        <ToggleGroupItem value={ALL}>
          <Gem />
          {`All ${materials.length}`}
        </ToggleGroupItem>
        {MATERIAL_FAMILIES.map((key) => {
          const spec = MATERIAL_FAMILY[key]
          const count = materials.filter((item) => item.family === key).length
          return (
            <ToggleGroupItem key={key} value={key} disabled={count === 0}>
              <spec.icon />
              {`${spec.label} ${count}`}
            </ToggleGroupItem>
          )
        })}
      </ToggleGroup>
      <PagedList
        items={shown}
        initial={PAGE}
        step={PAGE}
        noun={['material', 'materials']}
        className='grid min-w-0 grid-cols-1 gap-3 @4xl/eco:grid-cols-2'
        itemKey={(material) =>
          `${material.kind ?? ''}-${material.world_material_id ?? ''}`
        }
      >
        {(material) => (
          <MaterialCard
            key={`${material.held}-${material.edited}-${material.label}`}
            worldId={worldId}
            material={material}
          />
        )}
      </PagedList>
      <PartHeader
        icon={Coins}
        title='Goods'
        note='What each good is worth before markets move it, how much it feeds, whether war needs it, and how much of it a thousand people use each epoch.'
      />
      <PagedList
        items={[...view.data.commodities]}
        initial={12}
        noun={['good', 'goods']}
        className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3'
        itemKey={(good) => good.kind}
      >
        {(good) => (
          <div className='flex min-w-0 flex-col gap-1 rounded-lg border bg-background p-2'>
            <div className='flex min-w-0 items-center justify-between gap-2'>
              <Text as='span' weight='semibold' truncate>
                {good.label}
              </Text>
              {good.strategic && (
                <Badge size='sm' variant='warning'>
                  Strategic
                </Badge>
              )}
            </div>
            <Muted as='span' variant='caption'>
              {`Worth ${good.base_price} · feeds ${good.nourishment} · ${good.per_1000} used by a thousand each epoch`}
            </Muted>
          </div>
        )}
      </PagedList>
    </div>
  )
}
