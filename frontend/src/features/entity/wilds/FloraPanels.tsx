import { Fragment, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bug,
  Lock,
  Plus,
  Sprout,
  Trash2,
  TriangleAlert,
  Wheat,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  biochemistryValues,
  cultivationValues,
  growthCycleValues,
  speciesClassValues,
  type components,
} from '@/api/generated/schema'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  Medallion,
  Paged,
  Section,
  StatBar,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { PERCENT, busyOf } from '../lore/model'
import { MindPicker } from '../mind/parts'
import {
  type SpeciesCard,
  floraKeys,
  useSpeciesEdit,
  useWildAction,
} from './api'
import {
  BADGE_OF,
  BIOCHEMISTRY,
  CULTIVATION,
  GROWTH_CYCLE,
  type Named,
  PLANT_YIELD,
  SPECIES_CLASS,
  fieldLabel,
  named,
} from './labels'
import { Card, Group, Name, NumberField, Tile, TileGrid } from './parts'

type Blocked = { id: number; card: SpeciesCard; blocked: string | null }
type RegionCrops = components['schemas']['RegionCrops']
type WorldLife = components['schemas']['WorldLife']

const GROWN = new Set(['plant', 'fungus'])
const SPECIES_TYPES = ['species']
const REGION_TYPES = ['region']
const WORKING = 'Working on it.'

function tableOf(
  values: readonly string[],
  table: Record<string, Named>
): Record<string, string> {
  return Object.fromEntries(values.map((key) => [key, named(table, key).label]))
}

function share(value: string): number | null {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed >= 0 && parsed <= PERCENT
    ? parsed
    : null
}

function CultivationTrack({ stage }: { stage: string }) {
  const current = named(CULTIVATION, stage)
  const step = CULTIVATION[stage]?.step ?? 0
  return (
    <div
      data-surface='CultivationTrack'
      className='flex min-w-0 flex-col gap-2'
      aria-label={`Cultivation: ${current.label}`}
    >
      <div className='flex min-w-0 items-center'>
        {cultivationValues.map((key, index) => {
          const spec = named(CULTIVATION, key)
          const reached = (CULTIVATION[key]?.step ?? 0) <= step
          return (
            <Fragment key={key}>
              {index > 0 && (
                <span
                  aria-hidden='true'
                  className={cn(
                    'h-0.5 min-w-2 flex-1 rounded-full',
                    reached ? 'bg-primary' : 'bg-border'
                  )}
                />
              )}
              <span
                aria-label={spec.label}
                className={cn(
                  'rounded-full',
                  key === stage &&
                    'ring-2 ring-ring/40 ring-offset-2 ring-offset-background'
                )}
              >
                <Medallion
                  icon={spec.icon}
                  tone={reached ? (spec.tone ?? 'gold') : 'muted'}
                  size='sm'
                />
              </span>
            </Fragment>
          )
        })}
      </div>
      <div className='flex min-w-0 flex-wrap items-baseline gap-x-2'>
        <Text as='span' weight='semibold'>
          {current.label}
        </Text>
        <Muted as='span' variant='caption'>
          {CULTIVATION[stage]?.hint ?? ''}
        </Muted>
      </div>
    </div>
  )
}

export function FloraCard({ card }: { card: SpeciesCard }) {
  const kind = named(SPECIES_CLASS, card.species_class)
  const life = named(BIOCHEMISTRY, card.biochemistry)
  const plant = card.plant
  return (
    <Card
      title='Kind of life'
      icon={kind.icon}
      tone={kind.tone}
      hint={SPECIES_CLASS[card.species_class]?.hint}
      wide
    >
      <div data-surface='SpeciesFlora' className='flex min-w-0 flex-col gap-3'>
        <TileGrid>
          <Tile spec={kind} caption={SPECIES_CLASS[card.species_class]?.hint} />
          <Tile
            spec={life}
            caption={BIOCHEMISTRY[card.biochemistry]?.hint}
            aside={
              card.bearable ? undefined : (
                <Badge size='sm' variant='destructive'>
                  <TriangleAlert aria-hidden='true' />
                  Cannot live here
                </Badge>
              )
            }
          />
          {plant && (
            <Tile
              spec={named(GROWTH_CYCLE, plant.growth_cycle)}
              caption={`Needs ${plant.growing_seasons} growing ${plant.growing_seasons === 1 ? 'season' : 'seasons'} and soil of ${plant.soil_need}`}
            />
          )}
        </TileGrid>
        {!card.bearable && (
          <Muted variant='caption'>
            Its world does not bear life built on {life.label.toLowerCase()}; it
            cannot grow or spread there until the world bears it.
          </Muted>
        )}
        {plant && (
          <>
            <CultivationTrack stage={plant.cultivation} />
            {plant.cultivar_of && (
              <div className='flex min-w-0 flex-wrap items-center gap-2'>
                <Muted as='span' variant='caption'>
                  Bred from
                </Muted>
                <Name item={plant.cultivar_of} />
              </div>
            )}
          </>
        )}
        {card.sown_in.length > 0 && (
          <ul
            data-surface='SownIn'
            className='flex min-w-0 flex-col gap-2'
            aria-label='Lands that sow it'
          >
            <Paged items={card.sown_in} as='li'>
              {(row) => (
                <li
                  key={row.region?.id}
                  className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-2'
                >
                  <div className='flex min-w-0 items-center gap-2'>
                    <Medallion icon={Wheat} tone='success' size='sm' />
                    <div className='min-w-0 flex-1'>
                      <Name item={row.region} />
                    </div>
                    {row.locked.includes('share') && (
                      <Badge size='sm' variant='outline'>
                        <Lock aria-hidden='true' />
                        Held
                      </Badge>
                    )}
                  </div>
                  <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
                    <StatBar
                      label='Share of the fields'
                      value={row.share}
                      max={PERCENT}
                      tone='success'
                    />
                    <StatBar
                      label='How well the land suits it'
                      value={row.fit}
                      max={PERCENT}
                      tone={row.fit >= PERCENT / 2 ? 'success' : 'warning'}
                    />
                  </div>
                </li>
              )}
            </Paged>
          </ul>
        )}
        {card.pests.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Muted as='span' variant='caption'>
              Its pests:
            </Muted>
            {card.pests.map((item) => (
              <Badge key={item.id} size='sm' variant='warning'>
                <Bug aria-hidden='true' />
                {item.name}
              </Badge>
            ))}
          </div>
        )}
        {card.pest_of.length > 0 && (
          <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Muted as='span' variant='caption'>
              It feeds on:
            </Muted>
            {card.pest_of.map((item) => (
              <Badge key={item.id} size='sm' variant='outline'>
                <Sprout aria-hidden='true' />
                {item.name}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </Card>
  )
}

function usePlantEdit(id: number) {
  return useWildAction<{ values: Record<string, unknown>; release?: string[] }>(
    'plant:edit',
    (vars) => ({
      species_id: id,
      values: vars.values,
      release: vars.release ?? [],
    })
  )
}

function useCropSet() {
  return useWildAction<{
    region: number
    plant: number
    share: number | null
    hold?: boolean
    release?: string[]
  }>('crop:set', (vars) => ({
    region_id: vars.region,
    plant_id: vars.plant,
    share: vars.share,
    hold: vars.hold ?? true,
    release: vars.release ?? [],
  }))
}

function useCropDrop() {
  return useWildAction<{ region: number; plant: number }>(
    'crop:drop',
    (vars) => ({ region_id: vars.region, plant_id: vars.plant })
  )
}

function useCropPest() {
  return useWildAction<{ plant: number; pest: number; present: boolean }>(
    'crop_pest:set',
    (vars) => ({
      plant_id: vars.plant,
      pest_id: vars.pest,
      present: vars.present,
    })
  )
}

function ShareSetter({
  label,
  value,
  blocked,
  onSave,
}: {
  label: string
  value: number
  blocked: string | null
  onSave: (next: number) => void
}) {
  const [draft, setDraft] = useState(String(value))
  const parsed = share(draft)
  const problem =
    parsed === null
      ? 'A share runs from 0 to 100'
      : parsed === value
        ? 'This is the present share'
        : null
  return (
    <div className='flex min-w-0 items-end gap-2'>
      <div className='min-w-0 flex-1'>
        <NumberField
          label={label}
          value={draft}
          min={0}
          max={PERCENT}
          disabled={blocked !== null}
          onChange={setDraft}
        />
      </div>
      <Button
        size='sm'
        variant='outline'
        disabled={(blocked ?? problem) !== null}
        disabledReason={blocked ?? problem ?? undefined}
        onClick={() => parsed !== null && onSave(parsed)}
      >
        Set
      </Button>
    </div>
  )
}

function NumberSetter({
  label,
  value,
  min,
  max,
  blocked,
  onSave,
}: {
  label: string
  value: number
  min: number
  max: number
  blocked: string | null
  onSave: (next: number) => void
}) {
  const [draft, setDraft] = useState(String(value))
  const parsed = Number(draft)
  const problem = !Number.isInteger(parsed)
    ? 'Write a whole number'
    : parsed < min || parsed > max
      ? `It runs from ${min} to ${max}`
      : parsed === value
        ? 'This is the present value'
        : null
  return (
    <div className='flex min-w-0 items-end gap-2'>
      <div className='min-w-0 flex-1'>
        <NumberField
          label={label}
          value={draft}
          min={min}
          max={max}
          disabled={blocked !== null}
          onChange={setDraft}
        />
      </div>
      <Button
        size='sm'
        variant='outline'
        disabled={(blocked ?? problem) !== null}
        disabledReason={blocked ?? problem ?? undefined}
        onClick={() => onSave(parsed)}
      >
        Set
      </Button>
    </div>
  )
}

function SowForm({
  blocked,
  pick,
  onSow,
}: {
  blocked: string | null
  pick: 'region' | 'plant'
  onSow: (target: number, share: number) => void
}) {
  const [target, setTarget] = useState<number | null>(null)
  const [draft, setDraft] = useState('20')
  const parsed = share(draft)
  const reason =
    blocked ??
    (target === null
      ? pick === 'region'
        ? 'Choose a land'
        : 'Choose a plant'
      : parsed === null
        ? 'A share runs from 0 to 100'
        : null)
  return (
    <div className='flex min-w-0 flex-wrap items-end gap-2'>
      <EntityPicker
        types={pick === 'region' ? REGION_TYPES : SPECIES_TYPES}
        value={target}
        onChange={setTarget}
        placeholder={pick === 'region' ? 'Sow it in…' : 'Sow a plant…'}
      />
      <NumberField
        label='Share of the fields'
        value={draft}
        min={0}
        max={PERCENT}
        disabled={blocked !== null}
        onChange={setDraft}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => {
          if (target !== null && parsed !== null) onSow(target, parsed)
          setTarget(null)
        }}
      >
        <Plus />
        Sow
      </Button>
    </div>
  )
}

export function FloraControls({ id, card, blocked }: Blocked) {
  const save = useSpeciesEdit(id)
  const plantEdit = usePlantEdit(id)
  const sow = useCropSet()
  const clear = useCropDrop()
  const pest = useCropPest()
  const [pestId, setPestId] = useState<number | null>(null)
  const pending =
    save.isPending ||
    plantEdit.isPending ||
    sow.isPending ||
    clear.isPending ||
    pest.isPending
  const busy = busyOf(blocked, pending)
  const plant = card.plant
  const grown = GROWN.has(card.species_class)
  return (
    <div data-surface='FloraControls' className='flex min-w-0 flex-col gap-3'>
      <Group title='Kind of life' icon={Sprout}>
        <div className='grid min-w-0 grid-cols-1 gap-3 @md/wild:grid-cols-2'>
          <MindPicker
            label={fieldLabel('species_class')}
            value={card.species_class}
            table={tableOf(speciesClassValues, SPECIES_CLASS)}
            blocked={busy}
            onPick={(value) =>
              save.mutate({ values: { species_class: value } })
            }
          />
          <MindPicker
            label={fieldLabel('biochemistry')}
            value={card.biochemistry}
            table={tableOf(biochemistryValues, BIOCHEMISTRY)}
            blocked={busy}
            onPick={(value) => save.mutate({ values: { biochemistry: value } })}
          />
        </div>
        <Muted variant='caption'>
          Plants and fungi are gathered, sown and harvested; vermin spoil stores
          and feed on crops. A kind lives only on worlds that bear its kind of
          life.
        </Muted>
      </Group>
      {grown && plant ? (
        <>
          <Group title='How it grows' icon={Wheat}>
            <div className='grid min-w-0 grid-cols-1 gap-3 @md/wild:grid-cols-2'>
              <MindPicker
                label={fieldLabel('growth_cycle')}
                value={plant.growth_cycle}
                table={tableOf(growthCycleValues, GROWTH_CYCLE)}
                blocked={busy}
                onPick={(value) =>
                  plantEdit.mutate({ values: { growth_cycle: value } })
                }
              />
              <MindPicker
                label={fieldLabel('cultivation')}
                value={plant.cultivation}
                table={tableOf(cultivationValues, CULTIVATION)}
                blocked={busy}
                onPick={(value) =>
                  plantEdit.mutate({ values: { cultivation: value } })
                }
              />
              <NumberSetter
                key={`seasons-${plant.growing_seasons}`}
                label={fieldLabel('growing_seasons')}
                value={plant.growing_seasons}
                min={1}
                max={12}
                blocked={busy}
                onSave={(next) =>
                  plantEdit.mutate({ values: { growing_seasons: next } })
                }
              />
              <NumberSetter
                key={`soil-${plant.soil_need}`}
                label={fieldLabel('soil_need')}
                value={plant.soil_need}
                min={0}
                max={PERCENT}
                blocked={busy}
                onSave={(next) =>
                  plantEdit.mutate({ values: { soil_need: next } })
                }
              />
            </div>
            {plant.locked.length > 0 && (
              <Button
                size='sm'
                variant='ghost'
                className='self-start'
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() =>
                  plantEdit.mutate({ values: {}, release: [...plant.locked] })
                }
              >
                <Lock />
                Let the world shape its growth again
              </Button>
            )}
          </Group>
          <Group title='Where it is sown' icon={Sprout} wide>
            {card.sown_in.length === 0 ? (
              <Muted>No land sows it yet.</Muted>
            ) : (
              <div className='flex min-w-0 flex-col gap-2'>
                <Paged items={card.sown_in}>
                  {(row) =>
                    row.region && (
                      <div
                        key={row.region.id}
                        className='flex min-w-0 flex-col gap-2 rounded-lg border p-2'
                      >
                        <div className='flex min-w-0 items-center gap-2'>
                          <div className='min-w-0 flex-1'>
                            <Name item={row.region} />
                          </div>
                          <Button
                            size='icon-sm'
                            variant='ghost'
                            aria-label={`Clear it from the fields of ${row.region.name}`}
                            disabled={busy !== null}
                            disabledReason={busy ?? undefined}
                            onClick={() =>
                              row.region &&
                              clear.mutate({ region: row.region.id, plant: id })
                            }
                          >
                            <Trash2 />
                          </Button>
                        </div>
                        <ShareSetter
                          key={`${row.region.id}-${row.share}`}
                          label='Share of the fields'
                          value={row.share}
                          blocked={busy}
                          onSave={(next) =>
                            row.region &&
                            sow.mutate({
                              region: row.region.id,
                              plant: id,
                              share: next,
                            })
                          }
                        />
                      </div>
                    )
                  }
                </Paged>
              </div>
            )}
            <SowForm
              blocked={busy}
              pick='region'
              onSow={(region, next) =>
                sow.mutate({ region, plant: id, share: next })
              }
            />
          </Group>
          <Group title='Its pests' icon={Bug}>
            {card.pests.length === 0 ? (
              <Muted>Nothing feeds on it yet.</Muted>
            ) : (
              <div className='flex min-w-0 flex-wrap gap-1.5'>
                {card.pests.map((item) => (
                  <Badge key={item.id} variant='warning'>
                    <Bug aria-hidden='true' />
                    {item.name}
                    <Button
                      size='icon-sm'
                      variant='ghost'
                      aria-label={`${item.name} no longer feeds on it`}
                      disabled={busy !== null}
                      disabledReason={busy ?? undefined}
                      onClick={() =>
                        pest.mutate({
                          plant: id,
                          pest: item.id,
                          present: false,
                        })
                      }
                    >
                      <Trash2 />
                    </Button>
                  </Badge>
                ))}
              </div>
            )}
            <div className='flex min-w-0 flex-wrap items-end gap-2'>
              <EntityPicker
                types={SPECIES_TYPES}
                value={pestId}
                onChange={setPestId}
                placeholder='A pest that feeds on it…'
              />
              <Button
                size='sm'
                variant='outline'
                disabled={busy !== null || pestId === null}
                disabledReason={
                  busy ?? (pestId === null ? 'Choose a pest' : undefined)
                }
                onClick={() => {
                  if (pestId !== null)
                    pest.mutate({ plant: id, pest: pestId, present: true })
                  setPestId(null)
                }}
              >
                <Plus />
                Set the pest
              </Button>
            </div>
          </Group>
        </>
      ) : (
        <Muted variant='caption'>
          {grown
            ? 'The world sets out how it grows after the next epoch; then you can shape it here.'
            : 'Only plants and fungi are sown in fields; set its kind of life to plant or fungus to sow it.'}
        </Muted>
      )}
    </div>
  )
}

function useRegionCrops(regionId: number) {
  return useQuery({
    queryKey: floraKeys.crops(regionId),
    queryFn: () =>
      unwrap(
        api.GET('/api/regions/{region_id}/crops', {
          params: { path: { region_id: regionId } },
        })
      ),
  })
}

function CropRow({
  regionId,
  row,
  blocked,
}: {
  regionId: number
  row: RegionCrops['crops'][number]
  blocked: string | null
}) {
  const sow = useCropSet()
  const clear = useCropDrop()
  const busy = busyOf(blocked, sow.isPending || clear.isPending)
  const stage = row.cultivation ? named(CULTIVATION, row.cultivation) : null
  const held = row.locked.includes('share')
  if (!row.plant) return null
  const plant = row.plant
  return (
    <div className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Medallion
          icon={stage?.icon ?? Sprout}
          tone={stage?.tone ?? 'success'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Name item={plant} />
          <div className='flex min-w-0 flex-wrap gap-1'>
            {stage && (
              <Badge size='sm' variant={BADGE_OF[stage.tone ?? 'gold']}>
                {stage.label}
              </Badge>
            )}
            {row.products.map((key) => {
              const product = named(PLANT_YIELD, key)
              const Icon = product.icon
              return (
                <Badge key={key} size='sm' variant='secondary'>
                  <Icon aria-hidden='true' />
                  {product.label}
                </Badge>
              )
            })}
            {held && (
              <Badge size='sm' variant='outline'>
                <Lock aria-hidden='true' />
                Held
              </Badge>
            )}
          </div>
        </div>
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Clear ${plant.name} from these fields`}
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => clear.mutate({ region: regionId, plant: plant.id })}
        >
          <Trash2 />
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <StatBar
          label='Share of the fields'
          value={row.share}
          max={PERCENT}
          tone='success'
        />
        <StatBar
          label='How well the land suits it'
          value={row.fit}
          max={PERCENT}
          tone={row.fit >= PERCENT / 2 ? 'success' : 'warning'}
        />
      </div>
      {row.pests.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Muted as='span' variant='caption'>
            Pests:
          </Muted>
          {row.pests.map((item) => (
            <Badge key={item.id} size='sm' variant='warning'>
              <Bug aria-hidden='true' />
              {item.name}
            </Badge>
          ))}
        </div>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-2'>
        <div className='min-w-0 flex-1'>
          <ShareSetter
            key={`${plant.id}-${row.share}`}
            label='Hold its share at'
            value={row.share}
            blocked={busy}
            onSave={(next) =>
              sow.mutate({ region: regionId, plant: plant.id, share: next })
            }
          />
        </div>
        {held && (
          <Button
            size='sm'
            variant='ghost'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() =>
              sow.mutate({
                region: regionId,
                plant: plant.id,
                share: null,
                hold: false,
                release: ['share'],
              })
            }
          >
            <Lock />
            Let it drift
          </Button>
        )}
      </div>
    </div>
  )
}

export function RegionCropsSection({
  regionId,
  readOnlyReason,
}: {
  regionId: number
  readOnlyReason?: string | null
}) {
  const view = useRegionCrops(regionId)
  const sow = useCropSet()
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const busy = busyOf(blocked, sow.isPending)
  const data = view.data
  const full = data !== undefined && data.crops.length >= data.crop_cap
  return (
    <Section
      id='section-crops'
      title='Fields and crops'
      description='The plants this land sows, the share of its fields each takes, how well the land suits it and what feeds on it. The harvest follows how well its crops fit the land.'
      icon={Wheat}
      tone='success'
    >
      {view.isPending && <LoadingBlock label='Reading the fields' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The fields could not be read'
          description={view.error.message}
        />
      )}
      {data && (
        <div data-surface='RegionCrops' className='flex min-w-0 flex-col gap-3'>
          <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
            <KpiTile
              label='Harvest from its crops'
              value={`${data.harvest_pct}%`}
              icon={Wheat}
              tone={data.harvest_pct >= 90 ? 'success' : 'warning'}
              meter={{
                value: data.harvest_pct,
                max: PERCENT,
                label: 'Harvest from its crops',
              }}
              hint='The share of a full harvest its crops give, from how well each fits the land'
            />
            <KpiTile
              label='Crops sown'
              value={`${data.crops.length} of ${data.crop_cap}`}
              icon={Sprout}
              tone='info'
              hint='A land sows only so many crops at once'
            />
          </div>
          {data.crops.length === 0 ? (
            <EmptyState
              icon={Sprout}
              title='No crop is sown here'
              description='Its harvest follows the land alone until a plant is gathered and sown here, spreads from a neighbour or is sown by your hand.'
            />
          ) : (
            <div className='flex min-w-0 flex-col gap-2'>
              <Paged items={data.crops}>
                {(row) => (
                  <CropRow
                    key={row.plant?.id}
                    regionId={regionId}
                    row={row}
                    blocked={blocked}
                  />
                )}
              </Paged>
            </div>
          )}
          {full ? (
            <Muted variant='caption'>
              Its fields hold as many crops as a land can sow; clear one before
              sowing another.
            </Muted>
          ) : (
            <SowForm
              blocked={busy}
              pick='plant'
              onSow={(plant, next) =>
                sow.mutate({ region: regionId, plant, share: next })
              }
            />
          )}
        </div>
      )}
    </Section>
  )
}

function useWorldLife(worldId: number) {
  return useQuery({
    queryKey: floraKeys.life(worldId),
    queryFn: () =>
      unwrap(
        api.GET('/api/worlds/{world_id}/life', {
          params: { path: { world_id: worldId } },
        })
      ),
  })
}

export function WorldLifeSection({ worldId }: { worldId: number }) {
  const view = useWorldLife(worldId)
  const toggle = useWildAction<{ biochemistry: string; present: boolean }>(
    'world:life',
    (vars) => ({
      world_id: worldId,
      biochemistry: vars.biochemistry,
      present: vars.present,
    })
  )
  const { reason } = useGodGate()
  const blocked = reason() ?? (toggle.isPending ? WORKING : null)
  const data: WorldLife | undefined = view.data
  return (
    <Section
      id='section-world-life'
      title='Life it can bear'
      description='The kinds of life this world bears. A kind lives, spreads and is carried here only if its world bears its kind of life; void and spirit life live anywhere.'
      icon={Sprout}
      tone='success'
    >
      {view.isPending && <LoadingBlock label='Reading its life' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Its life could not be read'
          description={view.error.message}
        />
      )}
      {data && (
        <div
          data-surface='WorldLife'
          className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3'
        >
          {data.kinds.map((row) => {
            const spec = named(BIOCHEMISTRY, row.biochemistry)
            return (
              <div
                key={row.biochemistry}
                className={cn(
                  'flex min-w-0 items-center gap-2 rounded-lg border p-2',
                  row.borne || row.anywhere
                    ? 'bg-muted/30'
                    : 'border-dashed opacity-70'
                )}
              >
                <Medallion
                  icon={spec.icon}
                  tone={row.borne || row.anywhere ? spec.tone : 'muted'}
                  size='sm'
                />
                <div className='flex min-w-0 flex-1 flex-col'>
                  <Text as='span' weight='medium' truncate>
                    {row.label}
                  </Text>
                  <Muted as='span' variant='caption' truncate>
                    {row.anywhere
                      ? 'Lives on any world'
                      : row.borne
                        ? 'This world bears it'
                        : 'This world does not bear it'}
                    {row.kinds > 0
                      ? ` · ${row.kinds} ${row.kinds === 1 ? 'kind' : 'kinds'} here`
                      : ''}
                  </Muted>
                </div>
                {!row.anywhere && (
                  <Button
                    size='sm'
                    variant={row.borne ? 'outline' : 'default'}
                    aria-pressed={row.borne}
                    disabled={blocked !== null}
                    disabledReason={blocked ?? undefined}
                    onClick={() =>
                      toggle.mutate({
                        biochemistry: row.biochemistry,
                        present: !row.borne,
                      })
                    }
                  >
                    {row.borne ? 'Withhold' : 'Let it bear'}
                  </Button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </Section>
  )
}
