import { useState } from 'react'
import {
  ArrowRight,
  Check,
  Footprints,
  Leaf,
  Plus,
  Sparkles,
  Trash2,
  TriangleAlert,
  Wheat,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  commodityKindValues,
  dietValues,
  domesticationStageValues,
  materialKindValues,
  sizeClassValues,
  socialityValues,
  speciesUseValues,
} from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import {
  EmptyState,
  EntityLink,
  KpiTile,
  Section,
  StatBar,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useSons } from '@/features/pantheon/api'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { DictField, type FieldSpec, LoreFields } from '../lore/LoreFields'
import { table, words } from '../lore/api'
import { PERCENT, busyOf } from '../lore/model'
import { MindPicker } from '../mind/parts'
import { type SpeciesCard, useSpecies, useSpeciesEdit } from './api'

type Ref = { id: number; name: string } | null | undefined
const COMMUNITIES = ['settlement', 'people', 'faction', 'cult'] as const
const TERRAINS = [
  'plain',
  'steppe',
  'forest',
  'jungle',
  'marsh',
  'hills',
  'mountains',
  'high_pass',
  'desert',
  'tundra',
  'ice_sheet',
  'volcanic',
  'coast',
  'island',
  'river_valley',
  'canyon',
] as const

function Name({ item }: { item: Ref }) {
  if (!item) return <Muted as='span'>unknown</Muted>
  return (
    <EntityLink kind='entity' id={String(item.id)}>
      {item.name}
    </EntityLink>
  )
}

const FIELDS: FieldSpec[] = [
  { key: 'size_class', kind: 'enum', values: sizeClassValues },
  { key: 'diet', kind: 'enum', values: dietValues },
  { key: 'sociality', kind: 'enum', values: socialityValues },
  { key: 'stage', kind: 'enum', values: domesticationStageValues },
  { key: 'body_plan', kind: 'text' },
  { key: 'lifespan_years', kind: 'number', min: 1 },
  { key: 'maturity_years', kind: 'number', min: 0 },
  { key: 'litter_size', kind: 'number', min: 1 },
  { key: 'breeding_seasons', kind: 'number', min: 0 },
  { key: 'metabolism', kind: 'number', min: 0, max: PERCENT },
  { key: 'temperature_min', kind: 'number' },
  { key: 'temperature_max', kind: 'number' },
  { key: 'water_need', kind: 'number', min: 0, max: PERCENT },
  { key: 'altitude_min', kind: 'number' },
  { key: 'altitude_max', kind: 'number' },
  { key: 'aggression', kind: 'number', min: 0, max: PERCENT },
  { key: 'territoriality', kind: 'number', min: 0, max: PERCENT },
  { key: 'cunning', kind: 'number', min: 0, max: PERCENT },
  { key: 'fear_of_people', kind: 'number', min: 0, max: PERCENT },
  { key: 'tameability', kind: 'number', min: 0, max: PERCENT },
  { key: 'nocturnal', kind: 'bool' },
  { key: 'migratory', kind: 'bool' },
]

function Ranges({
  id,
  card,
  blocked,
}: {
  id: number
  card: SpeciesCard
  blocked: string | null
}) {
  const [region, setRegion] = useState<number | null>(null)
  const [target, setTarget] = useState<number | null>(null)
  const set = useGodAction<{ region: number; abundance: number }>({
    run: ({ region: where, abundance }) =>
      unwrap(
        api.POST('/api/actions/species:range', {
          body: { species_id: id, region_id: where, values: { abundance } },
        })
      ),
  })
  const drop = useGodAction<number>({
    run: (where) =>
      unwrap(
        api.POST('/api/actions/species:drop_range', {
          body: { species_id: id, region_id: where },
        })
      ),
  })
  const move = useGodAction<{ from: number; to: number }>({
    run: ({ from, to }) =>
      unwrap(
        api.POST('/api/actions/species:move_range', {
          body: { species_id: id, source_id: from, target_id: to },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending, drop.isPending, move.isPending)
  return (
    <div data-surface='SpeciesRanges' className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Where it ranges</Label>
      {card.ranges.length === 0 && <Muted>It ranges nowhere on the map.</Muted>}
      <ul className='flex min-w-0 flex-col gap-2'>
        {card.ranges.map((row) => (
          <RangeRow
            key={row.region?.id}
            row={row}
            busy={busy}
            onSet={(abundance) =>
              set.mutate({ region: row.region?.id ?? 0, abundance })
            }
            onDrop={() => drop.mutate(row.region?.id ?? 0)}
          />
        ))}
      </ul>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <EntityPicker
          types={['region']}
          value={region}
          onChange={setRegion}
          placeholder='Seed into a land…'
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || region === null}
          disabledReason={
            busy ?? (region === null ? 'Choose a land' : undefined)
          }
          onClick={() => set.mutate({ region: region ?? 0, abundance: 10 })}
        >
          <Plus />
          Seed it there
        </Button>
        {card.ranges[0]?.region && (
          <>
            <EntityPicker
              types={['region']}
              value={target}
              onChange={setTarget}
              placeholder='Drive the main herd to…'
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || target === null}
              disabledReason={
                busy ?? (target === null ? 'Choose a land' : undefined)
              }
              onClick={() =>
                move.mutate({
                  from: card.ranges[0]?.region?.id ?? 0,
                  to: target ?? 0,
                })
              }
            >
              <ArrowRight />
              Move the herd
            </Button>
          </>
        )}
      </div>
    </div>
  )
}

function RangeRow({
  row,
  busy,
  onSet,
  onDrop,
}: {
  row: SpeciesCard['ranges'][number]
  busy: string | null
  onSet: (value: number) => void
  onDrop: () => void
}) {
  const [draft, setDraft] = useState(String(row.abundance))
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-2'>
      <Name item={row.region} />
      <div className='min-w-0 flex-1'>
        <StatBar
          label={`${words(row.trend)}, fit ${row.fit}, hunted ${row.hunted}`}
          value={row.abundance}
          max={PERCENT}
        />
      </div>
      <Input
        className='w-20'
        type='number'
        min={0}
        max={PERCENT}
        value={draft}
        aria-label='abundance'
        onChange={(event) => setDraft(event.target.value)}
      />
      <Button
        size='icon'
        variant='ghost'
        aria-label='Set abundance'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => onSet(Math.round(Number(draft) || 0))}
      >
        <Check />
      </Button>
      <Button
        size='icon'
        variant='ghost'
        aria-label='Drive it out'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={onDrop}
      >
        <Trash2 />
      </Button>
    </li>
  )
}

function Yields({
  id,
  card,
  blocked,
}: {
  id: number
  card: SpeciesCard
  blocked: string | null
}) {
  const [product, setProduct] = useState('')
  const [commodity, setCommodity] = useState('')
  const [material, setMaterial] = useState('')
  const set = useGodAction<{
    product: string
    commodity: string | null
    material: string | null
    rate: number
  }>({
    run: ({ product: name, commodity: kind, material: matter, rate }) =>
      unwrap(
        api.POST('/api/actions/species:yield', {
          body: {
            species_id: id,
            product: name,
            commodity: (kind || null) as 'grain' | null,
            material: (matter || null) as 'hide' | null,
            rate,
          },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending)
  return (
    <div data-surface='SpeciesYields' className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>What it yields</Label>
      <ul className='flex min-w-0 flex-wrap gap-2'>
        {card.yields.map((row) => (
          <li key={row.product} className='flex items-center gap-1'>
            <Badge variant='outline'>{`${row.rate} ${row.product}${row.material ? ` (${words(row.material)})` : ''}`}</Badge>
            <Button
              size='icon'
              variant='ghost'
              aria-label={`Remove ${row.product}`}
              disabled={busy !== null}
              disabledReason={busy ?? undefined}
              onClick={() =>
                set.mutate({
                  product: row.product,
                  commodity: row.commodity ?? null,
                  material: row.material ?? null,
                  rate: 0,
                })
              }
            >
              <Trash2 />
            </Button>
          </li>
        ))}
      </ul>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='flex min-w-0 flex-col gap-1'>
          <Label>Product</Label>
          <Input
            value={product}
            aria-label='Product'
            onChange={(event) => setProduct(event.target.value)}
          />
        </div>
        <MindPicker
          label='Goods'
          value={commodity}
          table={table(commodityKindValues)}
          blocked={busy}
          placeholder='Choose'
          onPick={setCommodity}
        />
        <MindPicker
          label='Material'
          value={material}
          table={table(materialKindValues)}
          blocked={busy}
          placeholder='Optional'
          onPick={setMaterial}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || product === '' || commodity === ''}
          disabledReason={
            busy ??
            (product === '' || commodity === ''
              ? 'Name the product and its goods'
              : undefined)
          }
          onClick={() =>
            set.mutate({
              product,
              commodity,
              material: material || null,
              rate: 1,
            })
          }
        >
          <Wheat />
          Add yield
        </Button>
      </div>
    </div>
  )
}

function Uses({
  id,
  card,
  blocked,
}: {
  id: number
  card: SpeciesCard
  blocked: string | null
}) {
  const set = useGodAction<{ use: string; held: boolean }>({
    run: ({ use, held }) =>
      unwrap(
        api.POST('/api/actions/species:use', {
          body: { species_id: id, use: use as 'food', held },
        })
      ),
  })
  const busy = busyOf(blocked, set.isPending)
  return (
    <div data-surface='SpeciesUses' className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>Kept for</Label>
      <ul className='flex min-w-0 flex-wrap gap-3'>
        {speciesUseValues.map((use) => (
          <li key={use}>
            <label className='flex items-center gap-2'>
              <Switch
                checked={card.uses.includes(use)}
                disabled={busy !== null}
                aria-label={words(use)}
                onCheckedChange={(held) => set.mutate({ use, held })}
              />
              <Text as='span'>{words(use)}</Text>
            </label>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Domestication({
  id,
  card,
  blocked,
}: {
  id: number
  card: SpeciesCard
  blocked: string | null
}) {
  const [community, setCommunity] = useState<number | null>(null)
  const [son, setSon] = useState<number | null>(null)
  const sons = useSons()
  const tame = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/species:domesticate', {
          body: { species_id: id, community_id: community ?? 0 },
        })
      ),
  })
  const holy = useGodAction<number | null>({
    run: (who) =>
      unwrap(
        api.POST('/api/actions/species:sacred', {
          body: { species_id: id, son_id: who },
        })
      ),
  })
  const spawn = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/beast:spawn', { body: { species_id: id } })
      ),
  })
  const busy = busyOf(blocked, tame.isPending, holy.isPending, spawn.isPending)
  return (
    <div
      data-surface='DomesticationTimeline'
      className='flex min-w-0 flex-col gap-2'
    >
      <Label variant='overline'>Taming and holiness</Label>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {domesticationStageValues.map((stage) => (
          <Badge
            key={stage}
            variant={stage === card.stage ? 'info' : 'outline'}
          >
            {words(stage)}
          </Badge>
        ))}
        {card.domesticated_from && (
          <Text as='span'>
            bred from <Name item={card.domesticated_from} />
          </Text>
        )}
        {card.sacred_to && (
          <Text as='span'>
            sacred to <Name item={card.sacred_to} />
          </Text>
        )}
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <EntityPicker
          types={COMMUNITIES}
          value={community}
          onChange={setCommunity}
          placeholder='Herders…'
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || community === null}
          disabledReason={
            busy ?? (community === null ? 'Choose the herders' : undefined)
          }
          onClick={() => tame.mutate(undefined)}
        >
          <Leaf />
          Domesticate now
        </Button>
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
        <Button
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
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => holy.mutate(null)}
          >
            Unhallow
          </Button>
        )}
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => spawn.mutate(undefined)}
        >
          <Footprints />
          Raise a great beast
        </Button>
      </div>
    </div>
  )
}

function Body({
  id,
  card,
  blocked,
}: {
  id: number
  card: SpeciesCard
  blocked: string | null
}) {
  const edit = useSpeciesEdit(id)
  const top = card.ranges[0]
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        <KpiTile
          label='Size'
          value={words(card.size_class)}
          icon={Footprints}
        />
        <KpiTile
          label='Diet'
          value={words(card.diet)}
          icon={Leaf}
          tone='verdigris'
        />
        <KpiTile
          label='Lands'
          value={card.ranges.length}
          icon={Sparkles}
          tone='info'
          hint={top?.region?.name}
        />
        <KpiTile
          label='Tameability'
          value={card.tameability}
          icon={Check}
          tone='muted'
          meter={{
            value: card.tameability,
            max: PERCENT,
            label: 'tameability',
          }}
        />
      </div>
      <div
        data-surface='SpeciesTraits'
        className='flex min-w-0 flex-wrap gap-2'
      >
        {card.traits.map((trait) => (
          <Badge key={trait} variant='outline'>
            {words(trait)}
          </Badge>
        ))}
      </div>
      <div
        data-surface='FoodChain'
        className='flex min-w-0 flex-wrap items-center gap-2'
      >
        {card.hunts.length > 0 && <Text as='span'>hunts</Text>}
        {card.hunts.map((item) => (
          <Name key={item.id} item={item} />
        ))}
        {card.hunted_by.length > 0 && <Text as='span'>hunted by</Text>}
        {card.hunted_by.map((item) => (
          <Name key={item.id} item={item} />
        ))}
        {card.beasts.length > 0 && <Text as='span'>its great ones:</Text>}
        {card.beasts.map((item) => (
          <Name key={item.id} item={item} />
        ))}
        {card.descendants.length > 0 && <Text as='span'>gave rise to</Text>}
        {card.descendants.map((item) => (
          <Name key={item.id} item={item} />
        ))}
      </div>
      <LoreFields
        entityId={id}
        surface='SpeciesProfile'
        fields={FIELDS}
        current={card}
        locked={card.locked}
        blocked={blocked}
        editor={edit}
      />
      <DictField
        entityId={id}
        spec={{ key: 'habitat', label: 'Lands it loves', value: card.habitat }}
        blocked={blocked}
        suggestions={TERRAINS}
        editor={edit}
      />
      <Ranges id={id} card={card} blocked={blocked} />
      <Yields id={id} card={card} blocked={blocked} />
      <Uses id={id} card={card} blocked={blocked} />
      <Domestication id={id} card={card} blocked={blocked} />
      {card.herds.length > 0 && (
        <div
          data-surface='SpeciesHerds'
          className='flex min-w-0 flex-col gap-1'
        >
          <Label variant='overline'>Kept in herds by</Label>
          {card.herds.map((row) => (
            <Text key={row.community?.id} as='span'>
              <Name item={row.community} />{' '}
              {`${row.head} head, ${words(row.stage)}`}
            </Text>
          ))}
        </div>
      )}
      {card.hosts.length > 0 && (
        <div
          data-surface='SpeciesHosts'
          className='flex min-w-0 flex-wrap items-center gap-2'
        >
          <Label variant='overline'>Carries</Label>
          {card.hosts.map((row) => (
            <Badge
              key={row.disease?.id}
              variant={row.immune ? 'outline' : 'destructive'}
            >
              {`${row.disease?.name ?? 'a sickness'}${row.immune ? ' (immune)' : ''}`}
            </Badge>
          ))}
        </div>
      )}
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
      description='Body, diet, habitat, ranges, yields, taming and its place in the food web.'
      icon={Leaf}
    >
      {view.isPending && <Muted>Reading the kind…</Muted>}
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
