import { type ReactNode, useId } from 'react'
import {
  ChevronDown,
  Crown,
  MapPin,
  Swords,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { formatNumber } from '@/lib/format'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Switch } from '@/components/ui/switch'
import { EntityLink, Paged, FieldTile } from '@/components/domain'
import { type ThemeColorName } from '@/components/domain/useThemeColors'
import { Label, Muted, Stat, Text } from '@/components/typography'
import {
  PASSAGE_STATE,
  STRATUM,
} from '@/features/entity/environment/geologyLabels'
import { ALL_FAMILIES, familyOf } from '@/features/graph/families'
import {
  BorderMarker,
  ClusterMarker,
  ColorSwatch,
  GlowMarker,
  HatchSwatch,
  IconMarker,
  LineMarker,
  ShaftMarker,
  StratumSwatch,
} from './SwatchMarker'
import { type MapView } from './api'
import { shaftsOf } from './deepLayer'
import {
  PASSAGE_LOOK,
  ROCK_SEAM_TOKEN,
  ROCK_TOKEN,
  SEABED_TOKEN,
  STRATUM_LOOK,
} from './deepLooks'
import { EVENT_ICON, SETTLEMENT_ICON, typeIcon } from './iconPaths'
import { EVENT_TOKEN } from './mapLayout'
import {
  LINE_STYLE,
  type LineKind,
  PASSAGE_KINDS,
  ROAD_KINDS,
  ROUTE_KINDS,
  relationLine,
} from './mapLines'
import {
  type LayerMode,
  type Overlay,
  type PositionedPoint,
  SETTLEMENT_TIERS,
  TIER_LABEL,
  isDead,
  populationTrend,
} from './mapModel'
import { type MarkerFilter, type Thresholds } from './mapScene'
import { EVENT_KIND_LABEL, LINE_LABEL, typeName } from './mapText'
import { type LayerPalette } from './useLayerPalette'

const LAYER_TITLE: Partial<Record<LayerMode, string>> = {
  political: 'Political control',
  religions: 'Dominant faith',
  languages: 'Dominant language',
  creators: 'Region creators',
  regions: 'Regions',
}

const LAYER_EMPTY: Partial<Record<LayerMode, string>> = {
  political: 'No community dominates any region yet.',
  religions: 'No god is worshipped in any region yet.',
  languages: 'No language is spoken in any region yet.',
  creators: 'There is no region on this map.',
  regions: 'There is no region on this map.',
}

const LINE_TOKEN: Record<LineKind, ThemeColorName> = {
  road: 'muted-foreground',
  trade_road: 'brand-gold',
  trade: 'brand-gold',
  hostility: 'destructive',
  rule: 'rarity-epic',
  hunt: 'destructive',
  conurbation: 'brand-gold',
  route: 'brand-gold',
  route_busy: 'brand-gold',
  route_blocked: 'destructive',
  outbreak: 'destructive',
  front: 'destructive',
  supply: 'brand-gold',
  passage_open: PASSAGE_LOOK.open.token,
  passage_digging: PASSAGE_LOOK.digging.token,
  passage_flooded: PASSAGE_LOOK.flooded.token,
  passage_collapsed: PASSAGE_LOOK.collapsed.token,
  passage_sealed: PASSAGE_LOOK.sealed.token,
}

const LINE_NOTE: Partial<Record<LineKind, string>> = {
  trade_road: 'goods flow along it',
  outbreak: 'the sickness spreads this way',
  trade: 'trade with no road between',
  rule: 'arrow points at the ruled',
  hunt: 'arrow points at the prey',
  conurbation: 'settlements grown into one city',
  passage_open: 'a way through the deep between two cells',
  passage_digging: 'still being dug',
  passage_flooded: 'water fills it',
  passage_collapsed: 'fallen in; it must be cleared',
  passage_sealed: 'closed by a seal',
}

type MapLegendProps = {
  view: MapView
  mode: LayerMode
  overlays: Record<Overlay, boolean>
  palette: LayerPalette | null
  points: readonly PositionedPoint[]
  filter: MarkerFilter
  onToggleType: (type: string, shown: boolean) => void
  onFallen: (shown: boolean) => void
  thresholds: Thresholds
  trendPct: number
  typeLabels: ReadonlyMap<string, string>
  tierOfPoint: (id: number) => (typeof SETTLEMENT_TIERS)[number]
}

function Block({
  title,
  defaultOpen,
  children,
}: {
  title: string
  defaultOpen: boolean
  children: ReactNode
}) {
  return (
    <Collapsible
      defaultOpen={defaultOpen}
      className='flex min-w-0 flex-col gap-2'
    >
      <CollapsibleTrigger asChild>
        <Button variant='ghost' size='sm' className='group justify-between'>
          {title}
          <ChevronDown className='transition-transform group-aria-expanded:rotate-180' />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-2'>
        {children}
      </CollapsibleContent>
    </Collapsible>
  )
}

function Row({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <li className='flex min-w-0 items-center gap-2'>
      {icon}
      <div className='flex min-w-0 flex-1 items-baseline gap-2'>{children}</div>
    </li>
  )
}

function TypeRow({
  type,
  token,
  label,
  count,
  shown,
  onToggle,
}: {
  type: string
  token: ThemeColorName
  label: string
  count: number
  shown: boolean
  onToggle: (type: string, shown: boolean) => void
}) {
  const id = useId()
  return (
    <li className='flex min-w-0 items-center gap-2'>
      <Checkbox
        id={id}
        checked={shown}
        onCheckedChange={(checked) => onToggle(type, checked === true)}
        aria-label={`Show ${label} on the map`}
      />
      <IconMarker icon={typeIcon(type)} token={token} />
      <Label as='label' htmlFor={id} className='min-w-0 flex-1 truncate'>
        {label}
      </Label>
      <Stat value={count} />
    </li>
  )
}

function PoliticalRows({
  view,
  palette,
}: {
  view: MapView
  palette: LayerPalette
}) {
  const regionName = new Map(
    view.points.map((point) => [point.entity.id, point.entity.name])
  )
  const byRuler = new Map<number, { name: string; regions: string[] }>()
  for (const [regionId, control] of Object.entries(view.political)) {
    const entry = byRuler.get(control.ruler_id) ?? {
      name: control.ruler_name,
      regions: [],
    }
    entry.regions.push(
      `${regionName.get(Number(regionId)) ?? 'Region'} ${Math.round(control.share)}%${control.contested ? ' · contested' : ''}`
    )
    byRuler.set(control.ruler_id, entry)
  }
  return (
    <ul className='flex min-w-0 flex-col gap-2'>
      <Paged items={palette.categories} as='li'>
        {(category) => {
          const id = Number(category.key.split(':')[1])
          const entry = byRuler.get(id)
          return (
            <Row
              key={category.key}
              icon={
                <ColorSwatch token={category.token} color={category.color} />
              }
            >
              <div className='flex min-w-0 flex-col'>
                <EntityLink kind='entity' id={String(id)}>
                  {entry?.name ?? category.label}
                </EntityLink>
                <Muted variant='caption'>{entry?.regions.join(', ')}</Muted>
              </div>
            </Row>
          )
        }}
      </Paged>
    </ul>
  )
}

function CategoryRows({ palette }: { palette: LayerPalette }) {
  return (
    <ul className='flex min-w-0 flex-col gap-1.5'>
      <Paged items={palette.categories} as='li'>
        {(category) => (
          <Row
            key={category.key}
            icon={<ColorSwatch token={category.token} color={category.color} />}
          >
            <Text as='span' truncate className='flex-1'>
              {category.label}
            </Text>
            <Stat value={category.count} />
          </Row>
        )}
      </Paged>
    </ul>
  )
}

function DomainKey({
  mode,
  palette,
}: {
  mode: LayerMode
  palette: LayerPalette
}) {
  if (mode === 'regions' || palette.categories.length === 0) return null
  return (
    <ul className='flex min-w-0 flex-col gap-1.5'>
      <Row icon={<BorderMarker />}>
        <Muted variant='caption'>
          Where one colour meets another; the colour deepens along its edge.
        </Muted>
      </Row>
      {palette.contested.size > 0 && (
        <Row icon={<HatchSwatch />}>
          <Muted variant='caption'>{`Contested: no ruler holds it firmly (${plural(palette.contested.size, 'region', 'regions')})`}</Muted>
        </Row>
      )}
      {palette.rulers.size > 0 && (
        <Row
          icon={
            <Crown
              aria-hidden='true'
              className='size-icon-md text-brand-gold'
            />
          }
        >
          <Muted variant='caption'>Seat of a ruler</Muted>
        </Row>
      )}
    </ul>
  )
}

const STATES_SHOWN = Object.keys(PASSAGE_LOOK).length

function DeepKey({ view }: { view: MapView }) {
  const level = view.level
  if (!level) return null
  const look = STRATUM_LOOK[level.stratum]
  const stratum = STRATUM[level.stratum]
  const shafts = shaftsOf(view)
  const states = new Set(shafts.map((shaft) => shaft.state))
  const glyphs = new Set(shafts.map((shaft) => shaft.glyph))
  return (
    <Block title='The deep' defaultOpen>
      <ul className='flex min-w-0 flex-col gap-1.5'>
        <Row icon={<StratumSwatch fill={look.fill} glow={look.glow} />}>
          <Text as='span' truncate className='flex-1'>
            {stratum.label}
          </Text>
          <Muted variant='caption'>{`${plural(level.cells.length, 'cell', 'cells')}`}</Muted>
        </Row>
        <Row icon={<IconMarker icon={stratum.icon} token={look.glow} />}>
          <Muted variant='caption'>{stratum.hint}</Muted>
        </Row>
        <Row icon={<ColorSwatch token={ROCK_TOKEN} />}>
          <Text as='span'>Solid rock</Text>
          <Muted variant='caption'>no hollow at this depth</Muted>
        </Row>
        <Row icon={<ColorSwatch token={SEABED_TOKEN} />}>
          <Text as='span'>Rock beneath the sea</Text>
        </Row>
        <Row icon={<LineMarker token={look.glow} width={2} />}>
          <Text as='span'>Edge of a hollow</Text>
          <Muted variant='caption'>brighter where its light is greater</Muted>
        </Row>
        <Row icon={<LineMarker token={ROCK_SEAM_TOKEN} width={1} dash='3 2' />}>
          <Text as='span'>The coast above</Text>
        </Row>
        {glyphs.has('shaft') && (
          <Row icon={<ShaftMarker token={look.glow} shape='shaft' up />}>
            <Text as='span'>Shaft to another depth</Text>
          </Row>
        )}
        {glyphs.has('mouth') && (
          <Row icon={<ShaftMarker token={look.glow} shape='mouth' up />}>
            <Text as='span'>Way up to the surface</Text>
          </Row>
        )}
        <Paged items={[...states].sort()} initial={STATES_SHOWN} as='li'>
          {(state) => (
            <Row
              key={state}
              icon={<ColorSwatch token={PASSAGE_LOOK[state].token} />}
            >
              <Text as='span'>{PASSAGE_STATE[state].label}</Text>
              <Muted variant='caption'>shaft or way up in this state</Muted>
            </Row>
          )}
        </Paged>
      </ul>
    </Block>
  )
}

function WaysDown({ view }: { view: MapView }) {
  const openings = view.deep?.openings ?? []
  if (view.level || openings.length === 0) return null
  const states = [...new Set(openings.map((opening) => opening.state))].sort()
  return (
    <Block title='Ways down' defaultOpen={false}>
      <ul className='flex min-w-0 flex-col gap-1.5'>
        <Paged items={states} initial={STATES_SHOWN} as='li'>
          {(state) => (
            <Row
              key={state}
              icon={
                <ShaftMarker
                  token={PASSAGE_LOOK[state].token}
                  shape='mouth'
                  up={false}
                />
              }
            >
              <Text as='span'>{`${PASSAGE_STATE[state].label} way down`}</Text>
              <Muted variant='caption'>{`${openings.filter((opening) => opening.state === state).length}`}</Muted>
            </Row>
          )}
        </Paged>
      </ul>
    </Block>
  )
}

export function MapLegend({
  view,
  mode,
  overlays,
  palette,
  points,
  filter,
  onToggleType,
  onFallen,
  thresholds,
  trendPct,
  typeLabels,
  tierOfPoint,
}: MapLegendProps) {
  const fallenId = useId()
  const layerTitle = LAYER_TITLE[mode]
  const regionIds = new Set(view.geometry.regions.map((region) => region.id))
  const stacked = new Set([
    ...view.markers.map((marker) => marker.id),
    ...view.wars.map((war) => war.id),
  ])
  const markers = points.filter(
    (point) => !regionIds.has(point.id) && !stacked.has(point.id)
  )
  const fallenCount = markers.filter((point) => isDead(point.status)).length
  const settlements = markers.filter((point) => point.type === 'settlement')
  const tiers = new Set(settlements.map((point) => tierOfPoint(point.id)))
  const families = ALL_FAMILIES.filter((family) =>
    markers.some((point) => familyOf(point.type).key === family.key)
  )
  const trends = new Set(
    Object.values(view.settlements)
      .map((info) =>
        populationTrend(info.population, info.previous_population, trendPct)
      )
      .filter(Boolean)
  )
  const eventKinds = overlays.events
    ? [...new Set(view.markers.map((marker) => marker.kind))].filter(
        (kind) => !(overlays.wars && kind === 'battle')
      )
    : []
  const lineKinds = new Set<LineKind>([
    ...view.roads.map((road): LineKind =>
      road.kind === 'trade' ? 'trade_road' : 'road'
    ),
    ...view.relations.map((line) => relationLine(view, line)),
    ...(view.trade ?? []).map((route): LineKind =>
      route.status === 'blockaded' ? 'route_blocked' : 'route'
    ),
  ])
  const lines = [...lineKinds].filter((kind) =>
    PASSAGE_KINDS.has(kind)
      ? true
      : ROUTE_KINDS.has(kind)
        ? overlays.trade
        : ROAD_KINDS.has(kind)
          ? overlays.roads
          : overlays.ties
  )
  const ongoing = view.wars.some((war) => war.ongoing)
  const threshold: Record<string, string> = {
    village: `< ${formatNumber(thresholds.town)}`,
    town: `≥ ${formatNumber(thresholds.town)}`,
    city: `≥ ${formatNumber(thresholds.city)}`,
    great_city: `≥ ${formatNumber(thresholds.greatCity)}`,
    megacity: `≥ ${formatNumber(thresholds.megacity)}`,
    conurbation: `≥ ${formatNumber(thresholds.conurbation)}`,
    capital: 'most populous of a ruler',
  }
  const anyMarker =
    families.length + eventKinds.length + lines.length > 0 ||
    (overlays.wars && view.wars.length > 0) ||
    view.notes.length > 0
  return (
    <div data-map-legend className='flex min-w-0 flex-col gap-3'>
      {layerTitle && palette && (
        <Block title={layerTitle} defaultOpen>
          {palette.categories.length === 0 ? (
            <Muted>{LAYER_EMPTY[mode]}</Muted>
          ) : mode === 'political' ? (
            <PoliticalRows view={view} palette={palette} />
          ) : (
            <CategoryRows palette={palette} />
          )}
          <DomainKey mode={mode} palette={palette} />
        </Block>
      )}
      {view.level ? (
        <DeepKey view={view} />
      ) : (
        <Block title='The land' defaultOpen={false}>
          <ul className='flex min-w-0 flex-col gap-1.5'>
            <Paged items={view.geometry.palette.biome_names} as='li'>
              {(name, index) => (
                <Row
                  key={name}
                  icon={
                    <ColorSwatch
                      color={view.geometry.palette.biome_colours[index]}
                    />
                  }
                >
                  <Text as='span' truncate className='flex-1'>
                    {name.replaceAll('_', ' ')}
                  </Text>
                </Row>
              )}
            </Paged>
          </ul>
        </Block>
      )}
      <WaysDown view={view} />
      <Block title='Markers' defaultOpen={!layerTitle}>
        {!anyMarker && <Muted>No markers on this map yet.</Muted>}
        {fallenCount > 0 && (
          <FieldTile id={fallenId} label='Show the fallen'>
            <div className='flex min-w-0 items-center justify-between gap-2'>
              <Switch
                id={fallenId}
                checked={filter.fallen}
                onCheckedChange={onFallen}
              />
              <Stat value={fallenCount} />
            </div>
          </FieldTile>
        )}
        <ul className='flex min-w-0 flex-col gap-1.5'>
          <Paged items={families} as='li'>
            {(family) => (
              <li key={family.key} className='flex min-w-0 flex-col gap-1'>
                <Label variant='overline'>{family.label}</Label>
                <ul className='flex min-w-0 flex-col gap-1'>
                  <Paged
                    items={family.types.filter((type) =>
                      markers.some((point) => point.type === type)
                    )}
                    as='li'
                  >
                    {(type) => (
                      <TypeRow
                        key={type}
                        type={type}
                        token={
                          type === 'settlement' ? 'brand-gold' : family.token
                        }
                        label={typeName(type, typeLabels)}
                        count={
                          markers.filter((point) => point.type === type).length
                        }
                        shown={!filter.hiddenTypes.has(type)}
                        onToggle={onToggleType}
                      />
                    )}
                  </Paged>
                </ul>
              </li>
            )}
          </Paged>
          {markers.length > 1 && (
            <Row icon={<ClusterMarker />}>
              <Muted variant='caption'>
                Records close together gather under one mark; the number counts
                them and the ring shows their kinds. Click to list them all.
              </Muted>
            </Row>
          )}
          {SETTLEMENT_TIERS.filter((tier) => tiers.has(tier)).map((tier) => (
            <Row
              key={tier}
              icon={
                <IconMarker icon={SETTLEMENT_ICON[tier]} token='brand-gold' />
              }
            >
              <Text as='span' truncate className='flex-1'>
                {TIER_LABEL[tier]}
              </Text>
              <Muted variant='caption'>{threshold[tier]}</Muted>
            </Row>
          ))}
          {trends.has('up') && (
            <Row
              icon={
                <TrendingUp
                  aria-hidden='true'
                  className='size-icon-md text-success'
                />
              }
            >
              <Text as='span'>Population rising</Text>
            </Row>
          )}
          {trends.has('down') && (
            <Row
              icon={
                <TrendingDown
                  aria-hidden='true'
                  className='size-icon-md text-destructive'
                />
              }
            >
              <Text as='span'>Population falling</Text>
            </Row>
          )}
          <Paged items={eventKinds} as='li'>
            {(kind) => (
              <Row
                key={kind}
                icon={
                  <IconMarker
                    icon={EVENT_ICON[kind] ?? EVENT_ICON.event}
                    token={
                      (EVENT_TOKEN[kind] as ThemeColorName | null) ??
                      'muted-foreground'
                    }
                  />
                }
              >
                <Text as='span'>{EVENT_KIND_LABEL[kind] ?? kind}</Text>
              </Row>
            )}
          </Paged>
          <Paged items={lines} as='li'>
            {(kind) => (
              <Row
                key={kind}
                icon={
                  <LineMarker
                    token={LINE_TOKEN[kind]}
                    width={LINE_STYLE[kind].main.width}
                    dash={LINE_STYLE[kind].main.dash?.join(' ')}
                  />
                }
              >
                <Text as='span'>{LINE_LABEL[kind]}</Text>
                {LINE_NOTE[kind] && (
                  <Muted variant='caption'>{LINE_NOTE[kind]}</Muted>
                )}
              </Row>
            )}
          </Paged>
          {overlays.wars && view.wars.length > 0 && (
            <>
              <Row icon={<IconMarker icon={Swords} token='destructive' />}>
                <Text as='span'>War</Text>
                <Muted variant='caption'>
                  {ongoing
                    ? 'pulses while it lasts; with its battles'
                    : 'with its battles'}
                </Muted>
              </Row>
              <Row icon={<GlowMarker />}>
                <Muted variant='caption'>
                  The redder the ground, the more blood spilled there.
                </Muted>
              </Row>
            </>
          )}
          {view.notes.length > 0 && (
            <Row
              icon={
                <MapPin
                  aria-hidden='true'
                  className='size-icon-md text-primary'
                />
              }
            >
              <Text as='span'>Your note</Text>
            </Row>
          )}
        </ul>
      </Block>
      <Label variant='overline'>{`${plural(markers.length, 'marker', 'markers')} · ${plural(view.geometry.regions.length, 'region', 'regions')}`}</Label>
    </div>
  )
}
