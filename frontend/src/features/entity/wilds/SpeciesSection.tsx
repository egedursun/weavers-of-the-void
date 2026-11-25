import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import {
  ArrowRight,
  Ban,
  Biohazard,
  Check,
  Compass,
  Crosshair,
  Dna,
  Footprints,
  GitBranch,
  HeartPulse,
  Leaf,
  MapPin,
  MapPinned,
  Moon,
  Mountain,
  Package,
  Pin,
  Plus,
  ShieldAlert,
  Sparkles,
  Sprout,
  Sun,
  Thermometer,
  Trash2,
  TriangleAlert,
  Unlock,
  Wheat,
  type LucideIcon,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  bodyPlanValues,
  commodityKindValues,
  dietValues,
  domesticationStageValues,
  materialKindValues,
  rangeTrendValues,
  sizeClassValues,
  socialityValues,
  animalRoleValues,
} from '@/api/generated/schema'
import { type ActProp } from '@/api/mutation'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  EmptyState,
  KpiTile,
  Medallion,
  MiniStat,
  Section,
  StatBar,
  Paged,
  LoadingBlock,
  FieldTile,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { type Named } from '@/features/entity/economy/labels'
import { ChoiceSelect } from '@/features/entity/economy/parts'
import { useKinds } from '@/features/kinds/api'
import { speciesRangeSearch } from '@/features/map/speciesRange'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { useSons } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { PLANS } from '../body/labels'
import { useWorldMaterials } from '../economy/api'
import { COMMODITY } from '../economy/labels'
import { TERRAIN } from '../environment/labels'
import { PERCENT, busyOf } from '../lore/model'
import { MindPicker } from '../mind/parts'
import { AnatomyCard } from './AnatomySection'
import { FloraCard, FloraControls } from './FloraPanels'
import {
  CustomUseBadges,
  FoodLinkControls,
  HerdDrop,
  HostControls,
  KeepingControls,
  WorldMaterialBadge,
} from './WildControls'
import { type SpeciesCard, useSpecies, useSpeciesEdit } from './api'
import {
  BADGE_OF,
  DIET,
  ECOLOGY_ICON,
  LIFE_ICONS,
  MATERIAL,
  SIZE,
  SIZE_STEPS,
  SOCIALITY,
  STAGE,
  TEMPERAMENT,
  TRAIT,
  TREND,
  USE,
  barTone,
  fieldLabel,
  named,
  plain,
  titled,
  PRODUCT_PARTS,
  type ProductPart,
} from './labels'
import {
  AdjustPanel,
  Card,
  Group,
  Held,
  Name,
  NumberField,
  RangeTrack,
  SwitchField,
  ShareEditor,
  StageTrack,
  Tile,
  TileGrid,
} from './parts'

type Range = SpeciesCard['ranges'][number]
type Blocked = { id: number; card: SpeciesCard; blocked: string | null }

const COMMUNITIES = ['settlement', 'people', 'faction', 'cult'] as const
const SEED_ABUNDANCE = 10
const LAND_SCALE = 100
const TERRAINS = Object.fromEntries(
  Object.entries(TERRAIN).filter(
    ([key]) => !['urban', 'ruin_field'].includes(key)
  )
)
const PLAN_NAMES = Object.fromEntries(
  bodyPlanValues.map((key) => [key, named(PLANS, key).label])
)

function edit(id: number, key: string, value: number) {
  return unwrap(
    api.POST('/api/actions/species:edit', {
      body: {
        species_id: id,
        values: { [key]: value } as Record<string, never>,
        release: [],
      },
    })
  )
}

function field(key: string, value: number, min: number, max?: number) {
  return { key, label: fieldLabel(key), value, min, max }
}

function speciesGroups(card: SpeciesCard): AdjustGroup[] {
  return [
    {
      title: 'Life cycle',
      fields: [
        field('lifespan_years', card.lifespan_years, 1),
        field('maturity_years', card.maturity_years, 0),
        field('litter_size', card.litter_size, 1),
        field('breeding_seasons', card.breeding_seasons, 0),
        field('metabolism', card.metabolism, 0, PERCENT),
        field('water_need', card.water_need, 0, PERCENT),
      ],
    },
    {
      title: 'Temperament',
      fields: [
        ...TEMPERAMENT.map((item) =>
          field(item.key, card[item.key], 0, PERCENT)
        ),
        field('tameability', card.tameability, 0, PERCENT),
      ],
    },
    {
      title: 'Climate it bears',
      fields: [
        field('temperature_min', card.temperature_min, -PERCENT),
        field('temperature_max', card.temperature_max, -PERCENT),
        field('altitude_min', card.altitude_min, 0),
        field('altitude_max', card.altitude_max, 0),
      ],
    },
  ]
}

function Hero({ card }: { card: SpeciesCard }) {
  const plan = named(PLANS, card.body_plan)
  const size = named(SIZE, card.size_class)
  const diet = named(DIET, card.diet)
  const social = named(SOCIALITY, card.sociality)
  const stage = named(STAGE, card.stage)
  return (
    <div className='flex min-w-0 items-center gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <Medallion icon={plan.icon} tone={plan.tone ?? 'gold'} />
      <div className='flex min-w-0 flex-1 flex-col gap-1.5'>
        <Text weight='semibold'>{`${size.label} ${plan.label.toLowerCase()} creature`}</Text>
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Badge size='sm' variant='secondary'>
            <diet.icon />
            {diet.label}
          </Badge>
          <Badge size='sm' variant='secondary'>
            <social.icon />
            {social.label}
          </Badge>
          <Badge size='sm' variant={card.nocturnal ? 'info' : 'warning'}>
            {card.nocturnal ? <Moon /> : <Sun />}
            {card.nocturnal ? 'Active at night' : 'Active by day'}
          </Badge>
          <Badge size='sm' variant={card.migratory ? 'info' : 'secondary'}>
            {card.migratory ? <Compass /> : <MapPin />}
            {card.migratory ? 'Migrates' : 'Stays in its lands'}
          </Badge>
          <Badge
            size='sm'
            variant={card.stage === 'wild' ? 'outline' : 'success'}
          >
            <stage.icon />
            {stage.label}
          </Badge>
          <Badge size='sm' variant='default'>
            <LIFE_ICONS.herd />
            {`${card.abundance} strong in all its lands`}
          </Badge>
        </div>
        {card.migration_path.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Muted as='span' variant='caption'>
              Migrates through
            </Muted>
            <Paged items={card.migration_path}>
              {(land) => <Name key={land.id} item={land} />}
            </Paged>
          </div>
        )}
        {card.totem_of.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Muted as='span' variant='caption'>
              Totem of
            </Muted>
            <Paged items={card.totem_of}>
              {(people) => <Name key={people.id} item={people} />}
            </Paged>
          </div>
        )}
        {(card.sacred_to || card.domesticated_from) && (
          <div className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1'>
            {card.sacred_to && (
              <span className='flex min-w-0 items-center gap-1.5'>
                <Sparkles
                  aria-hidden='true'
                  className='size-icon-xs text-primary'
                />
                <Muted as='span' variant='caption'>
                  Sacred to
                </Muted>
                <Name item={card.sacred_to} />
              </span>
            )}
            {card.domesticated_from && (
              <span className='flex min-w-0 items-center gap-1.5'>
                <Dna aria-hidden='true' className='size-icon-xs text-primary' />
                <Muted as='span' variant='caption'>
                  Bred from
                </Muted>
                <Name item={card.domesticated_from} />
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Vitals({ card }: { card: SpeciesCard }) {
  const size = named(SIZE, card.size_class)
  const diet = named(DIET, card.diet)
  const top = card.ranges[0]
  const total = card.ranges.reduce((sum, row) => sum + row.abundance, 0)
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 @xs/wild:grid-cols-2 @lg/wild:grid-cols-4'>
      <KpiTile
        label='Size'
        value={size.label}
        icon={size.icon}
        tone={size.tone ?? 'gold'}
        hint={SIZE[card.size_class]?.hint}
        meter={{
          value: SIZE[card.size_class]?.rank ?? 1,
          max: SIZE_STEPS,
          label: 'Size class',
        }}
      />
      <KpiTile
        label='Diet'
        value={diet.label}
        icon={diet.icon}
        tone={diet.tone ?? 'gold'}
        hint={`Hunts ${card.hunts.length}, hunted by ${card.hunted_by.length}`}
      />
      <KpiTile
        label='Lands'
        value={card.ranges.length}
        icon={MapPinned}
        tone='info'
        hint={
          top?.region
            ? `Most at ${top.region.name}, ${total} abundance in all`
            : 'It ranges nowhere yet'
        }
      />
      <KpiTile
        label='Tameability'
        value={`${card.tameability}%`}
        icon={STAGE.tamed.icon}
        tone='success'
        hint='How readily people can keep it'
        meter={{
          value: card.tameability,
          max: PERCENT,
          label: 'Tameability',
        }}
      />
    </div>
  )
}

function Temperament({ card }: { card: SpeciesCard }) {
  return (
    <Card title='Temperament' icon={ShieldAlert} tone='danger'>
      {TEMPERAMENT.map((item) => (
        <StatBar
          key={item.key}
          label={item.label}
          value={card[item.key]}
          max={PERCENT}
          icon={item.icon}
          tone={item.tone}
        />
      ))}
      <StatBar
        label='Tameability'
        value={card.tameability}
        max={PERCENT}
        icon={STAGE.tamed.icon}
        tone='success'
      />
    </Card>
  )
}

function LifeCycle({ card }: { card: SpeciesCard }) {
  return (
    <Card title='Life cycle' icon={HeartPulse} tone='success'>
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <MiniStat
          icon={LIFE_ICONS.lifespan}
          label='Years of life'
          value={card.lifespan_years}
          tone='gold'
        />
        <MiniStat
          icon={LIFE_ICONS.maturity}
          label='Years to grow'
          value={card.maturity_years}
          tone='success'
        />
        <MiniStat
          icon={LIFE_ICONS.litter}
          label='Young per litter'
          value={card.litter_size}
          tone='info'
        />
        <MiniStat
          icon={LIFE_ICONS.seasons}
          label='Litters a year'
          value={card.breeding_seasons}
          tone='verdigris'
        />
      </div>
      <StatBar
        framed
        label='Metabolism'
        value={card.metabolism}
        max={PERCENT}
        icon={LIFE_ICONS.metabolism}
        tone='warning'
      />
      <StatBar
        framed
        label='Water need'
        value={card.water_need}
        max={PERCENT}
        icon={LIFE_ICONS.water}
        tone='info'
      />
    </Card>
  )
}

function Climate({ card }: { card: SpeciesCard }) {
  const floor = Math.min(0, card.temperature_min)
  const ceiling = Math.max(LAND_SCALE, card.temperature_max)
  return (
    <Card
      title='Climate it bears'
      icon={Thermometer}
      tone='info'
      hint='Land scale: 0 frozen, 100 scorching'
    >
      <RangeTrack
        label='Warmth'
        icon={Thermometer}
        low={card.temperature_min}
        high={card.temperature_max}
        floor={floor}
        ceiling={ceiling}
        tone='warning'
        scale='cold to hot'
      />
      <RangeTrack
        label='Height of the ground'
        icon={Mountain}
        low={card.altitude_min}
        high={card.altitude_max}
        floor={0}
        ceiling={Math.max(LAND_SCALE, card.altitude_max)}
        tone='verdigris'
        scale='lowland to peak'
      />
      <Habitat card={card} />
    </Card>
  )
}

function Habitat({ card }: { card: SpeciesCard }) {
  const rows = Object.entries(card.habitat).sort(([, a], [, b]) => b - a)
  return (
    <div className='flex min-w-0 flex-col gap-2 border-t pt-3'>
      <Label variant='overline'>Lands it loves</Label>
      {rows.length === 0 ? (
        <Muted variant='caption'>It favours no land over another.</Muted>
      ) : (
        rows.map(([key, share]) => {
          const terrain = named(TERRAIN, key)
          return (
            <StatBar
              key={key}
              label={terrain.label}
              value={share}
              max={PERCENT}
              icon={terrain.icon}
              tone='success'
            />
          )
        })
      )}
    </div>
  )
}

function Traits({ card }: { card: SpeciesCard }) {
  return (
    <Card
      title='Gifts and afflictions'
      icon={Sparkles}
      tone='verdigris'
      hint='What sets this kind apart, and the sicknesses it spreads'
      aside={
        <Badge size='sm' variant='secondary'>
          {card.traits.length}
        </Badge>
      }
      wide
    >
      {card.traits.length === 0 ? (
        <Muted>An ordinary kind, with no gift worth naming.</Muted>
      ) : (
        <TileGrid>
          <Paged items={card.traits}>
            {(trait) => <Tile key={trait} spec={named(TRAIT, trait)} />}
          </Paged>
        </TileGrid>
      )}
      {card.hosts.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Sicknesses it carries</Label>
          <div className='flex min-w-0 flex-wrap gap-1.5'>
            <Paged items={card.hosts}>
              {(row) => (
                <Badge
                  key={row.disease?.id}
                  size='sm'
                  variant={row.immune ? 'success' : 'destructive'}
                >
                  <Biohazard />
                  {`${row.disease?.name ?? 'A sickness'}${row.immune ? ', unharmed by it' : ''}`}
                </Badge>
              )}
            </Paged>
          </div>
        </div>
      )}
    </Card>
  )
}

function Kin({
  title,
  icon: Icon,
  items,
  empty,
}: {
  title: string
  icon: LucideIcon
  items: SpeciesCard['hunts']
  empty: string
}) {
  return (
    <div className='flex min-w-0 flex-col gap-1.5 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <div className='flex min-w-0 items-center gap-1.5'>
        <Icon
          aria-hidden='true'
          className='size-icon-xs shrink-0 text-muted-foreground'
        />
        <Label truncate className='flex-1'>
          {title}
        </Label>
        <Muted as='span' variant='caption'>
          {items.length}
        </Muted>
      </div>
      {items.length === 0 ? (
        <Muted variant='caption'>{empty}</Muted>
      ) : (
        <div className='flex min-w-0 flex-wrap gap-x-3 gap-y-1'>
          <Paged items={items}>
            {(item) => <Name key={item.id} item={item} />}
          </Paged>
        </div>
      )}
    </div>
  )
}

function FoodChain({ card }: { card: SpeciesCard }) {
  return (
    <Card
      title='Food chain and kin'
      icon={Crosshair}
      tone='danger'
      hint='Who it eats, who eats it, and what came of it'
      wide
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/card:grid-cols-2'>
        <Kin
          title='Hunts'
          icon={Crosshair}
          items={card.hunts}
          empty='It preys on no kind.'
        />
        <Kin
          title='Hunted by'
          icon={ShieldAlert}
          items={card.hunted_by}
          empty='No kind preys on it.'
        />
        {(card.pinned_prey.length > 0 || card.barred_prey.length > 0) && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5 @md/card:col-span-2'>
            <Paged items={card.pinned_prey}>
              {(item) => (
                <Badge key={`pin-${item.id}`} variant='default'>
                  <Pin />
                  {`Always hunts ${item.name}`}
                </Badge>
              )}
            </Paged>
            <Paged items={card.barred_prey}>
              {(item) => (
                <Badge key={`bar-${item.id}`} variant='destructive'>
                  <Ban />
                  {`Never hunts ${item.name}`}
                </Badge>
              )}
            </Paged>
          </div>
        )}
        <Kin
          title='Gave rise to'
          icon={GitBranch}
          items={card.descendants}
          empty='No kind has sprung from it.'
        />
        <Kin
          title='Its great beasts'
          icon={Footprints}
          items={card.beasts}
          empty='None of its kind has grown into a legend.'
        />
      </div>
    </Card>
  )
}

function UsesAndYields({ card }: { card: SpeciesCard }) {
  return (
    <Card
      title='Uses and yields'
      icon={Package}
      tone='gold'
      hint={`Kept for ${card.uses.length} of ${plural(animalRoleValues.length, 'use', 'uses')}; yields are per head each epoch`}
      wide
    >
      <div
        data-surface='SpeciesUses'
        className='flex min-w-0 flex-wrap gap-1.5'
      >
        {animalRoleValues.map((use) => {
          const spec = named(USE, use)
          const held = card.uses.includes(use)
          return (
            <Badge
              key={use}
              variant={held ? BADGE_OF[spec.tone ?? 'gold'] : 'outline'}
              className={held ? undefined : 'border-dashed opacity-50'}
              aria-label={`${spec.label}: ${held ? 'kept for this' : 'not kept for this'}`}
            >
              <spec.icon />
              {spec.label}
            </Badge>
          )
        })}
      </div>
      <CustomUseBadges card={card} />
      {card.yields.length === 0 ? (
        <Muted>Nothing worth taking from it.</Muted>
      ) : (
        <div data-surface='SpeciesYields' className='min-w-0'>
          <TileGrid>
            <Paged items={card.yields}>
              {(row) => {
                const goods = row.commodity ? COMMODITY[row.commodity] : null
                return (
                  <Tile
                    key={row.product}
                    spec={{
                      label: titled(row.product),
                      icon: goods?.icon ?? Package,
                      tone: 'gold',
                    }}
                    caption={[
                      goods?.label,
                      row.material &&
                      plain(MATERIAL, row.material) !== goods?.label
                        ? plain(MATERIAL, row.material)
                        : null,
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                    aside={
                      <span className='flex items-center gap-1'>
                        <WorldMaterialBadge name={row.world_material} />
                        <Badge
                          size='sm'
                          variant='default'
                        >{`×${row.rate}`}</Badge>
                      </span>
                    }
                  />
                )
              }}
            </Paged>
          </TileGrid>
        </div>
      )}
    </Card>
  )
}

function Taming({ id, card, blocked }: Blocked) {
  const heads = card.herds.reduce((sum, row) => sum + row.head, 0)
  return (
    <Card
      title='Taming and herds'
      icon={STAGE.herded.icon}
      tone='verdigris'
      hint={
        card.herds.length > 0
          ? `Kept since epoch ${Math.min(...card.herds.map((row) => row.since_epoch))}`
          : 'No people keeps it yet'
      }
    >
      <StageTrack stage={card.stage} />
      <div className='grid min-w-0 grid-cols-2 gap-2'>
        <MiniStat
          icon={LIFE_ICONS.herd}
          label='Head in herds'
          value={heads}
          tone='verdigris'
        />
        <MiniStat
          icon={STAGE.domesticated.icon}
          label={card.herds.length === 1 ? 'Herder people' : 'Herder peoples'}
          value={card.herds.length}
          tone='success'
        />
      </div>
      {card.herds.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={card.herds} as='li'>
            {(row) => {
              const stage = named(STAGE, row.stage)
              return (
                <li
                  key={row.community?.id}
                  className='flex min-w-0 items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'
                >
                  <Medallion icon={stage.icon} tone={stage.tone} size='sm' />
                  <div className='flex min-w-0 flex-1 flex-col gap-1'>
                    <Name item={row.community} />
                    <div className='flex min-w-0 flex-wrap gap-1'>
                      <Badge size='sm' variant={BADGE_OF[stage.tone ?? 'gold']}>
                        {stage.label}
                      </Badge>
                      <Badge size='sm' variant='secondary'>
                        <LIFE_ICONS.herd />
                        {`${row.head} head`}
                      </Badge>
                      <Badge size='sm' variant='secondary'>
                        <Wheat />
                        {`Fed ${row.fed_epochs} ${row.fed_epochs === 1 ? 'epoch' : 'epochs'}`}
                      </Badge>
                    </div>
                  </div>
                  {row.community && (
                    <HerdDrop
                      communityId={row.community.id}
                      speciesId={id}
                      name={row.community.name}
                      blocked={blocked}
                    />
                  )}
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
    </Card>
  )
}

function RangeCard({ row }: { row: Range }) {
  const trend = named(TREND, row.trend)
  return (
    <li className='flex min-w-0 flex-col gap-2.5 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion icon={MapPin} tone='info' size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Name item={row.region} fallback='A lost land' />
          <Muted as='span' variant='caption' truncate>
            {`Since epoch ${row.since_epoch}`}
          </Muted>
        </div>
        <Badge size='sm' variant={TREND[row.trend]?.badge ?? 'secondary'}>
          <trend.icon />
          {trend.label}
        </Badge>
      </div>
      <StatBar
        label='Abundance'
        value={row.abundance}
        max={PERCENT}
        icon={LIFE_ICONS.herd}
        tone={barTone(row.abundance, 'success')}
      />
      <StatBar
        label='Fit to the land'
        value={row.fit}
        max={PERCENT}
        icon={Leaf}
        tone='verdigris'
      />
      <StatBar
        label='Hunting pressure'
        value={row.hunted}
        max={PERCENT}
        icon={Crosshair}
        tone='destructive'
      />
      {row.locked.length > 0 && (
        <Badge size='sm' variant='default'>
          {`Held: ${row.locked.map(fieldLabel).join(', ').toLowerCase()}`}
        </Badge>
      )}
    </li>
  )
}

function RangeLink({ card }: { card: SpeciesCard }) {
  const navigate = useNavigate()
  return (
    <Button
      size='sm'
      variant='outline'
      onClick={() =>
        void navigate({
          to: '/map',
          search: speciesRangeSearch(card.world_id ?? null, card.species_id),
        })
      }
    >
      <MapPinned />
      Show its range on the map
    </Button>
  )
}

function Ranges({ card }: { card: SpeciesCard }) {
  return (
    <Card
      title='Where it ranges'
      icon={MapPinned}
      tone='info'
      hint='How many live in each land, how well it suits them and how hard they are hunted'
      aside={
        <Badge size='sm' variant='info'>
          {`${card.ranges.length} ${card.ranges.length === 1 ? 'land' : 'lands'}`}
        </Badge>
      }
    >
      {card.ranges.length > 0 && <RangeLink card={card} />}
      {card.ranges.length === 0 ? (
        <EmptyState
          icon={MapPinned}
          title='It ranges nowhere'
          description='Seed it into a land from the controls below.'
        />
      ) : (
        <ul
          data-surface='SpeciesRanges'
          className='grid min-w-0 grid-cols-1 gap-2 @lg/card:grid-cols-2'
        >
          <Paged items={card.ranges} as='li'>
            {(row) => <RangeCard key={row.region?.id} row={row} />}
          </Paged>
        </ul>
      )}
    </Card>
  )
}

function NatureControls({ id, card, blocked }: Blocked) {
  const save = useSpeciesEdit(id)
  const busy = busyOf(blocked, save.isPending)
  const pick = (key: string, value: string | boolean) =>
    save.mutate({ values: { [key]: value } })
  const choices: {
    key: 'size_class' | 'diet' | 'sociality' | 'stage' | 'body_plan'
    table: Record<string, string>
  }[] = [
    { key: 'size_class', table: pickTable(sizeClassValues, SIZE) },
    { key: 'diet', table: pickTable(dietValues, DIET) },
    { key: 'sociality', table: pickTable(socialityValues, SOCIALITY) },
    { key: 'stage', table: pickTable(domesticationStageValues, STAGE) },
    {
      key: 'body_plan',
      table: {
        ...PLAN_NAMES,
        [card.body_plan]: named(PLANS, card.body_plan).label,
      },
    },
  ]
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Group title='Body and habits' icon={HeartPulse}>
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/wild:grid-cols-2 @3xl/wild:grid-cols-3'>
          {choices.map((item) => (
            <MindPicker
              act={save}
              key={item.key}
              label={fieldLabel(item.key)}
              value={String(card[item.key])}
              table={item.table}
              blocked={busy}
              onPick={(value) => pick(item.key, value)}
            />
          ))}
          {(['nocturnal', 'migratory'] as const).map((key) => (
            <SwitchField
              act={save}
              key={key}
              label={fieldLabel(key)}
              checked={card[key]}
              disabled={busy !== null}
              onChange={(next) => pick(key, next)}
            />
          ))}
        </div>
      </Group>
      <AdjustStats
        id={`species-${id}`}
        groups={speciesGroups(card)}
        note='Shares and temperament run from 0 to 100; warmth and height use the land scale.'
        run={({ key, value }) => edit(id, key, value)}
      />
    </div>
  )
}

function pickTable(
  values: readonly string[],
  table: Record<string, { label: string }>
): Record<string, string> {
  return Object.fromEntries(
    values.map((key) => [key, table[key]?.label ?? titled(key)])
  )
}

function RangeEditor({
  id,
  row,
  blocked,
}: {
  id: number
  row: Range
  blocked: string | null
}) {
  const [draft, setDraft] = useState({
    abundance: String(row.abundance),
    fit: String(row.fit),
    hunted: String(row.hunted),
    trend: row.trend as string,
  })
  const region = row.region?.id ?? 0
  const set = useGodAction<{
    values: EditValues
    release?: string[]
  }>({
    writes: [{ lever: 'species:range' }],
    run: ({ values, release }) =>
      unwrap(
        api.POST('/api/actions/species:range', {
          body: {
            species_id: id,
            region_id: region,
            values: values as Record<string, never>,
            release: release ?? [],
          },
        })
      ),
  })
  const drop = useGodAction({
    writes: [{ lever: 'species:drop_range' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/species:drop_range', {
          body: { species_id: id, region_id: region },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending, drop.isPending)
  const whole = (value: string) =>
    Math.max(0, Math.min(PERCENT, Math.round(Number(value) || 0)))
  const changed = Object.fromEntries(
    [
      ['abundance', whole(draft.abundance), row.abundance],
      ['fit', whole(draft.fit), row.fit],
      ['hunted', whole(draft.hunted), row.hunted],
      ['trend', draft.trend, row.trend],
    ]
      .filter(([, next, now]) => next !== now)
      .map(([key, next]) => [key, next])
  )
  const put = (key: keyof typeof draft) => (value: string) =>
    setDraft((before) => ({ ...before, [key]: value }))
  return (
    <li className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <MapPin aria-hidden='true' className='size-icon-sm text-info' />
        <div className='min-w-0 flex-1'>
          <Name item={row.region} fallback='A lost land' />
        </div>
        <Button
          act={set}
          size='sm'
          disabled={busy !== null || Object.keys(changed).length === 0}
          disabledReason={
            busy ??
            (Object.keys(changed).length === 0 ? 'Nothing changed' : undefined)
          }
          onClick={() => set.mutate({ values: changed })}
        >
          <Check />
          Set it so
        </Button>
        {row.locked.length > 0 && (
          <Button
            act={set}
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => set.mutate({ values: {}, release: [...row.locked] })}
          >
            <Unlock />
            Release
          </Button>
        )}
        <Button
          act={drop}
          size='sm'
          variant='ghost'
          aria-label={`Drive it out of ${row.region?.name ?? 'this land'}`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => drop.mutate(undefined)}
        >
          <Trash2 />
          Drive it out
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-2 items-end gap-3 @xl/wild:grid-cols-4'>
        <NumberField
          label='Abundance'
          value={draft.abundance}
          min={0}
          max={PERCENT}
          disabled={busy !== null}
          onChange={put('abundance')}
        />
        <NumberField
          label='Fit to the land'
          value={draft.fit}
          min={0}
          max={PERCENT}
          disabled={busy !== null}
          onChange={put('fit')}
        />
        <NumberField
          label='Hunting pressure'
          value={draft.hunted}
          min={0}
          max={PERCENT}
          disabled={busy !== null}
          onChange={put('hunted')}
        />
        <MindPicker
          label='Trend'
          value={draft.trend}
          table={pickTable(rangeTrendValues, TREND)}
          blocked={busy}
          onPick={put('trend')}
        />
      </div>
    </li>
  )
}

function LandControls({ id, card, blocked }: Blocked) {
  const [region, setRegion] = useState<number | null>(null)
  const [target, setTarget] = useState<number | null>(null)
  const save = useSpeciesEdit(id)
  const seed = useGodAction<number>({
    writes: [{ lever: 'species:range' }],
    run: (where) =>
      unwrap(
        api.POST('/api/actions/species:range', {
          body: {
            species_id: id,
            region_id: where,
            values: { abundance: SEED_ABUNDANCE },
          },
        })
      ),
  })
  const move = useGodAction<{ from: number; to: number }>({
    writes: [{ lever: 'species:move_range' }],
    run: ({ from, to }) =>
      unwrap(
        api.POST('/api/actions/species:move_range', {
          body: { species_id: id, source_id: from, target_id: to },
        })
      ),
  })
  const busy = busyOf(blocked, save.isPending, seed.isPending, move.isPending)
  const main = card.ranges[0]?.region
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Group title='Lands it loves' icon={Leaf}>
        <ShareEditor
          act={save}
          key={JSON.stringify(card.habitat)}
          table={TERRAINS}
          value={card.habitat}
          max={PERCENT}
          amount='its liking for that land, from 0 to 100'
          busy={busy}
          addLabel='Add a land'
          onSave={(next) => save.mutate({ values: { habitat: next } })}
        />
      </Group>
      <Group title='Where it ranges' icon={MapPinned}>
        {card.ranges.length === 0 && <Muted>It ranges nowhere yet.</Muted>}
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={card.ranges} as='li'>
            {(row) => (
              <RangeEditor
                key={`${row.region?.id}-${row.abundance}-${row.fit}-${row.hunted}-${row.trend}`}
                id={id}
                row={row}
                blocked={blocked}
              />
            )}
          </Paged>
        </ul>
        <div className='grid min-w-0 grid-cols-1 items-end gap-3 @xl/wild:grid-cols-2'>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label>Seed it into a new land</Label>
            <EntityPicker
              types={['region']}
              value={region}
              onChange={setRegion}
              placeholder='Choose a land…'
            />
            <Button
              act={seed}
              size='sm'
              variant='outline'
              className='self-start'
              disabled={busy !== null || region === null}
              disabledReason={
                busy ?? (region === null ? 'Choose a land' : undefined)
              }
              onClick={() => seed.mutate(region ?? 0)}
            >
              <Plus />
              Seed it there
            </Button>
          </div>
          {main && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label>{`Drive the main herd out of ${main.name}`}</Label>
              <EntityPicker
                types={['region']}
                value={target}
                onChange={setTarget}
                placeholder='Choose where it goes…'
              />
              <Button
                act={move}
                size='sm'
                variant='outline'
                className='self-start'
                disabled={busy !== null || target === null}
                disabledReason={
                  busy ?? (target === null ? 'Choose a land' : undefined)
                }
                onClick={() => move.mutate({ from: main.id, to: target ?? 0 })}
              >
                <ArrowRight />
                Move the herd
              </Button>
            </div>
          )}
        </div>
      </Group>
    </div>
  )
}

function YieldControls({ id, card, blocked }: Blocked) {
  const [product, setProduct] = useState('')
  const [commodity, setCommodity] = useState('')
  const [material, setMaterial] = useState('')
  const [stuff, setStuff] = useState('')
  const [rate, setRate] = useState('1')
  const materials = useWorldMaterials(card.world_id ?? null)
  const crafted = Object.fromEntries(
    (materials.data?.materials ?? [])
      .filter((row) => row.world_material_id !== null)
      .map((row) => [String(row.world_material_id), row.label])
  )
  const goodKinds = useKinds('good', null)
  const goods: Record<string, Named> = Object.fromEntries(
    (goodKinds.data ?? [])
      .filter((kind) => !kind.retired)
      .map((kind) => [
        String(kind.id),
        { label: kind.name, icon: Package, tone: 'gold' as const },
      ])
  )
  const set = useGodAction<{
    product: string
    commodity: string | null
    material: string | null
    stuff?: number | null
    rate: number
    part?: ProductPart | null
    good?: number | null
  }>({
    writes: [{ lever: 'species:yield' }],
    run: ({
      product: name,
      commodity: kind,
      material: matter,
      stuff: own,
      rate: amount,
      part,
      good,
    }) =>
      unwrap(
        api.POST('/api/actions/species:yield', {
          body: {
            species_id: id,
            product: name,
            commodity: (kind || null) as 'grain' | null,
            material: (matter || null) as 'hide' | null,
            world_material_id: own ?? null,
            rate: amount,
            part: part ?? null,
            good_kind_id: good ?? null,
          },
        })
      ),
  })
  const use = useGodAction<{ use: string; held: boolean }>({
    writes: [{ lever: 'species:use' }],
    run: ({ use: kind, held }) =>
      unwrap(
        api.POST('/api/actions/species:use', {
          body: { species_id: id, use: kind as 'meat', held },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending, use.isPending)
  const amount = Math.round(Number(rate) || 0)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <Group title='Kept for' icon={Wheat}>
        <ul className='grid min-w-0 grid-cols-1 gap-2 @md/wild:grid-cols-2 @3xl/wild:grid-cols-4'>
          <Paged items={animalRoleValues} as='li'>
            {(key) => {
              const spec = named(USE, key)
              return (
                <li key={key}>
                  <label className='flex min-w-0 items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
                    <Medallion icon={spec.icon} tone={spec.tone} size='sm' />
                    <Text as='span' weight='medium' truncate className='flex-1'>
                      {spec.label}
                    </Text>
                    <Switch
                      act={use}
                      checked={card.uses.includes(key)}
                      disabled={busy !== null}
                      aria-label={spec.label}
                      onCheckedChange={(held) => use.mutate({ use: key, held })}
                    />
                  </label>
                </li>
              )
            }}
          </Paged>
        </ul>
      </Group>
      <Group title='What it yields' icon={Package}>
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={card.yields} as='li'>
            {(row) => (
              <YieldRow
                act={set}
                key={`${row.product}-${row.rate}`}
                row={row}
                busy={busy}
                goods={goods}
                onSet={(next, part, good) =>
                  set.mutate({
                    product: row.product,
                    commodity: row.commodity ?? null,
                    material: row.material ?? null,
                    stuff: row.world_material_id ?? null,
                    rate: next,
                    part,
                    good,
                  })
                }
              />
            )}
          </Paged>
        </ul>
        <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md/wild:grid-cols-2 @3xl/wild:grid-cols-4'>
          <FieldTile id={`yield-product-${id}`} label='Product'>
            <Input
              id={`yield-product-${id}`}
              value={product}
              placeholder='What it gives'
              onChange={(event) => setProduct(event.target.value)}
            />
          </FieldTile>
          <MindPicker
            label='Counts as goods'
            value={commodity}
            table={pickTable(commodityKindValues, COMMODITY)}
            blocked={busy}
            placeholder='Choose goods'
            onPick={setCommodity}
          />
          <MindPicker
            label='Material'
            value={material}
            table={pickTable(
              materialKindValues,
              Object.fromEntries(
                Object.entries(MATERIAL).map(([key, label]) => [key, { label }])
              )
            )}
            blocked={busy}
            placeholder='None'
            onPick={setMaterial}
          />
          {Object.keys(crafted).length > 0 && (
            <MindPicker
              label='A material of this world'
              value={stuff}
              table={crafted}
              blocked={busy}
              placeholder='None'
              onPick={setStuff}
            />
          )}
          <NumberField
            label='Per head'
            value={rate}
            min={1}
            disabled={busy !== null}
            onChange={setRate}
          />
        </div>
        <Button
          act={set}
          size='sm'
          variant='outline'
          className='self-start'
          disabled={
            busy !== null || product === '' || commodity === '' || amount < 1
          }
          disabledReason={
            busy ??
            (product === '' || commodity === ''
              ? 'Name the product and its goods'
              : amount < 1
                ? 'Give it at least one per head'
                : undefined)
          }
          onClick={() =>
            set.mutate({
              product,
              commodity,
              material: material || null,
              stuff: stuff ? Number(stuff) : null,
              rate: amount,
            })
          }
        >
          <Plus />
          Add the yield
        </Button>
      </Group>
    </div>
  )
}

const PART_CHOICES: Record<string, Named> = Object.fromEntries(
  Object.entries(PRODUCT_PARTS).map(([key, part]) => [
    key,
    { label: part.label, icon: part.icon, tone: part.tone ?? 'muted' },
  ])
)

function YieldRow({
  row,
  busy,
  goods: goodKinds,
  onSet,
  act,
}: {
  row: SpeciesCard['yields'][number]
  busy: string | null
  goods: Record<string, Named>
  onSet: (rate: number, part?: ProductPart | null, good?: number | null) => void
  act?: ActProp
}) {
  const [rate, setRate] = useState(String(row.rate))
  const goods = row.commodity ? COMMODITY[row.commodity] : null
  const label = titled(row.product)
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2'>
      <Medallion icon={goods?.icon ?? Package} tone='gold' size='sm' />
      <div className='flex min-w-0 flex-1 basis-32 flex-col'>
        <Text as='span' weight='medium' truncate>
          {label}
        </Text>
        <Muted as='span' variant='caption' truncate>
          {[
            row.part ? PRODUCT_PARTS[row.part].label : null,
            row.good_kind_name ?? goods?.label,
            row.material && plain(MATERIAL, row.material) !== goods?.label
              ? plain(MATERIAL, row.material)
              : null,
          ]
            .filter(Boolean)
            .join(' · ')}
        </Muted>
      </div>
      <div className='grid w-full min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <ChoiceSelect
          act={act}
          label={`${label} part`}
          value={row.part ?? ''}
          table={PART_CHOICES}
          blocked={busy}
          placeholder='Which part it is'
          onPick={(value) => onSet(row.rate, value as ProductPart)}
        />
        <ChoiceSelect
          act={act}
          label={`${label} good`}
          value={String(row.good_kind_id ?? '')}
          table={goodKinds}
          blocked={
            busy ??
            (Object.keys(goodKinds).length > 0
              ? null
              : 'No good of this world is known yet')
          }
          placeholder='Which good it counts as'
          onPick={(value) => onSet(row.rate, null, Number(value))}
        />
      </div>
      <Input
        className='w-20'
        type='number'
        inputMode='numeric'
        min={0}
        value={rate}
        aria-label={`${label} per head`}
        onChange={(event) => setRate(event.target.value)}
      />
      <Muted as='span' variant='caption'>
        per head
      </Muted>
      <Button
        act={act}
        size='icon-sm'
        variant='ghost'
        aria-label={`Set ${label}`}
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => onSet(Math.max(0, Math.round(Number(rate) || 0)))}
      >
        <Check />
      </Button>
      <Button
        act={act}
        size='icon-sm'
        variant='ghost'
        aria-label={`Remove ${label}`}
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => onSet(0)}
      >
        <Trash2 />
      </Button>
    </li>
  )
}

function TamingControls({ id, card, blocked }: Blocked) {
  const [community, setCommunity] = useState<number | null>(null)
  const [son, setSon] = useState<number | null>(null)
  const sons = useSons()
  const tame = useGodAction({
    writes: [{ lever: 'species:domesticate' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/species:domesticate', {
          body: { species_id: id, community_id: community ?? 0 },
        })
      ),
  })
  const holy = useGodAction<number | null>({
    writes: [{ lever: 'species:sacred' }],
    run: (who) =>
      unwrap(
        api.POST('/api/actions/species:sacred', {
          body: { species_id: id, son_id: who },
        })
      ),
  })
  const spawn = useGodAction({
    writes: [{ lever: 'beast:spawn' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/beast:spawn', { body: { species_id: id } })
      ),
  })
  const busy = busyOf(blocked, tame.isPending, holy.isPending, spawn.isPending)
  return (
    <div
      data-surface='DomesticationTimeline'
      className='grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'
    >
      <Group title='Give it to herders' icon={STAGE.domesticated.icon}>
        <Muted variant='caption'>
          A people takes it in and breeds it on: it becomes domesticated for
          them.
        </Muted>
        <EntityPicker
          types={COMMUNITIES}
          value={community}
          onChange={setCommunity}
          placeholder='Choose the herders…'
        />
        <Button
          act={tame}
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null || community === null}
          disabledReason={
            busy ?? (community === null ? 'Choose the herders' : undefined)
          }
          onClick={() => tame.mutate(undefined)}
        >
          <Leaf />
          Domesticate now
        </Button>
      </Group>
      <Group title='Hallow it' icon={Sparkles}>
        <MindPicker
          label='Sacred to'
          value={son === null ? '' : String(son)}
          table={Object.fromEntries(
            (sons.data ?? []).map((item) => [
              String(item.son.id),
              item.son.name,
            ])
          )}
          blocked={busy}
          placeholder='Choose a son'
          onPick={(value) => setSon(Number(value))}
        />
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            act={holy}
            size='sm'
            variant='outline'
            disabled={busy !== null || son === null}
            disabledReason={busy ?? (son === null ? 'Choose a son' : undefined)}
            onClick={() => holy.mutate(son)}
          >
            <Sparkles />
            Make sacred
          </Button>
          {card.sacred_to && (
            <Button
              act={holy}
              size='sm'
              variant='outline'
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() => holy.mutate(null)}
            >
              Unhallow
            </Button>
          )}
        </div>
      </Group>
      <Group title='Raise a legend' icon={Footprints} wide>
        <Muted variant='caption'>
          One of its kind grows into a named great beast with a lair and a
          hoard.
        </Muted>
        <Button
          act={spawn}
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => spawn.mutate(undefined)}
        >
          <Footprints />
          Raise a great beast
        </Button>
      </Group>
    </div>
  )
}

function SpeciesControls({ id, card, blocked }: Blocked) {
  const save = useSpeciesEdit(id)
  const busy = busyOf(blocked, save.isPending)
  return (
    <AdjustPanel
      acts={[save]}
      title='Shape this kind'
      note='Set its body, temper, lands, yields and taming. Whatever you set is held until you let the world decide again; every change goes into the ledger.'
      head={
        <Held
          act={save}
          keys={card.locked}
          label={fieldLabel}
          busy={busy}
          onRelease={() =>
            save.mutate({ values: {}, release: [...card.locked] })
          }
        />
      }
    >
      <Tabs defaultValue='nature'>
        <TabsList size='sm' aria-label='What to shape'>
          <TabsTrigger value='nature'>
            <HeartPulse />
            Nature
          </TabsTrigger>
          <TabsTrigger value='lands'>
            <MapPinned />
            Lands
          </TabsTrigger>
          <TabsTrigger value='yields'>
            <Wheat />
            Yields
          </TabsTrigger>
          <TabsTrigger value='taming'>
            <Dna />
            Taming
          </TabsTrigger>
          <TabsTrigger value='links'>
            <Crosshair />
            Hunting
          </TabsTrigger>
          <TabsTrigger value='sickness'>
            <Biohazard />
            Sickness
          </TabsTrigger>
          <TabsTrigger value='keeping'>
            <Sparkles />
            Keeping
          </TabsTrigger>
          <TabsTrigger value='growth'>
            <Sprout />
            Growth
          </TabsTrigger>
        </TabsList>
        <TabsContent value='nature'>
          <NatureControls id={id} card={card} blocked={blocked} />
        </TabsContent>
        <TabsContent value='lands'>
          <LandControls id={id} card={card} blocked={blocked} />
        </TabsContent>
        <TabsContent value='yields'>
          <YieldControls id={id} card={card} blocked={blocked} />
        </TabsContent>
        <TabsContent value='taming'>
          <TamingControls id={id} card={card} blocked={blocked} />
        </TabsContent>
        <TabsContent value='links'>
          <FoodLinkControls id={id} card={card} blocked={blocked} />
        </TabsContent>
        <TabsContent value='sickness'>
          <HostControls id={id} card={card} blocked={blocked} />
        </TabsContent>
        <TabsContent value='keeping'>
          <KeepingControls id={id} card={card} blocked={blocked} />
        </TabsContent>
        <TabsContent value='growth'>
          <FloraControls id={id} card={card} blocked={blocked} />
        </TabsContent>
      </Tabs>
    </AdjustPanel>
  )
}

function Body({ id, card, blocked }: Blocked) {
  return (
    <div
      data-surface='SpeciesProfile'
      className='@container/wild flex min-w-0 flex-col gap-4'
    >
      <Hero card={card} />
      <Vitals card={card} />
      <div className='grid min-w-0 grid-cols-1 gap-3 @xl/wild:grid-cols-2'>
        <Temperament card={card} />
        <LifeCycle card={card} />
        <Climate card={card} />
        <Taming id={id} card={card} blocked={blocked} />
        <Traits card={card} />
        <FoodChain card={card} />
        <UsesAndYields card={card} />
        <FloraCard card={card} />
        {card.species_class !== 'plant' && card.species_class !== 'fungus' && (
          <AnatomyCard nodeId={id} blocked={blocked} />
        )}
      </div>
      <Ranges card={card} />
      <SpeciesControls id={id} card={card} blocked={blocked} />
    </div>
  )
}

export function SpeciesSection({
  speciesId,
  readOnlyReason,
}: {
  speciesId: number
  readOnlyReason?: string | null
}) {
  const view = useSpecies(speciesId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <Section
      id='section-ecology'
      title='Ecology'
      description='How this kind lives: its body and temper, the lands it roams, what it eats and yields, and how far people have tamed it.'
      icon={ECOLOGY_ICON}
      tone='success'
    >
      {view.isPending && <LoadingBlock label='Reading the kind' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The kind is not yet described'
          description={view.error.message}
        />
      )}
      {view.data && <Body id={speciesId} card={view.data} blocked={blocked} />}
    </Section>
  )
}
