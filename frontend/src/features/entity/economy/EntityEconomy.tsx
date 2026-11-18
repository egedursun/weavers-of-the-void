import { type ReactNode, useId, useState } from 'react'
import {
  ArrowRight,
  Ban,
  Check,
  CircleCheck,
  CirclePause,
  Coins,
  Factory,
  Hourglass,
  Minus,
  Package,
  PencilRuler,
  Plus,
  Ship,
  SlidersHorizontal,
  Store,
  Trash2,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Flourish } from '@/components/ui/ornate'
import { Progress } from '@/components/ui/progress'
import {
  EmptyState,
  EntityLink,
  FieldTile,
  IconStat,
  type KpiTone,
  LoadingBlock,
  Medallion,
  MiniStat,
  Paged,
  Section,
} from '@/components/domain'
import { Label, Muted, SectionTitle, Stat, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { ControlPanel, MindPicker } from '../mind/parts'
import { HoardControl } from './HoardControl'
import {
  ECONOMY_REFRESH,
  useCommunityEconomy,
  useCurrencies,
  useWorkshopDesigns,
} from './api'
import {
  COMMODITY,
  type CommodityKind,
  GOODS_FAMILY,
  type GoodsFamily,
  MATERIAL_LABEL,
  type Named,
  STORE,
  STORE_KINDS,
  SPOILING_FLOWS,
  type StoreKind,
  WORKSHOP,
  type WorkshopKind,
  qualityTier,
} from './labels'
import { NONE, WORKING, materialRef, whole } from './model'
import {
  ChoiceSelect,
  EntityChoice,
  HeldBadge,
  MaterialSelect,
  ReleaseButton,
} from './parts'

type Economy = components['schemas']['CommunityEconomyView']
type ChainStep = components['schemas']['ChainStepView']
type Lot = components['schemas']['StockLotView']
type Workshop = components['schemas']['WorkshopView']
type Design = components['schemas']['WorkshopDesignView']

const PERCENT = 100
const SHORT = 50
const PIPS = 5
const NO_COIN = 'none'
const STRUCTURE_TYPES = ['structure'] as const
const FAMILIES = Object.keys(GOODS_FAMILY) as GoodsFamily[]
const COMMODITY_CHOICES = Object.fromEntries(
  Object.entries(COMMODITY).map(([key, item]) => [key, item.label])
)
const WORKSHOP_CHOICES = Object.fromEntries(
  Object.entries(WORKSHOP).map(([key, item]) => [key, item.label])
)

const TONE_BORDER: Record<KpiTone, string> = {
  gold: 'border-primary/30',
  verdigris: 'border-brand-verdigris/30',
  info: 'border-info/30',
  success: 'border-success/30',
  warning: 'border-warning/40 bg-warning/5',
  danger: 'border-destructive/40 bg-destructive/5',
  muted: 'border-border',
}

const PIP_TONE: Record<KpiTone, string> = {
  gold: 'bg-primary',
  verdigris: 'bg-brand-verdigris',
  info: 'bg-info',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-destructive',
  muted: 'bg-muted-foreground',
}

function MarketQuotes({ economy }: { economy: Economy }) {
  return (
    <div data-surface='MarketQuotes' className='flex min-w-0 flex-col gap-3'>
      <PartHeader
        icon={Store}
        title='Market prices'
        note='What each good fetches here this epoch, how much is offered and wanted, what came in and went out, and how far the price swung.'
      />
      {economy.quotes.length === 0 ? (
        <EmptyState
          icon={Store}
          size='inline'
          title='No market prices here yet'
          description='Prices appear once the community trades at a market.'
        />
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/econ:grid-cols-2 @4xl/econ:grid-cols-3'>
          <Paged items={economy.quotes} as='li'>
            {(quote) => (
              <li
                key={quote.commodity}
                className='flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-gild/60 bg-card p-2'
              >
                <div className='flex min-w-0 items-center justify-between gap-2'>
                  <Text as='span' weight='semibold' truncate>
                    {COMMODITY[quote.commodity].label}
                  </Text>
                  <Badge
                    size='sm'
                    variant={
                      quote.swing > 0
                        ? 'warning'
                        : quote.swing < 0
                          ? 'success'
                          : 'outline'
                    }
                  >
                    {`${formatInteger(quote.price)}${quote.swing !== 0 ? ` (${quote.swing > 0 ? '+' : ''}${quote.swing}%)` : ''}`}
                  </Badge>
                </div>
                <Muted as='span' variant='caption'>
                  {`Offered ${formatInteger(quote.supply)} · wanted ${formatInteger(quote.demand)} · in ${formatInteger(quote.imported)} · out ${formatInteger(quote.exported)}`}
                </Muted>
              </li>
            )}
          </Paged>
        </ul>
      )}
    </div>
  )
}

export function PartHeader({
  icon,
  title,
  note,
  tone = 'gold',
  aside,
}: {
  icon: LucideIcon
  title: string
  note?: string
  tone?: KpiTone
  aside?: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2'>
      <Medallion icon={icon} tone={tone} />
      <div className='flex min-w-0 flex-1 basis-48 flex-col gap-0.5'>
        <SectionTitle level={3} truncate className='text-gilded'>
          {title}
        </SectionTitle>
        <Flourish />
        {note && <Muted variant='caption'>{note}</Muted>}
      </div>
      {aside}
    </div>
  )
}

export function AdjustPanel({
  label,
  title,
  note,
  hold,
  onHold,
  children,
}: {
  label: string
  title: string
  note: string
  hold?: boolean
  onHold?: (value: boolean) => void
  children: ReactNode
}) {
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button variant='outline' size='sm' className='self-start'>
          <SlidersHorizontal />
          {label}
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col'>
        <ControlPanel title={title} note={note} hold={hold} onHold={onHold}>
          {children}
        </ControlPanel>
      </CollapsibleContent>
    </Collapsible>
  )
}

export const FIELD_GRID = 'grid min-w-0 grid-cols-1 items-end gap-3'

export function NumberField({
  label,
  value,
  onChange,
  min = 0,
  max,
  aria,
  disabled,
}: {
  label: string
  value: string
  onChange: (next: string) => void
  min?: number
  max?: number
  aria?: string
  disabled?: boolean
}) {
  const id = useId()
  return (
    <FieldTile id={id} label={label}>
      <Input
        id={id}
        type='number'
        inputMode='numeric'
        min={min}
        max={max}
        value={value}
        disabled={disabled}
        aria-label={aria ?? label}
        onChange={(event) => onChange(event.target.value)}
      />
    </FieldTile>
  )
}

export function LevelPips({
  level,
  tone = 'gold',
  label = 'Level',
}: {
  level: number
  tone?: KpiTone
  label?: string
}) {
  const lit = Math.min(PIPS, level)
  return (
    <span
      data-domain='level-pips'
      aria-label={`${label} ${level}`}
      className='inline-flex min-w-0 items-center gap-1.5'
    >
      <span aria-hidden='true' className='inline-flex items-center gap-0.5'>
        {Array.from({ length: PIPS }, (_, index) => (
          <span
            key={index}
            className={cn(
              'h-1.5 w-2.5 rounded-full',
              index < lit ? PIP_TONE[tone] : 'bg-muted'
            )}
          />
        ))}
      </span>
      <Label as='span' className='shrink-0'>
        {`Lv ${level}`}
      </Label>
    </span>
  )
}

export function GoodChip({
  kind,
  quantity,
  tone = 'outline',
  suffix,
}: {
  kind: CommodityKind
  quantity: number
  tone?: 'outline' | 'success' | 'destructive' | 'warning' | 'info'
  suffix?: string
}) {
  const spec = COMMODITY[kind]
  return (
    <Badge variant={tone} className='gap-1.5'>
      <spec.icon />
      <span className='tabular-nums'>{formatInteger(quantity)}</span>
      {`${spec.label.toLowerCase()}${suffix ?? ''}`}
    </Badge>
  )
}

function StoreTile({
  kind,
  supply,
  storage,
  keeper,
  spoiled,
}: {
  kind: StoreKind
  supply: number
  storage: number
  keeper: number | null
  spoiled: number
}) {
  const spec = STORE[kind]
  const over = storage > 0 && supply > storage
  const short = supply < SHORT
  const tone: KpiTone = over ? 'warning' : short ? 'danger' : spec.tone
  const keeperName = WORKSHOP[spec.keeper].label
  return (
    <div
      data-store={kind}
      data-overflow={over || undefined}
      className={cn(
        'flex h-full min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4',
        over && TONE_BORDER.warning,
        short && TONE_BORDER.danger
      )}
    >
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={spec.icon} tone={tone} />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Label truncate>{spec.label}</Label>
          <Muted variant='caption' truncate>
            {keeper
              ? `${keeperName} level ${keeper}`
              : `No ${keeperName.toLowerCase()}, kept in homes`}
          </Muted>
        </div>
      </div>
      <Stat
        value={supply}
        size='kpi'
        tone={over ? 'warning' : short ? 'destructive' : 'default'}
        unit={`/ ${formatInteger(storage)} ${spec.room}`}
      />
      <Progress
        size='sm'
        tone={over ? 'warning' : short ? 'destructive' : 'default'}
        value={
          storage > 0 ? Math.min(PERCENT, (supply / storage) * PERCENT) : 0
        }
        aria-label={`${spec.label} against ${spec.room}`}
      />
      <div className='mt-auto flex min-w-0 flex-wrap gap-1.5'>
        {over ? (
          <Badge variant='warning'>
            <TriangleAlert />
            {`Overflowing by ${formatInteger(supply - storage)}`}
          </Badge>
        ) : short ? (
          <Badge variant='destructive'>
            <TriangleAlert />
            Under half an epoch
          </Badge>
        ) : (
          <Badge variant='success'>
            <CircleCheck />
            Room to spare
          </Badge>
        )}
        <Badge variant='outline'>
          <Hourglass />
          {`${(supply / PERCENT).toFixed(1)} epochs of need`}
        </Badge>
        {spoiled > 0 && (
          <Badge variant='warning'>
            <Trash2 />
            {`${formatInteger(spoiled)} spoiled last epoch`}
          </Badge>
        )}
      </div>
    </div>
  )
}

function LotEditor({
  communityId,
  lot,
  busy,
}: {
  communityId: number
  lot: Lot
  busy: string | null
}) {
  const [quantity, setQuantity] = useState(String(lot.quantity))
  const [quality, setQuality] = useState(String(lot.quality))
  const [hold, setHold] = useState(lot.held)
  const set = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/stock:set', {
          body: {
            community_id: communityId,
            commodity: lot.commodity,
            material: lot.world_material_id === null ? lot.material : null,
            world_material_id: lot.world_material_id,
            quantity: whole(quantity),
            quality: whole(quality, PERCENT),
            hold,
          },
        })
      ),
  })
  const blocked = busy ?? (set.isPending ? WORKING : null)
  return (
    <AdjustPanel
      label='Set exactly'
      title={`Set the ${lot.label.toLowerCase()}`}
      note='Set how much lies in store and its quality. Held, the stores keep exactly this.'
      hold={hold}
      onHold={setHold}
    >
      <div className={cn(FIELD_GRID, 'grid-cols-2')}>
        <NumberField
          label='Amount'
          aria={`${lot.label} amount`}
          value={quantity}
          onChange={setQuantity}
        />
        <NumberField
          label='Quality'
          aria={`${lot.label} quality`}
          value={quality}
          max={PERCENT}
          onChange={setQuality}
        />
      </div>
      <Button
        size='sm'
        className='self-start'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => set.mutate(undefined)}
      >
        <Check />
        Set the lot
      </Button>
    </AdjustPanel>
  )
}

function GoodTile({
  communityId,
  lot,
  busy,
}: {
  communityId: number
  lot: Lot
  busy: string | null
}) {
  const spec = COMMODITY[lot.commodity]
  const family = GOODS_FAMILY[spec.family]
  const tier = qualityTier(lot.quality)
  const release = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/stock:release', { body: { lot_id: lot.id } })
      ),
  })
  const blocked = busy ?? (release.isPending ? WORKING : null)
  return (
    <li
      data-commodity={lot.commodity}
      className='flex h-full min-w-0 flex-col gap-2 rounded-md border surface-well border-gild/20 bg-muted/60 p-2.5'
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion icon={spec.icon} tone={family.tone} size='sm' />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='medium' truncate>
            {lot.label}
          </Text>
          <Muted variant='caption' truncate>
            {`${tier.label} · quality ${lot.quality}`}
          </Muted>
        </div>
        <HeldBadge held={lot.held} />
        <Stat value={lot.quantity} />
      </div>
      <Progress
        value={lot.quality}
        size='sm'
        tone={tier.meter}
        aria-label={`${lot.label} quality`}
      />
      <ReleaseButton
        held={lot.held}
        busy={blocked}
        onRelease={() => release.mutate(undefined)}
      />
      <LotEditor
        key={`${lot.quantity}-${lot.quality}-${lot.held}`}
        communityId={communityId}
        lot={lot}
        busy={blocked}
      />
    </li>
  )
}

function StoreControls({
  economy,
  worldId,
  busy,
}: {
  economy: Economy
  worldId: number | null
  busy: string | null
}) {
  const [commodity, setCommodity] = useState<string>('grain')
  const [material, setMaterial] = useState<string>(NONE)
  const [amount, setAmount] = useState('100')
  const [quality, setQuality] = useState('50')
  const grant = useGodAction({
    run: (sign: number) =>
      unwrap(
        api.POST('/api/actions/stock:grant', {
          body: {
            community_id: economy.community_id,
            commodity: commodity as CommodityKind,
            ...(material === NONE ? {} : materialRef(material)),
            quantity: sign * Math.max(0, Math.round(Number(amount) || 0)),
            quality: Math.min(
              PERCENT,
              Math.max(0, Math.round(Number(quality) || 0))
            ),
          },
        })
      ),
  })
  const blocked = busy ?? (grant.isPending ? WORKING : null)
  return (
    <AdjustPanel
      label='Adjust the stores'
      title='Add or take goods'
      note='Fill the stores with a good of the quality you choose, or take some away. Goods above the room of the granaries and warehouses spoil at the next epoch.'
    >
      <div className={cn(FIELD_GRID, '@md/econ:grid-cols-4')}>
        <MindPicker
          label='Good'
          value={commodity}
          table={COMMODITY_CHOICES}
          blocked={blocked}
          onPick={setCommodity}
        />
        <MaterialSelect
          label='Of the material'
          worldId={worldId}
          value={material}
          blocked={blocked}
          none='No particular material'
          onPick={setMaterial}
        />
        <NumberField label='Amount' value={amount} onChange={setAmount} />
        <NumberField
          label='Quality (0–100)'
          aria='Quality'
          value={quality}
          max={PERCENT}
          onChange={setQuality}
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-2'>
        <Button
          size='sm'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => grant.mutate(1)}
        >
          <Plus />
          Add to the stores
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => grant.mutate(-1)}
        >
          <Minus />
          Take away
        </Button>
      </div>
    </AdjustPanel>
  )
}

export function StockTable({
  economy,
  worldId = null,
  readOnlyReason,
}: {
  economy: Economy
  worldId?: number | null
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const busy = readOnlyReason ?? reason()
  const levels = new Map(economy.workshops.map((row) => [row.kind, row.level]))
  const spoiled = (kind: StoreKind) =>
    economy.flows
      .filter(
        (row) =>
          SPOILING_FLOWS.has(row.flow) &&
          COMMODITY[row.commodity].store === kind
      )
      .reduce((sum, row) => sum + Math.abs(row.quantity), 0)
  const lots = [...economy.stocks].sort(
    (a, b) =>
      FAMILIES.indexOf(COMMODITY[a.commodity].family) -
        FAMILIES.indexOf(COMMODITY[b.commodity].family) ||
      b.quantity - a.quantity
  )
  const totals = FAMILIES.map((family) => ({
    family,
    lots: lots.filter((lot) => COMMODITY[lot.commodity].family === family),
  }))
  return (
    <div data-surface='StockTable' className='flex min-w-0 flex-col gap-4'>
      <PartHeader
        icon={Package}
        title='The stores'
        note='100 is one epoch of what the people need; the room is what their granaries and warehouses hold. What overflows spoils.'
      />
      <div className='grid min-w-0 grid-cols-1 gap-3 @md/econ:grid-cols-3'>
        {STORE_KINDS.map((kind) => (
          <StoreTile
            key={kind}
            kind={kind}
            supply={economy.supply[kind] ?? 0}
            storage={economy.storage[kind] ?? 0}
            keeper={levels.get(STORE[kind].keeper) ?? null}
            spoiled={spoiled(kind)}
          />
        ))}
      </div>
      {lots.length === 0 ? (
        <EmptyState
          icon={Package}
          title='The stores are empty'
          description='Harvests, mines and workshops fill them each epoch.'
        />
      ) : (
        <>
          <div className='grid min-w-0 grid-cols-2 gap-2 @xl/econ:grid-cols-4'>
            <Paged items={totals}>
              {({ family, lots: held }) => {
                const spec = GOODS_FAMILY[family]
                return (
                  <MiniStat
                    key={family}
                    icon={spec.icon}
                    tone={held.length > 0 ? spec.tone : 'muted'}
                    label={spec.label}
                    value={formatInteger(
                      held.reduce((sum, lot) => sum + lot.quantity, 0)
                    )}
                    hint={`${spec.note}: ${held.length} ${held.length === 1 ? 'lot' : 'lots'} in store`}
                  />
                )
              }}
            </Paged>
          </div>
          <ul className='grid min-w-0 grid-cols-1 gap-2 @sm/econ:grid-cols-2 @3xl/econ:grid-cols-3'>
            <Paged items={lots} as='li'>
              {(lot) => (
                <GoodTile
                  key={lot.id}
                  communityId={economy.community_id}
                  lot={lot}
                  busy={busy}
                />
              )}
            </Paged>
          </ul>
        </>
      )}
      <StoreControls economy={economy} worldId={worldId} busy={busy} />
    </div>
  )
}

type StepState = 'making' | 'short' | 'idle'

const STEP_STATE: Record<
  StepState,
  {
    label: string
    icon: LucideIcon
    tone: KpiTone
    variant: 'success' | 'destructive' | 'warning'
  }
> = {
  making: {
    label: 'Producing',
    icon: CircleCheck,
    tone: 'success',
    variant: 'success',
  },
  short: {
    label: 'Blocked',
    icon: Ban,
    tone: 'danger',
    variant: 'destructive',
  },
  idle: {
    label: 'Idle',
    icon: CirclePause,
    tone: 'warning',
    variant: 'warning',
  },
}

function stepState(step: ChainStep): StepState {
  if (step.bottleneck) return 'short'
  return step.made > 0 ? 'making' : 'idle'
}

function Recipe({ step }: { step: ChainStep }) {
  return (
    <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
      {Object.entries(step.inputs).map(([kind, qty]) => (
        <GoodChip
          key={kind}
          kind={kind as CommodityKind}
          quantity={qty}
          tone={step.bottleneck === kind ? 'destructive' : 'outline'}
        />
      ))}
      <ArrowRight
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-muted-foreground'
      />
      <GoodChip kind={step.output} quantity={step.output_qty} tone='info' />
      <Muted variant='caption'>per batch</Muted>
    </div>
  )
}

function StepRow({
  step,
  workshopLevel,
}: {
  step: ChainStep
  workshopLevel: number | null
}) {
  const out = COMMODITY[step.output]
  const where = step.workshop ? WORKSHOP[step.workshop] : null
  const state = stepState(step)
  const look = STEP_STATE[state]
  const material = step.material ? MATERIAL_LABEL[step.material] : null
  return (
    <li
      data-bottleneck={step.bottleneck ?? undefined}
      data-state={state}
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3',
        state !== 'making' && TONE_BORDER[look.tone]
      )}
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion
          icon={where?.icon ?? Factory}
          tone={state === 'making' ? (where?.tone ?? 'gold') : look.tone}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text weight='semibold' truncate>
            {step.label}
          </Text>
          <div className='flex min-w-0 flex-wrap items-center gap-x-2'>
            <Muted variant='caption'>
              {where
                ? workshopLevel
                  ? where.label
                  : `${where.label}, none built`
                : 'At home, by hand'}
            </Muted>
            {where && workshopLevel ? (
              <LevelPips level={workshopLevel} tone={where.tone} />
            ) : null}
          </div>
        </div>
        <Badge variant={look.variant}>
          <look.icon />
          {look.label}
        </Badge>
      </div>
      <Recipe step={step} />
      {state !== 'idle' && (
        <div className='flex min-w-0 flex-wrap items-center gap-2 border-t pt-2.5'>
          {state === 'making' ? (
            <>
              <Badge variant='success' className='gap-1.5'>
                <out.icon />
                <span className='tabular-nums'>{`+${formatInteger(step.made)}`}</span>
                {`${out.label.toLowerCase()}${material ? ` of ${material.toLowerCase()}` : ''}`}
              </Badge>
              <Muted variant='caption'>{`made this epoch at quality ${step.quality}`}</Muted>
            </>
          ) : (
            <Text variant='caption' tone='destructive'>
              {`Stood idle for want of ${COMMODITY[step.bottleneck ?? step.output].label.toLowerCase()}: no ${out.label.toLowerCase()} was made.`}
            </Text>
          )}
        </div>
      )}
    </li>
  )
}

function WorkshopEditor({
  communityId,
  worldId,
  row,
  designs,
  busy,
}: {
  communityId: number
  worldId: number | null
  row: Workshop
  designs: Design[]
  busy: string | null
}) {
  const spec = WORKSHOP[row.kind]
  const [fleet, setFleet] = useState(String(row.fleet))
  const [idle, setIdle] = useState(String(row.idle_epochs))
  const [structure, setStructure] = useState<string | null>(
    row.structure_id === null ? null : String(row.structure_id)
  )
  const [design, setDesign] = useState<string>(
    row.design_id ? String(row.design_id) : NONE
  )
  const [hold, setHold] = useState(row.held)
  const edit = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/workshop:edit', {
          body: {
            community_id: communityId,
            kind: row.kind,
            fleet: whole(fleet),
            idle_epochs: whole(idle),
            structure_id: structure === null ? 0 : Number(structure),
            design_id: design === NONE ? 0 : Number(design),
            hold,
          },
        })
      ),
  })
  const blocked = busy ?? (edit.isPending ? WORKING : null)
  const fitting = designs.filter((item) => item.base_kind === row.kind)
  const designTable: Record<string, Named> = {
    [NONE]: {
      label: `A plain ${spec.label.toLowerCase()}`,
      icon: spec.icon,
      tone: 'muted',
    },
    ...Object.fromEntries(
      fitting.map((item) => [
        String(item.id),
        { label: item.name, icon: spec.icon, tone: spec.tone },
      ])
    ),
  }
  return (
    <AdjustPanel
      label='Adjust'
      title={`The ${spec.label.toLowerCase()}`}
      note='Set its ships, how long it has stood idle, the building it works from and the design it follows. Held, the people keep it as you set it.'
      hold={hold}
      onHold={setHold}
    >
      <div className={cn(FIELD_GRID, 'grid-cols-2')}>
        <NumberField
          label='Ships in its fleet'
          aria={`${spec.label} fleet`}
          value={fleet}
          onChange={setFleet}
        />
        <NumberField
          label='Epochs idle'
          aria={`${spec.label} idle epochs`}
          value={idle}
          onChange={setIdle}
        />
      </div>
      <ChoiceSelect
        label='Design'
        value={design}
        table={designTable}
        blocked={blocked}
        onPick={setDesign}
      />
      <EntityChoice
        label='Works from'
        types={STRUCTURE_TYPES}
        worldId={worldId}
        value={structure}
        blocked={blocked}
        placeholder='No building of its own'
        onChange={setStructure}
      />
      <Button
        size='sm'
        className='self-start'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={() => edit.mutate(undefined)}
      >
        <Check />
        Set the workshop
      </Button>
    </AdjustPanel>
  )
}

function WorkshopCard({
  communityId,
  worldId,
  row,
  designs,
  busy,
}: {
  communityId: number
  worldId: number | null
  row: Workshop
  designs: Design[]
  busy: string | null
}) {
  const spec = WORKSHOP[row.kind]
  const idle = row.idle_epochs > 0
  const design = designs.find((item) => item.id === row.design_id)
  const release = useGodAction({
    invalidate: ECONOMY_REFRESH,
    run: () =>
      unwrap(
        api.POST('/api/actions/workshop:release', {
          body: { community_id: communityId, kind: row.kind },
        })
      ),
  })
  const blocked = busy ?? (release.isPending ? WORKING : null)
  return (
    <li
      data-workshop={row.kind}
      className={cn(
        'flex h-full min-w-0 flex-col gap-2.5 rounded-md border surface-framed border-gild/70 bg-card p-3',
        idle && TONE_BORDER.warning
      )}
    >
      <div className='flex min-w-0 items-center gap-2.5'>
        <Medallion
          icon={spec.icon}
          tone={idle ? 'warning' : spec.tone}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-1'>
          <Text weight='medium' truncate>
            {design ? design.name : spec.label}
          </Text>
          <LevelPips level={row.level} tone={idle ? 'warning' : spec.tone} />
        </div>
        <HeldBadge held={row.held} />
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        {idle ? (
          <Badge size='sm' variant='warning'>
            <CirclePause />
            {`Idle ${row.idle_epochs} ${row.idle_epochs === 1 ? 'epoch' : 'epochs'}`}
          </Badge>
        ) : (
          <Badge size='sm' variant='success'>
            <CircleCheck />
            Working
          </Badge>
        )}
        {design && (
          <Badge size='sm' variant='info'>
            <PencilRuler />
            {`${spec.label} of a new design`}
          </Badge>
        )}
        {row.fleet > 0 && (
          <IconStat
            icon={Ship}
            label='Ships in its fleet'
            value={`${plural(row.fleet, 'ship', 'ships')}`}
            tone='info'
          />
        )}
        {row.structure_id !== null && (
          <EntityLink kind='entity' id={String(row.structure_id)}>
            Its building
          </EntityLink>
        )}
        <Muted variant='caption'>{`Since epoch ${row.built_epoch}`}</Muted>
      </div>
      <div className='mt-auto flex min-w-0 flex-col gap-2'>
        <ReleaseButton
          held={row.held}
          busy={blocked}
          onRelease={() => release.mutate(undefined)}
        />
        <WorkshopEditor
          key={`${row.fleet}-${row.idle_epochs}-${row.structure_id}-${row.design_id}-${row.held}`}
          communityId={communityId}
          worldId={worldId}
          row={row}
          designs={designs}
          busy={blocked}
        />
      </div>
    </li>
  )
}

function WorkshopControls({
  economy,
  busy,
}: {
  economy: Economy
  busy: string | null
}) {
  const [kind, setKind] = useState<string>('forge')
  const levels = new Map(economy.workshops.map((row) => [row.kind, row.level]))
  const [level, setLevel] = useState(
    String(levels.get('forge' as WorkshopKind) ?? 1)
  )
  const build = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/workshop:set', {
          body: {
            community_id: economy.community_id,
            kind: kind as WorkshopKind,
            level: Math.max(0, Math.round(Number(level) || 0)),
          },
        })
      ),
  })
  const blocked = busy ?? (build.isPending ? WORKING : null)
  const present = levels.get(kind as WorkshopKind) ?? 0
  return (
    <AdjustPanel
      label='Adjust the workshops'
      title='Build, raise or pull down a workshop'
      note='Choose a workshop and the level it should stand at. Level 0 pulls it down; granaries and warehouses add room to the stores.'
    >
      <div className={cn(FIELD_GRID, '@md/econ:grid-cols-3')}>
        <MindPicker
          label='Workshop'
          value={kind}
          table={WORKSHOP_CHOICES}
          blocked={blocked}
          onPick={(next) => {
            setKind(next)
            setLevel(String(levels.get(next as WorkshopKind) ?? 1))
          }}
        />
        <NumberField
          label='Level (0–20)'
          aria='Workshop level'
          value={level}
          max={20}
          onChange={setLevel}
        />
        <Button
          size='sm'
          className='justify-self-start'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={() => build.mutate(undefined)}
        >
          <Check />
          Set the workshop
        </Button>
      </div>
      <Muted variant='caption'>
        {present
          ? `${WORKSHOP[kind as WorkshopKind].label} stands at level ${present} now.`
          : `No ${WORKSHOP[kind as WorkshopKind].label.toLowerCase()} stands here yet.`}
      </Muted>
    </AdjustPanel>
  )
}

export function ProductionChain({
  economy,
  worldId = null,
  readOnlyReason,
}: {
  economy: Economy
  worldId?: number | null
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const busy = readOnlyReason ?? reason()
  const designs = useWorkshopDesigns(worldId).data ?? []
  const levels = new Map(economy.workshops.map((row) => [row.kind, row.level]))
  const order: Record<StepState, number> = { making: 0, short: 1, idle: 2 }
  const steps = economy.chain
    .filter((step) => step.runs || step.made > 0 || step.bottleneck)
    .sort((a, b) => order[stepState(a)] - order[stepState(b)])
  const active = steps.filter((step) => stepState(step) !== 'idle')
  const idle = steps.filter((step) => stepState(step) === 'idle')
  const count = (state: StepState) =>
    steps.filter((step) => stepState(step) === state).length
  const made = steps.reduce((sum, step) => sum + step.made, 0)
  const workshops = [...economy.workshops].sort(
    (a, b) => b.level - a.level || a.kind.localeCompare(b.kind)
  )
  return (
    <div data-surface='ProductionChain' className='flex min-w-0 flex-col gap-4'>
      <PartHeader
        icon={Factory}
        title='Production chain this epoch'
        note='Each step turns goods from the stores into a new good. A missing input blocks the step.'
      />
      <div className='grid min-w-0 grid-cols-2 gap-2 @xl/econ:grid-cols-4'>
        <MiniStat
          icon={CircleCheck}
          tone='success'
          label='Producing'
          value={count('making')}
        />
        <MiniStat
          icon={Ban}
          tone={count('short') > 0 ? 'danger' : 'muted'}
          label='Blocked'
          value={count('short')}
        />
        <MiniStat
          icon={CirclePause}
          tone={count('idle') > 0 ? 'warning' : 'muted'}
          label='Idle'
          value={count('idle')}
        />
        <MiniStat
          icon={Package}
          tone='gold'
          label='Goods made'
          value={formatInteger(made)}
        />
      </div>
      {steps.length === 0 ? (
        <EmptyState
          icon={Factory}
          title='Nothing was made here yet'
          description='Steps appear once a workshop stands or hands work at home.'
        />
      ) : (
        <>
          {active.length > 0 && (
            <ul className='grid min-w-0 grid-cols-1 gap-2 @3xl/econ:grid-cols-2'>
              <Paged items={active} as='li'>
                {(step) => (
                  <StepRow
                    key={step.key}
                    step={step}
                    workshopLevel={
                      step.workshop ? (levels.get(step.workshop) ?? null) : null
                    }
                  />
                )}
              </Paged>
            </ul>
          )}
          {idle.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <div className='flex min-w-0 items-center gap-2'>
                <CirclePause
                  aria-hidden='true'
                  className='size-icon-sm shrink-0 text-warning'
                />
                <Text variant='caption' tone='warning'>
                  {`${idle.length} idle this epoch: no hands to spare, no call for more, or the know-how is missing.`}
                </Text>
              </div>
              <ul className='grid min-w-0 grid-cols-1 gap-2 @xl/econ:grid-cols-2'>
                <Paged items={idle} as='li'>
                  {(step) => (
                    <StepRow
                      key={step.key}
                      step={step}
                      workshopLevel={
                        step.workshop
                          ? (levels.get(step.workshop) ?? null)
                          : null
                      }
                    />
                  )}
                </Paged>
              </ul>
            </div>
          )}
        </>
      )}
      <PartHeader
        icon={Store}
        title='Workshops'
        note={`${workshops.length} standing; each level adds hands and room.`}
      />
      {workshops.length === 0 ? (
        <EmptyState
          icon={Store}
          title='No workshops yet'
          description='The people build them as their knowledge and wealth grow.'
        />
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2 @sm/econ:grid-cols-2 @xl/econ:grid-cols-3'>
          <Paged items={workshops} as='li'>
            {(row) => (
              <WorkshopCard
                key={row.kind}
                communityId={economy.community_id}
                worldId={worldId}
                row={row}
                designs={designs}
                busy={busy}
              />
            )}
          </Paged>
        </ul>
      )}
      <WorkshopControls economy={economy} busy={busy} />
    </div>
  )
}

function CoinChoice({
  economy,
  readOnlyReason,
}: {
  economy: Economy
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const currencies = useCurrencies()
  const use = useGodAction({
    run: (value: string) =>
      unwrap(
        api.POST('/api/actions/currency:use', {
          body: {
            community_id: economy.community_id,
            currency_id: value === NO_COIN ? null : Number(value),
          },
        })
      ),
  })
  const busy = readOnlyReason ?? reason() ?? (use.isPending ? WORKING : null)
  const coin = (currencies.data ?? []).find(
    (row) => row.id === economy.currency_id
  )
  const table: Record<string, string> = {
    [NO_COIN]: 'Barter in kind',
    ...Object.fromEntries(
      (currencies.data ?? []).map((row) => [
        String(row.id),
        `${row.name} (purity ${row.purity})`,
      ])
    ),
  }
  if (economy.currency_id !== null && !coin)
    table[String(economy.currency_id)] = currencies.isPending
      ? 'Reading the coin…'
      : 'Its coin'
  const value =
    economy.currency_id !== null ? String(economy.currency_id) : NO_COIN
  return (
    <div className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-4'>
      <PartHeader
        icon={Coins}
        title='Coin and market'
        note={
          coin
            ? `Counts its wealth in ${coin.name}, purity ${coin.purity} and trust ${coin.trust}.`
            : economy.currency_id !== null
              ? 'Counts its wealth in a struck coin.'
              : 'Barters in kind; no coin counts its wealth.'
        }
        aside={
          economy.market ? (
            <Badge variant='success'>
              <Store />
              Holds a market
            </Badge>
          ) : (
            <Badge variant='outline'>
              <Store />
              No market
            </Badge>
          )
        }
      />
      <div className='max-w-sm min-w-0'>
        <MindPicker
          label='Coin it counts in'
          value={value}
          table={table}
          blocked={busy}
          onPick={(next) => use.mutate(next)}
        />
      </div>
    </div>
  )
}

export function EntityEconomy({
  communityId,
  worldId = null,
  readOnlyReason,
}: {
  communityId: number
  worldId?: number | null
  readOnlyReason?: string | null
}) {
  const view = useCommunityEconomy(communityId)
  return (
    <Section
      id='section-economy'
      title='Stores and production'
      description='What the stores hold, what the workshops made this epoch and where a missing good stopped the chain.'
      icon={Factory}
    >
      {view.isPending && <LoadingBlock label='Loading the stores' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The stores could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div className='@container/econ flex min-w-0 flex-col gap-8'>
          <StockTable
            economy={view.data}
            worldId={worldId}
            readOnlyReason={readOnlyReason}
          />
          <ProductionChain
            economy={view.data}
            worldId={worldId}
            readOnlyReason={readOnlyReason}
          />
          <MarketQuotes economy={view.data} />
          <CoinChoice economy={view.data} readOnlyReason={readOnlyReason} />
          {view.data.market && (
            <HoardControl
              communityId={communityId}
              worldId={worldId}
              readOnlyReason={readOnlyReason}
            />
          )}
        </div>
      )}
    </Section>
  )
}
