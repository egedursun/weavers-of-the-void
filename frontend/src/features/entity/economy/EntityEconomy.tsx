import { useState } from 'react'
import { ArrowRight, Factory, Minus, Plus, TriangleAlert } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { EmptyState, Medallion, Section, StatBar } from '@/components/domain'
import { Label, Muted, Stat, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { useCommunityEconomy, useCurrencies } from './api'
import {
  COMMODITY,
  type CommodityKind,
  WORKSHOP,
  type WorkshopKind,
} from './labels'

type Economy = components['schemas']['CommunityEconomyView']
type ChainStep = components['schemas']['ChainStepView']

const WORKING = 'Working…'
const AGGREGATES = [
  { key: 'food', label: 'Food' },
  { key: 'ore', label: 'Ore and stone' },
  { key: 'goods', label: 'Goods' },
] as const
const NO_COIN = 'none'
const COMMODITY_CHOICES = Object.fromEntries(
  Object.entries(COMMODITY).map(([key, item]) => [key, item.label])
)
const WORKSHOP_CHOICES = Object.fromEntries(
  Object.entries(WORKSHOP).map(([key, item]) => [key, item.label])
)

export function StockTable({
  economy,
  readOnlyReason,
}: {
  economy: Economy
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const [commodity, setCommodity] = useState<string>('grain')
  const [amount, setAmount] = useState('100')
  const [quality, setQuality] = useState('50')
  const grant = useGodAction({
    run: (sign: number) =>
      unwrap(
        api.POST('/api/actions/stock:grant', {
          body: {
            community_id: economy.community_id,
            commodity: commodity as CommodityKind,
            quantity: sign * Math.max(0, Math.round(Number(amount) || 0)),
            quality: Math.min(
              100,
              Math.max(0, Math.round(Number(quality) || 0))
            ),
          },
        })
      ),
  })
  const busy = readOnlyReason ?? reason() ?? (grant.isPending ? WORKING : null)
  return (
    <div data-surface='StockTable' className='flex min-w-0 flex-col gap-4'>
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3'>
        {AGGREGATES.map((aggregate) => (
          <StatBar
            key={aggregate.key}
            label={aggregate.label}
            value={economy.supply[aggregate.key] ?? 0}
            max={economy.storage[aggregate.key] ?? 0}
            tone={
              (economy.supply[aggregate.key] ?? 0) < 50
                ? 'destructive'
                : 'default'
            }
          />
        ))}
      </div>
      <Muted variant='caption'>
        A gauge of 100 is one epoch of what the people need; the cap is what
        their granaries and warehouses hold.
      </Muted>
      {economy.stocks.length === 0 ? (
        <Muted>The stores are empty.</Muted>
      ) : (
        <ul className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-2'>
          {economy.stocks.map((lot) => {
            const spec = COMMODITY[lot.commodity]
            return (
              <li
                key={lot.id}
                className='flex min-w-0 items-center gap-3 rounded-lg border bg-muted/30 p-2'
              >
                <Medallion icon={spec.icon} tone='muted' size='sm' />
                <div className='flex min-w-0 flex-1 flex-col gap-1'>
                  <div className='flex min-w-0 items-center gap-2'>
                    <Text className='min-w-0 flex-1' truncate>
                      {lot.label}
                    </Text>
                    <Stat value={lot.quantity} />
                  </div>
                  <Progress
                    value={lot.quality}
                    size='sm'
                    aria-label={`${lot.label} quality`}
                  />
                </div>
              </li>
            )
          })}
        </ul>
      )}
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-40 flex-1'>
          <MindPicker
            label='Good'
            value={commodity}
            table={COMMODITY_CHOICES}
            blocked={busy}
            onPick={setCommodity}
          />
        </div>
        <div className='flex w-28 flex-col gap-1'>
          <Label>Amount</Label>
          <Input
            type='number'
            min={0}
            value={amount}
            aria-label='Amount'
            onChange={(event) => setAmount(event.target.value)}
          />
        </div>
        <div className='flex w-24 flex-col gap-1'>
          <Label>Quality</Label>
          <Input
            type='number'
            min={0}
            max={100}
            value={quality}
            aria-label='Quality'
            onChange={(event) => setQuality(event.target.value)}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => grant.mutate(1)}
        >
          <Plus />
          Add to the stores
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => grant.mutate(-1)}
        >
          <Minus />
          Take away
        </Button>
      </div>
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
  const idle = step.made === 0
  return (
    <li
      data-bottleneck={step.bottleneck ?? undefined}
      className={`flex min-w-0 flex-wrap items-center gap-2 rounded-lg border p-2 ${step.bottleneck ? 'border-destructive/40 bg-destructive/8' : idle ? 'bg-muted/20' : 'bg-muted/40'}`}
    >
      <div className='flex min-w-0 flex-wrap items-center gap-1'>
        {Object.entries(step.inputs).map(([kind, qty]) => (
          <Badge
            key={kind}
            size='sm'
            variant={step.bottleneck === kind ? 'destructive' : 'outline'}
          >
            {`${qty} ${COMMODITY[kind as CommodityKind].label.toLowerCase()}`}
          </Badge>
        ))}
      </div>
      <ArrowRight
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-muted-foreground'
      />
      <div className='flex min-w-0 items-center gap-2'>
        {where ? (
          <Medallion
            icon={where.icon}
            tone={step.runs ? 'info' : 'muted'}
            size='sm'
          />
        ) : (
          <Medallion icon={Factory} tone='muted' size='sm' />
        )}
        <div className='flex min-w-0 flex-col'>
          <Text truncate>{step.label}</Text>
          <Muted variant='caption'>
            {where
              ? `${where.label}${workshopLevel ? `, level ${workshopLevel}` : ' (none built)'}`
              : 'At home'}
          </Muted>
        </div>
      </div>
      <ArrowRight
        aria-hidden='true'
        className='size-icon-sm shrink-0 text-muted-foreground'
      />
      <Badge size='sm' variant={idle ? 'outline' : 'success'}>
        {`${formatInteger(step.made)} ${out.label.toLowerCase()}${step.material ? ` of ${step.material.replace('_', ' ')}` : ''}`}
      </Badge>
      {step.bottleneck && (
        <Badge size='sm' variant='destructive'>
          <TriangleAlert />
          {`Short of ${COMMODITY[step.bottleneck].label.toLowerCase()}`}
        </Badge>
      )}
    </li>
  )
}

export function ProductionChain({
  economy,
  readOnlyReason,
}: {
  economy: Economy
  readOnlyReason?: string | null
}) {
  const { reason } = useGodGate()
  const [kind, setKind] = useState<string>('forge')
  const [level, setLevel] = useState('1')
  const levels = new Map(economy.workshops.map((row) => [row.kind, row.level]))
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
  const busy = readOnlyReason ?? reason() ?? (build.isPending ? WORKING : null)
  const steps = economy.chain.filter(
    (step) => step.runs || step.made > 0 || step.bottleneck
  )
  return (
    <div data-surface='ProductionChain' className='flex min-w-0 flex-col gap-3'>
      <Label variant='overline'>Production chain this epoch</Label>
      {steps.length === 0 ? (
        <Muted>Nothing was made here yet.</Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          {steps.map((step) => (
            <StepRow
              key={step.key}
              step={step}
              workshopLevel={
                step.workshop ? (levels.get(step.workshop) ?? null) : null
              }
            />
          ))}
        </ul>
      )}
      <Label variant='overline'>Workshops</Label>
      <div className='flex min-w-0 flex-wrap gap-2'>
        {economy.workshops.map((row) => {
          const spec = WORKSHOP[row.kind]
          return (
            <Badge
              key={row.kind}
              variant={row.idle_epochs > 0 ? 'outline' : 'info'}
            >
              <spec.icon />
              {`${spec.label} ${row.level}${row.fleet ? ` · ${row.fleet} ships` : ''}`}
            </Badge>
          )
        })}
      </div>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-40 flex-1'>
          <MindPicker
            label='Workshop'
            value={kind}
            table={WORKSHOP_CHOICES}
            blocked={busy}
            onPick={setKind}
          />
        </div>
        <div className='flex w-24 flex-col gap-1'>
          <Label>Level</Label>
          <Input
            type='number'
            min={0}
            max={20}
            value={level}
            aria-label='Workshop level'
            onChange={(event) => setLevel(event.target.value)}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => build.mutate(undefined)}
        >
          <Factory />
          Set the workshop
        </Button>
      </div>
      <Muted variant='caption'>Level 0 pulls the workshop down.</Muted>
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
  const table = {
    [NO_COIN]: 'Barter in kind',
    ...Object.fromEntries(
      (currencies.data ?? []).map((row) => [
        String(row.id),
        `${row.name} (purity ${row.purity})`,
      ])
    ),
  }
  return (
    <div className='max-w-sm min-w-48'>
      <MindPicker
        label='Coin it counts in'
        value={economy.currency_id ? String(economy.currency_id) : NO_COIN}
        table={table}
        blocked={busy}
        onPick={(value) => use.mutate(value)}
      />
    </div>
  )
}

export function EntityEconomy({
  communityId,
  readOnlyReason,
}: {
  communityId: number
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
      {view.isPending && <Muted>Loading the stores…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='The stores could not be read'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div className='flex min-w-0 flex-col gap-6'>
          <StockTable economy={view.data} readOnlyReason={readOnlyReason} />
          <ProductionChain
            economy={view.data}
            readOnlyReason={readOnlyReason}
          />
          <CoinChoice economy={view.data} readOnlyReason={readOnlyReason} />
        </div>
      )}
    </Section>
  )
}
