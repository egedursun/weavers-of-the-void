import { useMemo, useState } from 'react'
import {
  Ban,
  CalendarRange,
  Check,
  Coins,
  Landmark,
  Lock,
  Mountain,
  Plus,
  Route,
  Trash2,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
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
import {
  ConfirmDialog,
  EmptyState,
  EntityLink,
  FormRow,
  IconStat,
  KpiTile,
  Medallion,
  Section,
  StatBar,
  Paged,
} from '@/components/domain'
import {
  type ComboboxOption,
  RecordCombobox,
} from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { FIELD_GRID, NumberField, PartHeader } from './EntityEconomy'
import { useTradeRoutes } from './api'
import { MODE, ROUTE_STATUS, type TradeMode } from './labels'
import {
  DANGERS,
  DANGER_FIELD,
  DANGER_KEYS,
  type DangerKey,
  CARRIER_CHOICES,
  LAND_DECIDES,
  MODE_CHOICES,
  NO_CARRIER,
  OPEN_ALL_YEAR,
  STATUS_CHOICES,
  seasonChoices,
  fieldLabel,
  seasonTone,
  seasonWord,
} from './routeLabels'

type Detail = components['schemas']['TradeRouteDetail']
type RouteView = components['schemas']['TradeRouteView']
type Toll = components['schemas']['TollView']
type Loss = components['schemas']['RouteLossView']

const WORKING = 'Working…'
const PERCENT = 100
const MARKETS = ['people', 'settlement']
const MASTERS = ['people', 'settlement', 'faction', 'cult', 'polity', 'mortal']

function useOptions(types: readonly string[]): ComboboxOption[] {
  const names = useNames()
  return useMemo(
    () =>
      (names.data ?? [])
        .filter(
          (row) =>
            row.kind === 'entity' &&
            types.includes(row.type) &&
            (row.status === null ||
              row.status === undefined ||
              row.status === 'canon')
        )
        .map((row) => ({
          value: String(row.id),
          label: row.name,
          hint: row.type.replaceAll('_', ' '),
        })),
    [names.data, types]
  )
}

function lossesBy(losses: Loss[]): Record<DangerKey, number> {
  const totals = Object.fromEntries(
    DANGER_KEYS.map((key) => [key, 0])
  ) as Record<DangerKey, number>
  for (const loss of losses) totals[loss.cause] += loss.units
  return totals
}

function culprits(losses: Loss[], cause: DangerKey): string[] {
  return [
    ...new Set(
      losses
        .filter((loss) => loss.cause === cause && loss.culprit_name)
        .map((loss) => loss.culprit_name)
    ),
  ]
}

export function RouteDangers({ route }: { route: Detail }) {
  const lost = lossesBy(route.losses)
  const worst = DANGER_KEYS.reduce((best, key) =>
    route.dangers[key] > route.dangers[best] ? key : best
  )
  const season = route.season_pct
  return (
    <div data-surface='RouteDangers' className='flex min-w-0 flex-col gap-3'>
      <PartHeader
        icon={DANGERS[worst].icon}
        title='What threatens the cargo'
        note='Each danger takes its share of the losses; the worst season holds cargo back on every kind of way.'
      />
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/route:grid-cols-2'>
        <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'>
          {DANGER_KEYS.map((key) => {
            const spec = DANGERS[key]
            const named = culprits(route.losses, key)
            return (
              <div
                key={key}
                data-danger={key}
                className='flex min-w-0 flex-col gap-1.5'
              >
                <StatBar
                  label={spec.label}
                  value={route.dangers[key]}
                  max={PERCENT}
                  icon={spec.icon}
                  tone={
                    spec.tone === 'danger'
                      ? 'destructive'
                      : spec.tone === 'warning'
                        ? 'warning'
                        : spec.tone === 'info'
                          ? 'info'
                          : 'verdigris'
                  }
                />
                <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
                  <Muted variant='caption'>{spec.hint}</Muted>
                  {lost[key] > 0 && (
                    <Badge size='sm' variant='destructive'>
                      <spec.icon />
                      {`${formatInteger(lost[key])} lost${named.length > 0 ? ` to ${named.join(', ')}` : ''}`}
                    </Badge>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        <div className='flex min-w-0 flex-col gap-3'>
          <KpiTile
            label='Worst season keeps'
            value={`${season}%`}
            icon={CalendarRange}
            tone={seasonTone(season)}
            meter={{
              value: season,
              max: PERCENT,
              label: 'Share of cargo still moving in the worst season',
            }}
            hint={seasonWord(season)}
          />
          {route.chokepoint && (
            <div className='flex min-w-0 items-center gap-2.5 rounded-md border surface-framed border-gild/70 bg-card p-3'>
              <Medallion icon={Mountain} tone='warning' size='sm' />
              <div className='flex min-w-0 flex-col'>
                <Text weight='medium'>A chokepoint</Text>
                <Muted variant='caption'>
                  Strategic goods pass here and no other way leads between its
                  markets; overtaxing it brings merchants to war.
                </Muted>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function TollDestination({ toll }: { toll: Toll }) {
  if (toll.polity_id === null) return null
  const own = toll.polity_id === toll.controller_id
  return (
    <span className='flex min-w-0 items-center gap-1.5'>
      <Coins aria-hidden='true' className='size-icon-sm shrink-0 text-info' />
      <Muted variant='caption'>
        {own ? 'Into the treasury of ' : 'A share goes to the treasury of '}
        <EntityLink kind='entity' id={String(toll.polity_id)}>
          {toll.polity_name}
        </EntityLink>
      </Muted>
    </span>
  )
}

function HeldList({
  route,
  busy,
  onRelease,
}: {
  route: RouteView
  busy: string | null
  onRelease: (keys: string[]) => void
}) {
  if (route.locked.length === 0) return null
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-2'>
      <Lock aria-hidden='true' className='size-icon-xs shrink-0 text-primary' />
      {route.locked.map((key) => (
        <Button
          key={key}
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => onRelease([key])}
        >
          <Unlock />
          {`Release ${fieldLabel(key).toLowerCase()}`}
        </Button>
      ))}
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => onRelease(route.locked)}
      >
        <Unlock />
        Let the world decide everything again
      </Button>
    </div>
  )
}

type Values = Record<string, string | number | boolean | number[] | null>

function numberOr(value: string, fallback: number): number {
  const parsed = Math.round(Number(value))
  return Number.isFinite(parsed) ? parsed : fallback
}

export function RouteEditor({
  route,
  busy,
}: {
  route: RouteView
  busy: string | null
}) {
  const masters = useOptions(MASTERS)
  const armies = useOptions(['army'])
  const [mode, setMode] = useState<string>(route.mode)
  const [status, setStatus] = useState<string>(route.status)
  const [closedSeason, setClosedSeason] = useState<string>(
    route.closed_season === null ? OPEN_ALL_YEAR : String(route.closed_season)
  )
  const [carrier, setCarrier] = useState<string>(route.carrier ?? NO_CARRIER)
  const [controller, setController] = useState<string | null>(
    route.controller_id === null ? null : String(route.controller_id)
  )
  const [blocker, setBlocker] = useState<string | null>(
    route.blockaded_by_id === null ? null : String(route.blockaded_by_id)
  )
  const [numbers, setNumbers] = useState<Record<string, string>>({
    capacity: String(route.capacity),
    danger: String(route.danger),
    danger_bandits: String(route.dangers.bandits),
    danger_beasts: String(route.dangers.beasts),
    danger_weather: String(route.dangers.weather),
    danger_sea: String(route.dangers.sea),
    season_pct: String(route.season_pct),
    length: String(route.length),
    renown: String(route.renown),
    culture: String(route.culture),
  })
  const [chokepoint, setChokepoint] = useState(route.chokepoint)
  const edit = useGodAction({
    run: (body: { values?: Values; release?: string[] }) =>
      unwrap(
        api.POST('/api/actions/trade_route:edit', {
          body: { route_id: route.route_id, ...body },
        })
      ),
  })
  const blocked = busy ?? (edit.isPending ? WORKING : null)
  const set = (key: string) => (value: string) =>
    setNumbers((current) => ({ ...current, [key]: value }))
  const hold = (key: string, value: Values[string]) =>
    edit.mutate({ values: { [key]: value } })
  const numberRow = (key: string, max?: number) => (
    <div key={key} className='flex min-w-0 items-end gap-2'>
      <div className='min-w-0 flex-1'>
        <NumberField
          label={fieldLabel(key)}
          aria={fieldLabel(key)}
          value={numbers[key]}
          max={max}
          onChange={set(key)}
        />
      </div>
      <Button
        size='icon'
        variant={route.locked.includes(key) ? 'default' : 'outline'}
        aria-label={`Hold ${fieldLabel(key).toLowerCase()}`}
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => hold(key, numberOr(numbers[key], 0))}
      >
        <Check />
      </Button>
    </div>
  )
  return (
    <div data-surface='RouteEditor' className='flex min-w-0 flex-col gap-4'>
      <HeldList
        route={route}
        busy={blocked}
        onRelease={(keys) => edit.mutate({ release: keys })}
      />
      <div className={`${FIELD_GRID} @md/route:grid-cols-2`}>
        <div className='flex min-w-0 items-end gap-2'>
          <div className='min-w-0 flex-1'>
            <MindPicker
              label='Way of travel'
              value={mode}
              table={MODE_CHOICES}
              blocked={blocked}
              onPick={setMode}
            />
          </div>
          <Button
            size='icon'
            variant={route.locked.includes('mode') ? 'default' : 'outline'}
            aria-label='Hold the way of travel'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => hold('mode', mode)}
          >
            <Check />
          </Button>
        </div>
        <div className='flex min-w-0 items-end gap-2'>
          <div className='min-w-0 flex-1'>
            <MindPicker
              label='State'
              value={status}
              table={STATUS_CHOICES}
              blocked={blocked}
              onPick={setStatus}
            />
          </div>
          <Button
            size='icon'
            variant={route.locked.includes('status') ? 'default' : 'outline'}
            aria-label='Hold the state'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => hold('status', status)}
          >
            <Check />
          </Button>
        </div>
        <div className='flex min-w-0 items-end gap-2'>
          <div className='min-w-0 flex-1'>
            <MindPicker
              label='Closed season'
              value={closedSeason}
              table={seasonChoices(route.seasons)}
              blocked={blocked}
              onPick={setClosedSeason}
            />
          </div>
          <Button
            size='icon'
            variant={
              route.locked.includes('closed_season') ? 'default' : 'outline'
            }
            aria-label='Hold the closed season'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() =>
              hold(
                'closed_season',
                closedSeason === OPEN_ALL_YEAR ? null : Number(closedSeason)
              )
            }
          >
            <Check />
          </Button>
        </div>
        <div className='flex min-w-0 items-end gap-2'>
          <div className='min-w-0 flex-1'>
            <MindPicker
              label='Carried by'
              value={carrier}
              table={CARRIER_CHOICES}
              blocked={blocked}
              onPick={setCarrier}
            />
          </div>
          <Button
            size='icon'
            variant={route.locked.includes('carrier') ? 'default' : 'outline'}
            aria-label='Hold the carrier'
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() =>
              hold('carrier', carrier === NO_CARRIER ? null : carrier)
            }
          >
            <Check />
          </Button>
        </div>
        <FormRow label='Master of the road'>
          {(id) => (
            <div className='flex min-w-0 items-center gap-2'>
              <div className='min-w-0 flex-1'>
                <RecordCombobox
                  id={id}
                  options={masters}
                  value={controller}
                  onChange={(next) => setController(next)}
                  placeholder='Choose who keeps the road'
                  clearable
                  aria-label='Master of the road'
                />
              </div>
              <Button
                size='icon'
                variant={
                  route.locked.includes('controller_entity_id')
                    ? 'default'
                    : 'outline'
                }
                aria-label='Hold the master of the road'
                disabled={blocked !== null}
                disabledReason={blocked ?? undefined}
                onClick={() =>
                  hold(
                    'controller_entity_id',
                    controller === null ? null : Number(controller)
                  )
                }
              >
                <Check />
              </Button>
            </div>
          )}
        </FormRow>
        <FormRow label='Blockaded by'>
          {(id) => (
            <div className='flex min-w-0 items-center gap-2'>
              <div className='min-w-0 flex-1'>
                <RecordCombobox
                  id={id}
                  options={armies}
                  value={blocker}
                  onChange={(next) => setBlocker(next)}
                  placeholder='No army bars the way'
                  clearable
                  aria-label='Blockading army'
                />
              </div>
              <Button
                size='icon'
                variant={
                  route.locked.includes('blockaded_by_entity_id')
                    ? 'default'
                    : 'outline'
                }
                aria-label='Hold the blockade'
                disabled={blocked !== null}
                disabledReason={blocked ?? undefined}
                onClick={() =>
                  hold(
                    'blockaded_by_entity_id',
                    blocker === null ? null : Number(blocker)
                  )
                }
              >
                <Check />
              </Button>
            </div>
          )}
        </FormRow>
      </div>
      <Label variant='overline'>Dangers and the year</Label>
      <div
        className={`${FIELD_GRID} @md/route:grid-cols-2 @3xl/route:grid-cols-3`}
      >
        {[
          'danger',
          ...DANGER_KEYS.map((key) => DANGER_FIELD[key]),
          'season_pct',
        ].map((key) => numberRow(key, PERCENT))}
      </div>
      <Label variant='overline'>Size and fame</Label>
      <div
        className={`${FIELD_GRID} @md/route:grid-cols-2 @3xl/route:grid-cols-4`}
      >
        {numberRow('capacity')}
        {numberRow('length')}
        {numberRow('renown', PERCENT)}
        {numberRow('culture', PERCENT)}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <label className='flex shrink-0 items-center gap-2'>
          <Switch
            checked={chokepoint}
            onCheckedChange={setChokepoint}
            aria-label='A chokepoint'
          />
          <Text as='span'>A chokepoint for strategic goods</Text>
        </label>
        <Button
          size='sm'
          variant={route.locked.includes('chokepoint') ? 'default' : 'outline'}
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => hold('chokepoint', chokepoint)}
        >
          <Check />
          Hold
        </Button>
      </div>
    </div>
  )
}

export function TollControls({
  route,
  busy,
}: {
  route: RouteView
  busy: string | null
}) {
  const masters = useOptions(MASTERS)
  const tolled = new Set(route.tolls.map((toll) => toll.region_id))
  const free = route.path.filter(
    (region) => !tolled.has(region) && !route.untolled.includes(region)
  )
  const [region, setRegion] = useState<string>(
    free.length > 0 ? String(free[0]) : ''
  )
  const [keeper, setKeeper] = useState<string | null>(null)
  const [rate, setRate] = useState('5')
  const raise = useGodAction({
    run: (body: {
      region: number
      controller: number | null
      rate: number | null
      release?: string[]
    }) =>
      unwrap(
        api.POST('/api/actions/trade_route:toll_stop', {
          body: {
            route_id: route.route_id,
            region_id: body.region,
            controller_id: body.controller,
            rate: body.rate,
            release: body.release ?? [],
          },
        })
      ),
  })
  const forbid = useGodAction({
    run: (region: number) =>
      unwrap(
        api.POST('/api/actions/trade_route:toll_remove', {
          body: { route_id: route.route_id, region_id: region },
        })
      ),
  })
  const allow = useGodAction({
    run: (region: number) =>
      unwrap(
        api.POST('/api/actions/trade_route:edit', {
          body: { route_id: route.route_id, release: [`untolled.${region}`] },
        })
      ),
  })
  const blocked =
    busy ??
    (raise.isPending || forbid.isPending || allow.isPending ? WORKING : null)
  const regionName = (id: number) =>
    route.region_names[String(id)] ?? `Land ${id}`
  const lands = Object.fromEntries(
    free.map((id) => [String(id), regionName(id)])
  )
  return (
    <div data-surface='TollControls' className='flex min-w-0 flex-col gap-3'>
      {route.tolls.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={route.tolls} as='li'>
            {(toll) => (
              <li
                key={toll.region_id}
                className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-framed border-gild/70 bg-card p-2.5'
              >
                <Landmark
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-muted-foreground'
                />
                <Text weight='medium' truncate>
                  {toll.region_name}
                </Text>
                {toll.controller_held && (
                  <Badge size='sm' variant='info'>
                    <Lock />
                    {`Kept by ${toll.controller_name} by your word`}
                  </Badge>
                )}
                <div className='ms-auto flex min-w-0 flex-wrap gap-2'>
                  {toll.controller_held && (
                    <Button
                      size='sm'
                      variant='outline'
                      disabled={blocked !== null}
                      disabledReason={blocked ?? undefined}
                      onClick={() =>
                        raise.mutate({
                          region: toll.region_id,
                          controller: null,
                          rate: null,
                          release: ['controller_entity_id'],
                        })
                      }
                    >
                      <Unlock />
                      Let the land choose its keeper
                    </Button>
                  )}
                  <Button
                    size='sm'
                    variant='outline'
                    disabled={blocked !== null}
                    disabledReason={blocked ?? undefined}
                    onClick={() => forbid.mutate(toll.region_id)}
                  >
                    <Ban />
                    Forbid any toll here
                  </Button>
                </div>
              </li>
            )}
          </Paged>
        </ul>
      )}
      {route.untolled.length > 0 && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Paged items={route.untolled}>
            {(id) => (
              <Button
                key={id}
                size='sm'
                variant='outline'
                disabled={blocked !== null}
                disabledReason={blocked ?? undefined}
                onClick={() => allow.mutate(id)}
              >
                <Unlock />
                {`Allow tolls in ${regionName(id)} again`}
              </Button>
            )}
          </Paged>
        </div>
      )}
      {free.length > 0 && (
        <div className={`${FIELD_GRID} @md/route:grid-cols-4`}>
          <MindPicker
            label='Land on the way'
            value={region}
            table={lands}
            blocked={blocked}
            onPick={setRegion}
          />
          <FormRow label='Toll taken by'>
            {(id) => (
              <RecordCombobox
                id={id}
                options={masters}
                value={keeper}
                onChange={(next) => setKeeper(next)}
                placeholder='Choose a toll-taker'
                aria-label='Toll taken by'
              />
            )}
          </FormRow>
          <NumberField
            label='Toll %'
            aria='New toll rate'
            value={rate}
            max={PERCENT}
            onChange={setRate}
          />
          <Button
            size='sm'
            className='justify-self-start'
            disabled={blocked !== null || keeper === null || region === ''}
            disabledReason={
              blocked ??
              (keeper === null ? 'Choose who takes the toll' : undefined)
            }
            onClick={() =>
              raise.mutate({
                region: Number(region),
                controller: keeper === null ? null : Number(keeper),
                rate: numberOr(rate, 0),
              })
            }
          >
            <Plus />
            Raise a toll here
          </Button>
        </div>
      )}
    </div>
  )
}

export function StrikeRoute({
  route,
  busy,
}: {
  route: RouteView
  busy: string | null
}) {
  const [open, setOpen] = useState(false)
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/trade_route:delete', {
          body: { route_id: route.route_id },
        })
      ),
    onDone: () => setOpen(false),
  })
  if (route.status === 'decayed') return null
  return (
    <>
      <Button
        size='sm'
        variant='destructive'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => setOpen(true)}
      >
        <Trash2 />
        Strike the route from the world
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        destructive
        title={`Strike ${route.name}?`}
        desc='Grass grows over the way and merchants forget it. Merchants may find a new way between its markets later; close the route instead to keep them from it. The ledger can undo this.'
        confirmText='Strike it'
        isLoading={strike.isPending}
        handleConfirm={() => strike.mutate(undefined)}
      />
    </>
  )
}

export function FoundRouteDialog({
  firstId,
  triggerLabel = 'Lay out a new route',
}: {
  firstId?: number
  triggerLabel?: string
}) {
  const { reason } = useGodGate()
  const markets = useOptions(MARKETS)
  const masters = useOptions(MASTERS)
  const [open, setOpen] = useState(false)
  const [first, setFirst] = useState<string | null>(
    firstId === undefined ? null : String(firstId)
  )
  const [second, setSecond] = useState<string | null>(null)
  const [mode, setMode] = useState<string>(LAND_DECIDES)
  const [keeper, setKeeper] = useState<string | null>(null)
  const [toll, setToll] = useState('10')
  const found = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/trade_route:found', {
          body: {
            first_id: Number(first),
            second_id: Number(second),
            mode: mode === LAND_DECIDES ? null : (mode as TradeMode),
            controller_id: keeper === null ? null : Number(keeper),
            toll_pct: keeper === null || toll === '' ? null : numberOr(toll, 0),
          },
        })
      ),
    onDone: () => setOpen(false),
  })
  const missing =
    first === null || second === null
      ? 'Choose both markets'
      : first === second
        ? 'Choose two different markets'
        : null
  const blocked = reason() ?? (found.isPending ? WORKING : null) ?? missing
  const modes = { [LAND_DECIDES]: 'Let the land decide', ...MODE_CHOICES }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size='sm'>
          <Route />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent data-surface='FoundRouteDialog'>
        <DialogHeader>
          <DialogTitle>Lay out a trade route</DialogTitle>
          <DialogDescription>
            Join two markets by a road merchants know. Choose how goods travel,
            who keeps the road and the toll they take; what you choose is held
            until you release it.
          </DialogDescription>
        </DialogHeader>
        <div className='flex min-w-0 flex-col gap-3'>
          <FormRow label='First market'>
            {(id) => (
              <RecordCombobox
                id={id}
                options={markets}
                value={first}
                onChange={(next) => setFirst(next)}
                placeholder='A people or settlement'
                aria-label='First market'
              />
            )}
          </FormRow>
          <FormRow label='Second market'>
            {(id) => (
              <RecordCombobox
                id={id}
                options={markets}
                value={second}
                onChange={(next) => setSecond(next)}
                placeholder='A people or settlement'
                aria-label='Second market'
              />
            )}
          </FormRow>
          <MindPicker
            label='Way of travel'
            value={mode}
            table={modes}
            blocked={null}
            onPick={setMode}
          />
          {mode !== LAND_DECIDES && (
            <div className='flex min-w-0 items-center gap-2'>
              <Medallion
                icon={MODE[mode as TradeMode].icon}
                tone={MODE[mode as TradeMode].tone}
                size='sm'
              />
              <Muted variant='caption'>{`${MODE[mode as TradeMode].label}: its own seasons, dangers and capacity.`}</Muted>
            </div>
          )}
          <FormRow label='Keeper of the road (optional)'>
            {(id) => (
              <RecordCombobox
                id={id}
                options={masters}
                value={keeper}
                onChange={(next) => setKeeper(next)}
                placeholder='No one in particular'
                clearable
                aria-label='Keeper of the road'
              />
            )}
          </FormRow>
          {keeper !== null && (
            <NumberField
              label='Toll the keeper takes %'
              aria='Toll the keeper takes'
              value={toll}
              max={PERCENT}
              onChange={setToll}
            />
          )}
        </div>
        <DialogFooter>
          <Button
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            onClick={() => found.mutate(undefined)}
          >
            <Route />
            Lay the road
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function CommunityRoutes({ communityId }: { communityId: number }) {
  const routes = useTradeRoutes(null)
  const mine = (routes.data ?? []).filter(
    (route) => route.first_id === communityId || route.second_id === communityId
  )
  return (
    <Section
      id='section-community-routes'
      title='Trade roads'
      description='Every road that ends here, what threatens it and how hard its worst season bites. Open a road to command it.'
      icon={Route}
    >
      <div
        data-surface='CommunityRoutes'
        className='@container/route flex min-w-0 flex-col gap-3'
      >
        <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
          <Muted variant='caption'>{`${mine.length} ${mine.length === 1 ? 'road ends' : 'roads end'} here.`}</Muted>
          <FoundRouteDialog
            firstId={communityId}
            triggerLabel='Lay a road from here'
          />
        </div>
        {mine.length === 0 ? (
          <EmptyState
            icon={Route}
            title='No road ends here'
            description='Merchants open one once goods are dearer elsewhere, or lay one yourself.'
          />
        ) : (
          <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/route:grid-cols-2'>
            <Paged items={mine} as='li'>
              {(route) => {
                const other =
                  route.first_id === communityId
                    ? { id: route.second_id, name: route.second_name }
                    : { id: route.first_id, name: route.first_name }
                const mode = MODE[route.mode]
                const status = ROUTE_STATUS[route.status]
                return (
                  <li
                    key={route.route_id}
                    data-route={route.route_id}
                    className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
                  >
                    <div className='flex min-w-0 items-center gap-2.5'>
                      <Medallion
                        icon={mode.icon}
                        tone={status.tone}
                        size='sm'
                      />
                      <div className='flex min-w-0 flex-1 flex-col'>
                        <EntityLink kind='entity' id={String(route.route_id)}>
                          {route.name}
                        </EntityLink>
                        <Muted variant='caption' truncate>
                          {'To '}
                          <EntityLink kind='entity' id={String(other.id)}>
                            {other.name}
                          </EntityLink>
                          {` by ${mode.label.toLowerCase()}`}
                        </Muted>
                      </div>
                      <Badge size='sm' variant={status.variant}>
                        <status.icon />
                        {status.label}
                      </Badge>
                    </div>
                    <div className='flex min-w-0 flex-wrap gap-1.5'>
                      {DANGER_KEYS.filter((key) => route.dangers[key] > 0).map(
                        (key) => {
                          const spec = DANGERS[key]
                          return (
                            <IconStat
                              key={key}
                              icon={spec.icon}
                              label={spec.hint}
                              value={`${spec.label} ${route.dangers[key]}`}
                              tone={spec.tone}
                            />
                          )
                        }
                      )}
                      <IconStat
                        icon={CalendarRange}
                        label='Share of cargo still moving in the worst season'
                        value={`${route.season_pct}% worst season`}
                        tone={seasonTone(route.season_pct)}
                      />
                      {route.chokepoint && (
                        <IconStat
                          icon={Mountain}
                          label='A chokepoint for strategic goods'
                          value='Chokepoint'
                          tone='warning'
                        />
                      )}
                    </div>
                  </li>
                )
              }}
            </Paged>
          </ul>
        )}
      </div>
    </Section>
  )
}
