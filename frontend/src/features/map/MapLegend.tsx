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
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Switch } from '@/components/ui/switch'
import { EntityLink } from '@/components/domain'
import { type ThemeColorName } from '@/components/domain/useThemeColors'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { ALL_FAMILIES, familyOf } from '@/features/graph/families'
import {
  BorderMarker,
  ClusterMarker,
  ColorSwatch,
  GlowMarker,
  HatchSwatch,
  IconMarker,
  LineMarker,
} from './SwatchMarker'
import { type MapView } from './api'
import { EVENT_ICON, SETTLEMENT_ICON, typeIcon } from './iconPaths'
import { EVENT_TOKEN } from './mapLayout'
import { LINE_STYLE, type LineKind, ROAD_KINDS, ROUTE_KINDS } from './mapLines'
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
  route: 'brand-gold',
  route_busy: 'brand-gold',
  route_blocked: 'destructive',
  outbreak: 'destructive',
}

const LINE_NOTE: Partial<Record<LineKind, string>> = {
  trade_road: 'goods flow along it',
  outbreak: 'the sickness spreads this way',
  trade: 'trade with no road between',
  rule: 'arrow points at the ruled',
  hunt: 'arrow points at the prey',
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
      {palette.categories.map((category) => {
        const id = Number(category.key.split(':')[1])
        const entry = byRuler.get(id)
        return (
          <Row
            key={category.key}
            icon={<ColorSwatch token={category.token} color={category.color} />}
          >
            <div className='flex min-w-0 flex-col'>
              <EntityLink kind='entity' id={String(id)}>
                {entry?.name ?? category.label}
              </EntityLink>
              <Muted variant='caption'>{entry?.regions.join(', ')}</Muted>
            </div>
          </Row>
        )
      })}
    </ul>
  )
}

function CategoryRows({ palette }: { palette: LayerPalette }) {
  return (
    <ul className='flex min-w-0 flex-col gap-1.5'>
      {palette.categories.map((category) => (
        <Row
          key={category.key}
          icon={<ColorSwatch token={category.token} color={category.color} />}
        >
          <Text as='span' truncate className='flex-1'>
            {category.label}
          </Text>
          <Stat value={category.count} />
        </Row>
      ))}
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
          <Muted variant='caption'>{`Contested: no ruler holds it firmly (${palette.contested.size} regions)`}</Muted>
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
    ...view.relations.map((line) => line.kind as LineKind),
    ...(view.trade ?? []).map((route): LineKind =>
      route.status === 'blockaded' ? 'route_blocked' : 'route'
    ),
  ])
  const lines = [...lineKinds].filter((kind) =>
    ROUTE_KINDS.has(kind)
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
      <Block title='Markers' defaultOpen={!layerTitle}>
        {!anyMarker && <Muted>No markers on this map yet.</Muted>}
        {fallenCount > 0 && (
          <div className='flex min-w-0 items-center gap-2'>
            <Switch
              id={fallenId}
              checked={filter.fallen}
              onCheckedChange={onFallen}
            />
            <Label as='label' htmlFor={fallenId} className='min-w-0 flex-1'>
              Show the fallen
            </Label>
            <Stat value={fallenCount} />
          </div>
        )}
        <ul className='flex min-w-0 flex-col gap-1.5'>
          {families.map((family) => (
            <li key={family.key} className='flex min-w-0 flex-col gap-1'>
              <Label variant='overline'>{family.label}</Label>
              <ul className='flex min-w-0 flex-col gap-1'>
                {family.types
                  .filter((type) =>
                    markers.some((point) => point.type === type)
                  )
                  .map((type) => (
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
                  ))}
              </ul>
            </li>
          ))}
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
          {eventKinds.map((kind) => (
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
          ))}
          {lines.map((kind) => (
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
          ))}
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
      <Label variant='overline'>{`${markers.length} markers · ${view.geometry.regions.length} regions`}</Label>
    </div>
  )
}
