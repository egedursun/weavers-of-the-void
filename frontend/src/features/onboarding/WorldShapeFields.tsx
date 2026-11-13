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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RangeField } from '@/components/domain'
import {
  type Choice,
  ChoiceTiles,
  SettingGroup,
  SettingRow,
  SwitchRow,
} from '@/components/domain/SettingsKit'
import { Muted } from '@/components/typography'
import {
  type ClimateEra,
  type CosmosShape,
  type DimensionKind,
  type WorldAge,
  type WorldType,
} from './api'
import {
  MOISTURE_MIN,
  PERCENT_MAX,
  landShaped,
  layerBlocked,
  shapeBlocked,
  shapeLand,
} from './wizardModel'
import { type StepProps } from './wizardTypes'
import { AGE_ICON, CLIMATE_ICON, SHAPE_ICON } from './wizardVisuals'

const SEED_DECIDES = 'seed'
const SEED_LABEL = 'The seed decides'
const LAND_HELD =
  'The seed shapes the land; turn on "Shape the land yourself" to set it.'

type Option<T extends string> = {
  value: T
  label: string
  description?: string
  icon?: LucideIcon
}

function SeedSelect<T extends string>({
  icon,
  label,
  description,
  value,
  options,
  blocked = null,
  onChange,
}: {
  icon: LucideIcon
  label: string
  description: string
  value: T | null
  options: Option<T>[]
  blocked?: string | null
  onChange: (value: T | null) => void
}) {
  const chosen = options.find((option) => option.value === value)
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <SettingRow
        icon={icon}
        label={label}
        description={description}
        active={blocked === null}
      >
        {(id) => (
          <Select
            value={value ?? SEED_DECIDES}
            onValueChange={(next) =>
              onChange(next === SEED_DECIDES ? null : (next as T))
            }
            disabled={blocked !== null}
          >
            <SelectTrigger id={id} aria-label={label} className='w-full'>
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
        )}
      </SettingRow>
      {blocked !== null ? (
        <Muted variant='caption'>{blocked}</Muted>
      ) : (
        chosen?.description && (
          <Muted variant='caption'>{chosen.description}</Muted>
        )
      )}
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
  const held = shaped ? null : LAND_HELD
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
      description='Leave any of these to the seed, or fix them yourself. Every value can be changed later in the world drawer.'
    >
      <SeedSelect
        icon={Globe}
        label='Kind of the first world'
        description='What sort of world it is: its ground, sky and nature.'
        value={draft.worldType}
        options={kinds}
        onChange={(worldType) => update({ worldType })}
      />
      <SwitchRow
        icon={Mountain}
        label='Shape the land yourself'
        description='Set how much water, high ground and moisture the first world has.'
        checked={shaped}
        onChange={(on) => update(shapeLand(draft, on))}
      />
      <div className='flex min-w-0 flex-col gap-3'>
        <RangeField
          label='Water'
          icon={Droplets}
          hint='Share of the surface under water'
          value={draft.seaPct ?? 0}
          min={0}
          max={PERCENT_MAX}
          level={shaped ? shareLevel(draft.seaPct ?? 0) : SEED_LABEL}
          lowLabel='Dry world'
          highLabel='All water'
          disabledReason={held}
          onChange={(seaPct) => update({ seaPct })}
        />
        <RangeField
          label='High ground'
          icon={Mountain}
          hint='Share of the land that rises high'
          value={draft.mountainsPct ?? 0}
          min={0}
          max={PERCENT_MAX}
          level={shaped ? shareLevel(draft.mountainsPct ?? 0) : SEED_LABEL}
          lowLabel='Flat'
          highLabel='All peaks'
          disabledReason={held}
          onChange={(mountainsPct) => update({ mountainsPct })}
        />
        <RangeField
          label='Moisture'
          icon={Cloudy}
          hint='How wet the land is'
          value={draft.moisturePct ?? 0}
          min={MOISTURE_MIN}
          max={PERCENT_MAX}
          level={shaped ? moistureLevel(draft.moisturePct ?? 0) : SEED_LABEL}
          lowLabel='Parched'
          highLabel='Soaked'
          disabledReason={held}
          onChange={(moisturePct) => update({ moisturePct })}
        />
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
        <SeedSelect
          icon={Thermometer}
          label='Climate age'
          description='The climate the first world begins in.'
          value={draft.climateEra}
          options={climates}
          onChange={(climateEra) => update({ climateEra })}
        />
        <SeedSelect
          icon={Hourglass}
          label='Age at the first epoch'
          description='How old the world already is when time begins.'
          value={draft.worldAge}
          options={ages}
          onChange={(worldAge) => update({ worldAge })}
        />
      </div>
    </SettingGroup>
  )
}

export function CosmosShapeFields({ draft, update, options }: StepProps) {
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
    <div className='flex min-w-0 flex-col gap-3'>
      <ChoiceTiles
        label='Shape of the cosmos'
        value={draft.cosmos === 'single' ? 'one_sun' : draft.shape}
        options={shapes}
        blocked={blocked}
        onChange={(shape) => update({ shape })}
      />
      {blocked !== null && <Muted variant='caption'>{blocked}</Muted>}
      <SeedSelect
        icon={Layers}
        label='Second layer'
        description='What kind of layer of reality lies beside the first world.'
        value={draft.layerKind}
        options={layers}
        blocked={layerBlocked(draft)}
        onChange={(layerKind) => update({ layerKind })}
      />
    </div>
  )
}
