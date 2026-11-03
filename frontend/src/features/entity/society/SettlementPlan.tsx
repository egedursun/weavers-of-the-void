import { useState } from 'react'
import {
  Building,
  Coins,
  Flame,
  Hammer,
  Landmark,
  Percent,
  Save,
  ScrollText,
  Shield,
  TriangleAlert,
  Trash2,
  Unlock,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
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
import { LineChart } from '@/components/domain/LineChart'
import { Label, Muted, Text } from '@/components/typography'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { MindPicker } from '../mind/parts'
import { useSettlementPlan } from './api'
import { DISTRICT_SPEC, choices, words, type DistrictKind } from './labels'

type Plan = components['schemas']['SettlementPlanView']
type District = components['schemas']['DistrictView']

const WORKING = 'Working…'
const PERCENT = 100
const PROFILE_FIELDS = [
  { key: 'public_order', label: 'Order' },
  { key: 'crime', label: 'Crime' },
  { key: 'unrest', label: 'Unrest' },
  { key: 'sanitation', label: 'Sanitation' },
  { key: 'fire_risk', label: 'Fire risk' },
  { key: 'prestige', label: 'Prestige' },
  { key: 'treasury', label: 'Treasury' },
  { key: 'militia', label: 'Militia' },
  { key: 'investment_pool', label: 'Investment pool' },
] as const
const INFRA_FIELDS = [
  { key: 'walls_level', label: 'Wall level' },
  { key: 'walls_condition', label: 'Wall condition' },
  { key: 'gates', label: 'Gates' },
  { key: 'towers', label: 'Towers' },
  { key: 'roads', label: 'Roads' },
  { key: 'granary_capacity', label: 'Granary' },
  { key: 'warehouse_capacity', label: 'Warehouses' },
  { key: 'harbour_capacity', label: 'Harbour' },
] as const
const TIERS = ['hamlet', 'village', 'town', 'city', 'metropolis'] as const
const WATER = ['none', 'well', 'cistern', 'aqueduct'] as const
const MATERIALS = ['timber', 'stone'] as const

function DistrictTile({
  district,
  blocked,
}: {
  district: District
  blocked: string | null
}) {
  const spec = DISTRICT_SPEC[district.kind]
  const Icon = spec.icon
  const raze = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/district:raze', {
          body: { district_id: district.id },
        })
      ),
  })
  const raise = useGodAction({
    run: (level: number) =>
      unwrap(
        api.POST('/api/actions/district:edit', {
          body: { district_id: district.id, level, condition: PERCENT },
        })
      ),
  })
  const busy = blocked ?? (raze.isPending || raise.isPending ? WORKING : null)
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-lg border bg-muted/30 p-3'>
      <div className='flex min-w-0 items-center gap-2'>
        <Icon
          aria-hidden='true'
          className='size-icon-sm shrink-0 text-muted-foreground'
        />
        <Text className='min-w-0 flex-1' truncate>
          {spec.label}
        </Text>
        <Badge variant={district.material === 'stone' ? 'info' : 'outline'}>
          {words(district.material)}
        </Badge>
      </div>
      <StatBar
        label={`Level ${district.level}`}
        value={district.condition}
        max={PERCENT}
        tone={district.condition < 40 ? 'destructive' : 'default'}
      />
      <div className='flex min-w-0 flex-wrap gap-1'>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null || district.level >= 5}
          disabledReason={busy ?? 'Already at the highest level'}
          onClick={() => raise.mutate(district.level + 1)}
        >
          <Hammer />
          Enlarge
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => raze.mutate(undefined)}
        >
          <Trash2 />
          Raze
        </Button>
      </div>
    </li>
  )
}

function PlanForm({ plan, blocked }: { plan: Plan; blocked: string | null }) {
  const [numbers, setNumbers] = useState<Record<string, string>>(() => ({
    ...Object.fromEntries(
      PROFILE_FIELDS.map((field) => [field.key, String(plan[field.key])])
    ),
    ...Object.fromEntries(
      INFRA_FIELDS.map((field) => [
        field.key,
        String(plan.infrastructure[field.key]),
      ])
    ),
  }))
  const [picks, setPicks] = useState<Record<string, string>>(() => ({
    size_tier: plan.size_tier,
    water: plan.infrastructure.water,
    walls_material: plan.infrastructure.walls_material,
  }))
  const [flags, setFlags] = useState({
    sewers: plan.infrastructure.sewers,
    rationing: plan.rationing,
  })
  const [tax, setTax] = useState(String(plan.tax_rate))
  const [kind, setKind] = useState<string>('market')
  const [material, setMaterial] = useState<string>('stone')
  const locked = [...plan.locked, ...plan.infrastructure.locked]
  const save = useGodAction({
    run: (release: string[]) =>
      unwrap(
        api.POST('/api/actions/settlement:edit', {
          body: {
            settlement_id: plan.entity_id,
            values:
              release.length > 0
                ? {}
                : {
                    ...Object.fromEntries(
                      Object.entries(numbers).map(([key, value]) => [
                        key,
                        Math.max(0, Math.round(Number(value) || 0)),
                      ])
                    ),
                    ...picks,
                    ...flags,
                  },
            release,
          },
        })
      ),
  })
  const setRate = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/settlement:tax', {
          body: {
            settlement_id: plan.entity_id,
            rate: Math.max(0, Math.min(PERCENT, Number(tax) || 0)),
          },
        })
      ),
  })
  const build = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/district:build', {
          body: {
            settlement_id: plan.entity_id,
            kind: kind as DistrictKind,
            material: material as 'timber' | 'stone',
          },
        })
      ),
  })
  const free = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/settlement:free_city', {
          body: { settlement_id: plan.entity_id, free: !plan.free_city },
        })
      ),
  })
  const charter = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/settlement:charter', {
          body: { settlement_id: plan.entity_id },
        })
      ),
  })
  const pending =
    save.isPending ||
    setRate.isPending ||
    build.isPending ||
    free.isPending ||
    charter.isPending
  const busy = blocked ?? (pending ? WORKING : null)
  const districts = Object.fromEntries(
    Object.entries(DISTRICT_SPEC).map(([key, spec]) => [key, spec.label])
  )
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-wrap items-end gap-3'>
        <div className='min-w-40 flex-1'>
          <MindPicker
            label='District'
            value={kind}
            table={districts}
            blocked={busy}
            onPick={setKind}
          />
        </div>
        <div className='min-w-32'>
          <MindPicker
            label='Built of'
            value={material}
            table={choices(MATERIALS)}
            blocked={busy}
            onPick={setMaterial}
          />
        </div>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => build.mutate(undefined)}
        >
          <Building />
          Build it
        </Button>
        <div className='flex w-28 flex-col gap-1'>
          <Label>Tax (%)</Label>
          <Input
            type='number'
            min={0}
            max={PERCENT}
            value={tax}
            aria-label='Tax'
            onChange={(event) => setTax(event.target.value)}
          />
        </div>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setRate.mutate(undefined)}
        >
          <Percent />
          Set the tax
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => free.mutate(undefined)}
        >
          <Shield />
          {plan.free_city ? 'Bind it to its overlord' : 'Declare a free city'}
        </Button>
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null || plan.charter_id !== null}
          disabledReason={busy ?? 'It already holds a charter'}
          onClick={() => charter.mutate(undefined)}
        >
          <ScrollText />
          Grant a charter
        </Button>
      </div>
      <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
        {[...PROFILE_FIELDS, ...INFRA_FIELDS].map((field) => (
          <div key={field.key} className='flex min-w-0 flex-col gap-1'>
            <Label>{field.label}</Label>
            <Input
              type='number'
              min={0}
              value={numbers[field.key]}
              aria-label={field.label}
              onChange={(event) =>
                setNumbers((current) => ({
                  ...current,
                  [field.key]: event.target.value,
                }))
              }
            />
          </div>
        ))}
      </div>
      <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-3'>
        <MindPicker
          label='Size'
          value={picks.size_tier}
          table={choices(TIERS)}
          blocked={busy}
          onPick={(value) =>
            setPicks((current) => ({ ...current, size_tier: value }))
          }
        />
        <MindPicker
          label='Water'
          value={picks.water}
          table={choices(WATER)}
          blocked={busy}
          onPick={(value) =>
            setPicks((current) => ({ ...current, water: value }))
          }
        />
        <MindPicker
          label='Walls of'
          value={picks.walls_material}
          table={choices(MATERIALS)}
          blocked={busy}
          onPick={(value) =>
            setPicks((current) => ({ ...current, walls_material: value }))
          }
        />
      </div>
      <div className='flex min-w-0 flex-wrap gap-4'>
        {(['sewers', 'rationing'] as const).map((key) => (
          <label key={key} className='flex items-center gap-2'>
            <Switch
              checked={flags[key]}
              disabled={busy !== null}
              onCheckedChange={(value) =>
                setFlags((current) => ({ ...current, [key]: value }))
              }
              aria-label={words(key)}
            />
            <Text as='span'>{key === 'sewers' ? 'Sewers' : 'Rationing'}</Text>
          </label>
        ))}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => save.mutate([])}
        >
          <Save />
          Hold these values
        </Button>
        {locked.length > 0 && (
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => save.mutate(locked)}
          >
            <Unlock />
            Let them change again
          </Button>
        )}
        {locked.map((key) => (
          <Badge key={key} variant='outline'>{`held: ${words(key)}`}</Badge>
        ))}
      </div>
    </div>
  )
}

export function SettlementPlanSection({
  settlementId,
  readOnlyReason,
}: {
  settlementId: number
  readOnlyReason?: string | null
}) {
  const view = useSettlementPlan(settlementId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  return (
    <Section
      id='section-settlement-plan'
      title='The city'
      description='Its size, districts, walls, water and sewers; order, crime and unrest; how it stands a siege.'
      icon={Landmark}
    >
      {view.isPending && <Muted>Walking the streets…</Muted>}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Not surveyed yet'
          description={view.error.message}
        />
      )}
      {view.data && (
        <div
          data-surface='SettlementPlan'
          className='flex min-w-0 flex-col gap-5'
        >
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Badge variant='info'>{words(view.data.size_tier)}</Badge>
            {view.data.free_city && <Badge variant='success'>Free city</Badge>}
            {view.data.charter_id !== null && (
              <Badge variant='outline'>
                <EntityLink kind='entity' id={String(view.data.charter_id)}>
                  Chartered
                </EntityLink>
              </Badge>
            )}
            {view.data.rationing && <Badge variant='warning'>Rationing</Badge>}
            {view.data.infrastructure.sewers && (
              <Badge variant='outline'>Sewers</Badge>
            )}
            <Badge variant='outline'>{`Water: ${words(view.data.infrastructure.water)}`}</Badge>
            {view.data.foreigners.map((item) => (
              <Badge
                key={item.people_id}
                variant='outline'
              >{`${item.name} ${item.share}%`}</Badge>
            ))}
          </div>
          <div className='grid min-w-0 grid-cols-2 gap-3 md:grid-cols-4'>
            <KpiTile
              label='Treasury'
              value={formatInteger(view.data.treasury)}
              icon={Coins}
            />
            <KpiTile
              label='Districts'
              value={`${view.data.districts.length} of ${view.data.district_slots}`}
              icon={Building}
            />
            <KpiTile
              label='Housing'
              value={formatInteger(view.data.housing)}
              icon={Building}
            />
            <KpiTile
              label='Fire risk'
              value={String(view.data.fire_risk)}
              icon={Flame}
              tone={view.data.fire_risk > 50 ? 'danger' : 'muted'}
            />
          </div>
          <div className='grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2'>
            <StatBar
              label='Order'
              value={view.data.public_order}
              max={PERCENT}
              tone='success'
            />
            <StatBar
              label='Crime'
              value={view.data.crime}
              max={PERCENT}
              tone='destructive'
            />
            <StatBar
              label='Unrest'
              value={view.data.unrest}
              max={PERCENT}
              tone='warning'
            />
            <StatBar
              label='Sanitation'
              value={view.data.sanitation}
              max={PERCENT}
              tone='info'
            />
            <StatBar label='Wealth' value={view.data.wealth} max={PERCENT} />
            <StatBar
              label='Prestige'
              value={view.data.prestige}
              max={PERCENT}
              tone='verdigris'
            />
          </div>
          <Muted variant='caption'>{`Siege: food for ${view.data.siege_supplies} days, water for ${view.data.siege_water}, camp sickness ${view.data.siege_disease}. Builders can raise ${formatInteger(view.data.construction_capacity)}, porters haul ${formatInteger(view.data.hauling_capacity)}.`}</Muted>
          <ul
            data-surface='SettlementPlanTiles'
            className='grid min-w-0 auto-rows-min grid-cols-2 gap-3 md:grid-cols-4'
          >
            {view.data.districts.map((district) => (
              <DistrictTile
                key={district.id}
                district={district}
                blocked={blocked}
              />
            ))}
          </ul>
          <PlanForm
            key={JSON.stringify([
              view.data.locked,
              view.data.infrastructure.locked,
              view.data.treasury,
              view.data.districts.length,
            ])}
            plan={view.data}
            blocked={blocked}
          />
        </div>
      )}
    </Section>
  )
}

export function TreasurySection({ settlementId }: { settlementId: number }) {
  const view = useSettlementPlan(settlementId)
  if (!view.data) return null
  const history = view.data.history
  return (
    <>
      <Section
        id='section-treasury'
        title='Treasury'
        description='Every coin in and out: taxes, tolls, the owners’ investment, garrisons, walls, festivals, alms, building and fires.'
        icon={Coins}
      >
        {view.data.treasury_ledger.length === 0 ? (
          <Muted>No coin has moved yet.</Muted>
        ) : (
          <ul
            data-surface='TreasuryLedger'
            className='flex min-w-0 flex-col gap-1'
          >
            {view.data.treasury_ledger.map((line, index) => (
              <li
                key={`${line.epoch}-${index}`}
                className='flex min-w-0 items-center gap-3'
              >
                <Muted
                  variant='caption'
                  className='w-16 shrink-0'
                >{`Epoch ${line.epoch}`}</Muted>
                <Text
                  className='min-w-0 flex-1'
                  truncate
                >{`${words(line.entry)}${line.note ? `: ${line.note}` : ''}`}</Text>
                <Text
                  className={
                    line.amount < 0
                      ? 'w-24 shrink-0 text-right text-destructive'
                      : 'w-24 shrink-0 text-right text-success'
                  }
                >
                  {formatInteger(line.amount)}
                </Text>
                <Muted variant='caption' className='w-24 shrink-0 text-right'>
                  {formatInteger(line.balance)}
                </Muted>
              </li>
            ))}
          </ul>
        )}
      </Section>
      {history.length > 1 && (
        <Section
          id='chart-order-timeline'
          title='Order, crime and unrest'
          description='How the city has fared, epoch by epoch.'
          icon={Landmark}
        >
          <LineChart
            label='Order, crime and unrest'
            height={160}
            series={[
              {
                key: 'order',
                label: 'Order',
                color: 'var(--chart-2)',
                points: history.map((point) => ({
                  x: point.epoch,
                  y: point.public_order,
                })),
              },
              {
                key: 'crime',
                label: 'Crime',
                color: 'var(--color-destructive)',
                points: history.map((point) => ({
                  x: point.epoch,
                  y: point.crime,
                })),
              },
              {
                key: 'unrest',
                label: 'Unrest',
                color: 'var(--color-warning)',
                points: history.map((point) => ({
                  x: point.epoch,
                  y: point.unrest,
                })),
              },
              {
                key: 'sanitation',
                label: 'Sanitation',
                color: 'var(--color-info)',
                points: history.map((point) => ({
                  x: point.epoch,
                  y: point.sanitation,
                })),
              },
            ]}
          />
        </Section>
      )}
    </>
  )
}
