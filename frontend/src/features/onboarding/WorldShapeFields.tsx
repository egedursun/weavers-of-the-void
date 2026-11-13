import { type ReactNode, useId } from 'react'
import {
  Cloudy,
  Droplets,
  Globe,
  Hourglass,
  Layers,
  type LucideIcon,
  Mountain,
  Sparkles,
  Thermometer,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Label as FieldLabel } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { RangeField } from '@/components/domain'
import { Medallion } from '@/components/domain/KpiTile'
import {
  type Choice,
  ChoiceTiles,
  SettingGroup,
} from '@/components/domain/SettingsKit'
import { Muted, Text } from '@/components/typography'
import {
  type ClimateEra,
  type CosmosShape,
  type CosmosSize,
  type DimensionKind,
  type WorldAge,
  type WorldType,
} from './api'
import {
  MOISTURE_MIN,
  PERCENT_MAX,
  effectiveShape,
  landShaped,
  layerBlocked,
  shapeBlocked,
  shapeLand,
} from './wizardModel'
import { type StepProps } from './wizardTypes'
import {
  AGE_ICON,
  CLIMATE_ICON,
  COSMOS_ICON,
  SHAPE_ICON,
} from './wizardVisuals'

const SEED_DECIDES = 'seed'
const SEED_LABEL = 'The seed decides'

type Option<T extends string> = {
  value: T
  label: string
  description?: string
  icon?: LucideIcon
}

function SeedField<T extends string>({
  icon,
  label,
  value,
  options,
  blocked = null,
  quiet = false,
  onChange,
}: {
  icon: LucideIcon
  label: string
  value: T | null
  options: Option<T>[]
  blocked?: string | null
  quiet?: boolean
  onChange: (value: T | null) => void
}) {
  const id = useId()
  const noteId = useId()
  const chosen = options.find((option) => option.value === value)
  const note = blocked ?? chosen?.description ?? null
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <FieldLabel htmlFor={id} className={cn(quiet && 'sr-only')}>
        {label}
      </FieldLabel>
      <Select
        value={value ?? SEED_DECIDES}
        onValueChange={(next) =>
          onChange(next === SEED_DECIDES ? null : (next as T))
        }
        disabled={blocked !== null}
      >
        <SelectTrigger
          id={id}
          aria-label={label}
          aria-describedby={note ? noteId : undefined}
          className='w-full'
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={SEED_DECIDES}>
            <Sparkles aria-hidden='true' />
            {SEED_LABEL}
          </SelectItem>
          {options.map((option) => {
            const Icon = option.icon ?? icon
            return (
              <SelectItem key={option.value} value={option.value}>
                <Icon aria-hidden='true' />
                {option.label}
              </SelectItem>
            )
          })}
        </SelectContent>
      </Select>
      {note && (
        <Text
          id={noteId}
          as='p'
          variant='caption'
          tone={blocked === null ? 'primary' : 'muted'}
        >
          {note}
        </Text>
      )}
    </div>
  )
}

function Part({
  icon,
  title,
  hint,
  action,
  children,
}: {
  icon: LucideIcon
  title: string
  hint: string
  action?: ReactNode
  children?: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <Medallion icon={icon} tone='gold' size='sm' />
        <div className='flex min-w-0 flex-1 basis-48 flex-col gap-0.5'>
          <Text as='span' weight='semibold'>
            {title}
          </Text>
          <Muted variant='caption'>{hint}</Muted>
        </div>
        {action}
      </div>
      {children}
    </div>
  )
}

function Step({
  number,
  title,
  hint,
  blocked = null,
  children,
}: {
  number: number
  title: string
  hint: string
  blocked?: string | null
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='flex min-w-0 items-start gap-3'>
        <span
          aria-hidden='true'
          className={cn(
            'flex size-control-sm shrink-0 items-center justify-center rounded-full border',
            blocked === null
              ? 'border-primary/50 bg-primary/10 text-primary'
              : 'border-border bg-muted text-muted-foreground'
          )}
        >
          <Text as='span' variant='caption' weight='semibold' tone='inherit'>
            {number}
          </Text>
        </span>
        <div className='flex min-w-0 flex-col gap-0.5'>
          <Text as='span' weight='semibold'>
            {title}
          </Text>
          <Muted variant='caption'>{blocked ?? hint}</Muted>
        </div>
      </div>
      {children}
    </div>
  )
}

function moistureLevel(value: number): string {
  if (value <= -50) return 'Parched'
  if (value < 0) return 'Dry'
  if (value === 0) return 'Middling'
  if (value < 50) return 'Damp'
  return 'Soaked'
}

function shareLevel(value: number): string {
  if (value < 20) return 'Scarce'
  if (value < 40) return 'Some'
  if (value < 60) return 'Half'
  if (value < 80) return 'Most'
  return 'Nearly all'
}

export function FirstWorldFields({ draft, update, options }: StepProps) {
  const shaped = landShaped(draft)
  const kinds: Option<WorldType>[] = options.world_types.map((option) => ({
    value: option.world_type,
    label: option.label,
    description: option.description,
  }))
  const climates: Option<ClimateEra>[] = options.climate_eras.map((option) => ({
    value: option.era,
    label: option.label,
    description: option.description,
    icon: CLIMATE_ICON[option.era],
  }))
  const ages: Option<WorldAge>[] = Object.entries(options.world_ages).map(
    ([key, label]) => ({
      value: key as WorldAge,
      label,
      icon: AGE_ICON[key as WorldAge] ?? Hourglass,
    })
  )
  return (
    <SettingGroup
      label='The first world'
      description='Its kind, its land, its climate and its age. Each is left to the seed unless you fix it, and every value can be changed later in the world drawer.'
    >
      <div className='flex min-w-0 flex-col gap-5 rounded-xl border bg-muted/20 p-4'>
        <Part
          icon={Globe}
          title='Its kind'
          hint='What sort of world it is: its ground, sky and nature.'
        >
          <SeedField
            icon={Globe}
            label='Kind of the first world'
            quiet
            value={draft.worldType}
            options={kinds}
            onChange={(worldType) => update({ worldType })}
          />
        </Part>
        <Separator />
        <Part
          icon={Mountain}
          title='Its land'
          hint={
            shaped
              ? 'Water, high ground and moisture as you set them.'
              : 'The seed shapes the land: its water, high ground and moisture.'
          }
          action={
            <label className='flex items-center gap-2'>
              <Text as='span' variant='caption' tone='muted'>
                Shape it yourself
              </Text>
              <Switch
                aria-label='Shape the land yourself'
                checked={shaped}
                onCheckedChange={(on) => update(shapeLand(draft, on))}
              />
            </label>
          }
        >
          {shaped && (
            <div className='flex min-w-0 flex-col gap-3'>
              <RangeField
                label='Water'
                icon={Droplets}
                hint='Share of the surface under water'
                value={draft.seaPct ?? 0}
                min={0}
                max={PERCENT_MAX}
                level={shareLevel(draft.seaPct ?? 0)}
                lowLabel='Dry world'
                highLabel='All water'
                onChange={(seaPct) => update({ seaPct })}
              />
              <RangeField
                label='High ground'
                icon={Mountain}
                hint='Share of the land that rises high'
                value={draft.mountainsPct ?? 0}
                min={0}
                max={PERCENT_MAX}
                level={shareLevel(draft.mountainsPct ?? 0)}
                lowLabel='Flat'
                highLabel='All peaks'
                onChange={(mountainsPct) => update({ mountainsPct })}
              />
              <RangeField
                label='Moisture'
                icon={Cloudy}
                hint='How wet the land is'
                value={draft.moisturePct ?? 0}
                min={MOISTURE_MIN}
                max={PERCENT_MAX}
                level={moistureLevel(draft.moisturePct ?? 0)}
                lowLabel='Parched'
                highLabel='Soaked'
                onChange={(moisturePct) => update({ moisturePct })}
              />
            </div>
          )}
        </Part>
        <Separator />
        <Part
          icon={Thermometer}
          title='Its climate and age'
          hint='The climate it begins in and how old it already is when time begins.'
        >
          <div className='grid min-w-0 grid-cols-1 gap-4 md:grid-cols-2'>
            <SeedField
              icon={Thermometer}
              label='Climate age'
              value={draft.climateEra}
              options={climates}
              onChange={(climateEra) => update({ climateEra })}
            />
            <SeedField
              icon={Hourglass}
              label='Age at the first epoch'
              value={draft.worldAge}
              options={ages}
              onChange={(worldAge) => update({ worldAge })}
            />
          </div>
        </Part>
      </div>
    </SettingGroup>
  )
}

export function CosmosFields({ draft, update, options }: StepProps) {
  const sizes: Choice<CosmosSize>[] = options.cosmos.map((option) => ({
    value: option.size,
    label: option.label,
    hint: `${option.worlds} ${option.worlds === 1 ? 'world' : 'worlds'} under the sky`,
    icon: COSMOS_ICON[option.size] ?? Sparkles,
  }))
  const shapes: Choice<CosmosShape>[] = options.shapes.map((option) => ({
    value: option.shape,
    label: option.label,
    hint: option.hint,
    icon: SHAPE_ICON[option.shape] ?? Sparkles,
  }))
  const layers: Option<DimensionKind>[] = options.layer_kinds.map((option) => ({
    value: option.kind,
    label: option.label,
    description: option.description,
  }))
  const blocked = shapeBlocked(draft)
  return (
    <SettingGroup
      label='Cosmos'
      description='Two choices: how many worlds the cosmos begins with, and where the worlds beyond the first one lie.'
    >
      <div className='flex min-w-0 flex-col gap-5 rounded-xl border bg-muted/20 p-4'>
        <Step
          number={1}
          title='How many worlds'
          hint='Choose one. The first world is always made; the others wait beside it.'
        >
          <ChoiceTiles
            label='How many worlds'
            value={draft.cosmos}
            options={sizes}
            onChange={(cosmos) => update({ cosmos })}
          />
        </Step>
        <Separator />
        <Step
          number={2}
          title='Where the further worlds lie'
          hint='Choose one for the worlds beyond the first.'
          blocked={blocked}
        >
          <ChoiceTiles
            label='Where the further worlds lie'
            value={effectiveShape(draft)}
            options={shapes}
            blocked={blocked}
            onChange={(shape) => update({ shape })}
          />
          <div className='flex min-w-0 flex-col gap-1 border-l-2 border-primary/30 pl-4'>
            <Muted variant='caption'>
              Only for a layered cosmos: what kind of layer of reality lies
              beside the first world.
            </Muted>
            <SeedField
              icon={Layers}
              label='Second layer'
              value={draft.layerKind}
              options={layers}
              blocked={layerBlocked(draft)}
              onChange={(layerKind) => update({ layerKind })}
            />
          </div>
        </Step>
      </div>
    </SettingGroup>
  )
}
