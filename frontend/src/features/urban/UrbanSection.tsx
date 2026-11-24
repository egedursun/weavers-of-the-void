import { type ReactNode, useState } from 'react'
import {
  Coins,
  type LucideIcon,
  Gavel,
  Plus,
  Shovel,
  Store,
  Trash2,
  Truck,
  Users,
} from 'lucide-react'
import { plural } from '@/lib/units'
import { Button } from '@/components/ui/button'
import {
  EmptyState,
  KpiTile,
  LoadingBlock,
  PagedList,
  Section,
} from '@/components/domain'
import { type KpiTone } from '@/components/domain/KpiTile'
import { Label, Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { useEntityType } from '@/features/arcana/model'
import {
  Chip,
  Facts,
  ForgeCard,
  Meter,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { COMMODITIES } from '@/features/entity/affairs/labels'
import { MindPicker } from '@/features/entity/mind/parts'
import { DISTRICT_SPEC } from '@/features/entity/society/labels'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { StratumBadge } from '@/features/map/StratumBadge'
import {
  type ConvoyView,
  type CrimeStanceView,
  type DistrictUrbanView,
  type FleetView,
  type MarketPlayView,
  type NodeUrbanView,
  type OrderLawView,
  type PayrollView,
  type RacketView,
  type TradingPostView,
  type TribunalView,
  type TurfView,
  type UrbanAction,
  useNodeUrban,
  useUrbanAction,
} from './api'
import {
  CONVOY_STATUS,
  HOUSING,
  MORPHOLOGIES,
  ORDER_LAWS,
  PLAYS,
  PRESERVATION,
  RACKETS,
  SERVICES,
  STANCES,
  TRANSPORT,
  URBAN_ICON,
  VERDICTS,
} from './labels'

type Values = Record<string, number | string | boolean | null>
type Edit = { values: Values; release: string[] }
type Field = Parameters<typeof RecordEditor>[0]['fields'][number]

const COMMUNITY_TYPES = ['settlement', 'people']
const STRENGTHS = {
  '20': '20',
  '40': '40',
  '60': '60',
  '80': '80',
  '100': '100',
}

function Held({
  icon,
  tone,
  title,
  caption,
  removeLabel,
  editTitle,
  note,
  fields,
  locked,
  blocked,
  onEdit,
  onRemove,
  children,
}: {
  icon: LucideIcon
  tone: KpiTone
  title: ReactNode
  caption: ReactNode
  removeLabel: string
  editTitle: string
  note: string
  fields: Field[]
  locked: string[]
  blocked: string | null
  onEdit: (vars: Edit) => void
  onRemove: () => void
  children?: ReactNode
}) {
  return (
    <RecordRow
      icon={icon}
      tone={tone}
      title={title}
      caption={caption}
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={onRemove}
        >
          <Trash2 />
          {removeLabel}
        </Button>
      }
    >
      {children}
      <RecordEditor
        title={editTitle}
        note={note}
        fields={fields}
        locked={locked}
        busy={blocked}
        onSave={(values) => onEdit({ values, release: [] })}
        onRelease={(release) => onEdit({ values: {}, release })}
      />
    </RecordRow>
  )
}

function useRow<E extends UrbanAction, D extends UrbanAction, K extends object>(
  edit: E,
  remove: D,
  keys: K,
  blocked: string | null
) {
  const editing = useUrbanAction(
    edit,
    (vars: Edit) => ({ ...keys, ...vars }) as never,
    'Set so'
  )
  const removing = useUrbanAction(remove, (_: void) => keys as never, 'Done')
  return {
    busy: why(blocked, editing.isPending, removing.isPending),
    onEdit: (vars: Edit) => editing.mutate(vars),
    onRemove: () => removing.mutate(),
  }
}

function Listed<T>({
  title,
  items,
  empty,
  noun,
  itemKey,
  children,
}: {
  title: string
  items: T[]
  empty: string
  noun: [string, string]
  itemKey: (item: T) => string | number
  children: (item: T) => ReactNode
}) {
  return (
    <>
      <Label variant='overline'>{`${title} (${items.length})`}</Label>
      {items.length === 0 ? (
        <Muted variant='caption'>{empty}</Muted>
      ) : (
        <PagedList
          items={items}
          initial={3}
          noun={noun}
          className='flex min-w-0 flex-col gap-2'
          itemKey={itemKey}
        >
          {children}
        </PagedList>
      )}
    </>
  )
}

function TownCard({
  townId,
  town,
  blocked,
}: {
  townId: number
  town: NonNullable<NodeUrbanView['town']>
  blocked: string | null
}) {
  const edit = useUrbanAction(
    'town_urban:edit',
    (vars: Edit) => ({ settlement_id: townId, ...vars }),
    'The town is set'
  )
  const clear = useUrbanAction(
    'slums:clear',
    (_: void) => ({ settlement_id: townId }),
    'The slums are cleared'
  )
  const busy = why(blocked, edit.isPending, clear.isPending)
  const shape = MORPHOLOGIES[town.morphology]
  return (
    <RecordRow
      icon={shape.icon}
      tone={shape.tone}
      title={shape.label}
      caption={`${town.homeless} without a home`}
      aside={
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => clear.mutate()}
        >
          <Shovel />
          Clear the slums
        </Button>
      }
    >
      <RecordEditor
        title='Reshape the town'
        note='A planned town carries its services further and burns slower; a ringed one defends better in a siege.'
        fields={[
          {
            key: 'morphology',
            label: 'Growth pattern',
            kind: 'pick',
            table: table(MORPHOLOGIES),
          },
          { key: 'homeless', label: 'Homeless', kind: 'number', min: 0 },
        ]}
        locked={town.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function clampCoverage(text: string) {
  const value = Number(text)
  return Number.isNaN(value) ? 0 : Math.min(100, Math.max(0, Math.round(value)))
}

function DistrictCard({
  district,
  blocked,
}: {
  district: DistrictUrbanView
  blocked: string | null
}) {
  const [service, setService] = useState<string>('watch')
  const [coverage, setCoverage] = useState('100')
  const held = district.services.some((row) => row.service === service)
  const edit = useUrbanAction(
    'district_urban:edit',
    (vars: Edit) => ({ district_id: district.id, ...vars }),
    'The district is set'
  )
  const cover = useUrbanAction(
    'district_service:set',
    (_: void) => ({
      district_id: district.id,
      service: service as DistrictUrbanView['services'][number]['service'],
      coverage: clampCoverage(coverage),
    }),
    'The service covers it'
  )
  const recover = useUrbanAction(
    'district_service:edit',
    (_: void) => ({
      district_id: district.id,
      service: service as DistrictUrbanView['services'][number]['service'],
      values: { coverage: clampCoverage(coverage) },
      release: [],
    }),
    'The coverage is set'
  )
  const busy = why(blocked, edit.isPending, cover.isPending, recover.isPending)
  const homes = HOUSING[district.housing]
  return (
    <RecordRow
      icon={homes.icon}
      tone={homes.tone}
      title={`${DISTRICT_SPEC[district.kind].label} · level ${district.level}`}
      caption={`${homes.label}; ${district.turf.length} criminal holds`}
    >
      <Meter
        label='Desirability'
        value={district.desirability}
        tone='success'
      />
      <Meter label='Land value' value={district.land_value} tone='warning' />
      <PagedList
        items={district.services}
        initial={8}
        noun={['service', 'services']}
        className='flex min-w-0 flex-wrap gap-1.5'
        itemKey={(row) => row.service}
      >
        {(row) => (
          <li>
            <ServiceChip districtId={district.id} row={row} blocked={blocked} />
          </li>
        )}
      </PagedList>
      <PagedList
        items={district.turf}
        initial={3}
        noun={['hold', 'holds']}
        className='flex min-w-0 flex-wrap gap-1.5'
        itemKey={(row) => row.faction?.id ?? 0}
      >
        {(row) => (
          <li>
            <Chip icon={RACKETS.protection.icon} variant='destructive'>
              {`${row.faction?.name ?? 'an organisation'} holds it (${row.strength})`}
            </Chip>
          </li>
        )}
      </PagedList>
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-3'>
        <MindPicker
          label='Service'
          value={service}
          table={table(SERVICES)}
          blocked={blocked}
          onPick={setService}
        />
        <NumberField
          label='Coverage'
          value={coverage}
          min={0}
          max={100}
          disabled={busy !== null}
          onChange={setCoverage}
        />
        <Button
          size='sm'
          variant='outline'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => (held ? recover.mutate() : cover.mutate())}
        >
          <Plus />
          {held ? 'Set its coverage' : 'Cover it'}
        </Button>
      </div>
      <RecordEditor
        title='Reshape the district'
        note='Homes rise when water, faith and market reach them and fall when they do not; high land value prices the poor out.'
        fields={[
          {
            key: 'housing',
            label: 'Homes',
            kind: 'pick',
            table: table(HOUSING),
          },
          {
            key: 'desirability',
            label: 'Desirability',
            kind: 'number',
            min: 0,
            max: 100,
          },
          {
            key: 'land_value',
            label: 'Land value',
            kind: 'number',
            min: 0,
            max: 100,
          },
        ]}
        locked={district.locked}
        busy={busy}
        onSave={(values) => edit.mutate({ values, release: [] })}
        onRelease={(release) => edit.mutate({ values: {}, release })}
      />
    </RecordRow>
  )
}

function ServiceChip({
  districtId,
  row,
  blocked,
}: {
  districtId: number
  row: DistrictUrbanView['services'][number]
  blocked: string | null
}) {
  const remove = useUrbanAction(
    'district_service:delete',
    (_: void) => ({ district_id: districtId, service: row.service }),
    'The coverage is drawn anew'
  )
  const busy = why(blocked, remove.isPending)
  const spec = SERVICES[row.service]
  return (
    <Button
      size='sm'
      variant='ghost'
      disabled={busy !== null || row.locked.length === 0}
      disabledReason={
        busy ??
        (row.locked.length === 0
          ? 'Only a held coverage can be released'
          : undefined)
      }
      onClick={() => remove.mutate()}
    >
      <spec.icon />
      {`${spec.label} ${row.coverage} · epoch ${row.epoch}`}
    </Button>
  )
}

function PlacementCard({
  structureId,
  placement,
  blocked,
}: {
  structureId: number
  placement: NonNullable<NodeUrbanView['placement']>
  blocked: string | null
}) {
  const [district, setDistrict] = useState(
    String(placement.district_id ?? 'none')
  )
  const place = useUrbanAction(
    'structure:place',
    (_: void) => ({
      structure_id: structureId,
      district_id: district === 'none' ? null : Number(district),
    }),
    'The structure is placed'
  )
  const busy = why(blocked, place.isPending)
  const choices = Object.fromEntries([
    ['none', 'No district'],
    ...placement.choices.map((row) => [
      String(row.id),
      `${DISTRICT_SPEC[row.kind].label} · level ${row.level}`,
    ]),
  ])
  return (
    <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
      <MindPicker
        label='District it stands in'
        value={district}
        table={choices}
        blocked={blocked}
        onPick={setDistrict}
      />
      <Button
        size='sm'
        variant='outline'
        disabled={busy !== null}
        disabledReason={busy ?? undefined}
        onClick={() => place.mutate()}
      >
        <Store />
        Place it
      </Button>
    </div>
  )
}

function TurfCard({ row, blocked }: { row: TurfView; blocked: string | null }) {
  const action = useRow(
    'turf:edit',
    'turf:delete',
    { district_id: row.district_id, faction_id: row.faction?.id ?? 0 },
    blocked
  )
  return (
    <Held
      icon={RACKETS.protection.icon}
      tone='danger'
      title={<Ref node={row.faction} empty='a lost organisation' />}
      caption={
        <>
          {`Holds the ${row.district_kind ? DISTRICT_SPEC[row.district_kind].label : 'district'} of `}
          <Ref node={row.town} empty='a lost town' />
          {` since epoch ${row.since_epoch}`}
        </>
      }
      removeLabel='Drive out'
      editTitle='Set the turf'
      note='Turf grows under a weak watch and adds crime to its town.'
      fields={[
        { key: 'strength', label: 'Hold', kind: 'number', min: 0, max: 100 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter label='Hold' value={row.strength} tone='warning' />
    </Held>
  )
}

function RacketCard({
  row,
  blocked,
}: {
  row: RacketView
  blocked: string | null
}) {
  const action = useRow(
    'racket:edit',
    'racket:delete',
    {
      faction_id: row.faction?.id ?? 0,
      settlement_id: row.settlement?.id ?? 0,
      racket: row.racket,
    },
    blocked
  )
  const spec = RACKETS[row.racket]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={
        <>
          <Ref node={row.faction} empty='a lost organisation' />
          {' in '}
          <Ref node={row.settlement} empty='a lost town' />
          {` · ${row.income} coin a season since epoch ${row.since_epoch}`}
        </>
      }
      removeLabel='Break'
      editTitle='Set the racket'
      note='A racket turns turf into coin.'
      fields={[{ key: 'income', label: 'Income', kind: 'number', min: 0 }]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function PayrollCard({
  row,
  blocked,
}: {
  row: PayrollView
  blocked: string | null
}) {
  const action = useRow(
    'payroll:edit',
    'payroll:delete',
    { faction_id: row.faction?.id ?? 0, official_id: row.official?.id ?? 0 },
    blocked
  )
  return (
    <Held
      icon={Coins}
      tone='warning'
      title={<Ref node={row.official} empty='a lost official' />}
      caption={
        <>
          {'Paid by '}
          <Ref node={row.faction} empty='a lost organisation' />
          {` · ${row.bribe} coin a season since epoch ${row.since_epoch}`}
        </>
      }
      removeLabel='Off the payroll'
      editTitle='Set the bribe'
      note='Officials on the payroll turn suppression aside.'
      fields={[{ key: 'bribe', label: 'Bribe', kind: 'number', min: 0 }]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function StanceCard({
  row,
  blocked,
}: {
  row: CrimeStanceView
  blocked: string | null
}) {
  const action = useRow(
    'crime_stance:edit',
    'crime_stance:delete',
    { polity_id: row.polity?.id ?? 0, faction_id: row.faction?.id ?? 0 },
    blocked
  )
  const spec = STANCES[row.stance]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={<Ref node={row.faction} empty='a lost organisation' />}
      caption={
        <>
          {`${spec.label} by `}
          <Ref node={row.polity} empty='a lost realm' />
          {` since epoch ${row.since_epoch}`}
        </>
      }
      removeLabel='Drop'
      editTitle='Set the stance'
      note='Suppression takes turf; co-opting lowers crime and buys informers and privateers.'
      fields={[
        { key: 'stance', label: 'Stance', kind: 'pick', table: table(STANCES) },
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: 100,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter label='Strength' value={row.strength} tone='success' />
    </Held>
  )
}

function LawCard({
  orderId,
  row,
  blocked,
}: {
  orderId: number
  row: OrderLawView
  blocked: string | null
}) {
  const action = useRow(
    'order_law:edit',
    'order_law:delete',
    { faction_id: orderId, law: row.law },
    blocked
  )
  const spec = ORDER_LAWS[row.law]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={spec.label}
      caption={
        row.strength >= 70
          ? 'Breaking it means being cast out'
          : 'Breaking it means a fine'
      }
      removeLabel='Strike'
      editTitle='Set the law'
      note='The order’s tribunal judges those who break it.'
      fields={[
        { key: 'strength', label: 'Weight', kind: 'number', min: 0, max: 100 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter label='Weight' value={row.strength} tone='warning' />
    </Held>
  )
}

function TribunalCard({
  row,
  blocked,
}: {
  row: TribunalView
  blocked: string | null
}) {
  const strike = useUrbanAction(
    'tribunal:strike',
    (_: void) => ({ trial_id: row.id }),
    'The judgement is struck'
  )
  const busy = why(blocked, strike.isPending)
  const verdict = VERDICTS[row.verdict]
  return (
    <RecordRow
      icon={verdict.icon}
      tone={verdict.tone}
      title={
        <>
          <Ref node={row.accused} empty='a lost member' />
          {` · ${verdict.label}`}
        </>
      }
      caption={
        <>
          {`${ORDER_LAWS[row.law].label}, judged by `}
          <Ref node={row.order} empty='a lost order' />
          {` in epoch ${row.epoch}${row.fine ? ` · fined ${row.fine}` : ''}`}
        </>
      }
      aside={
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <Trash2 />
          Strike
        </Button>
      }
    />
  )
}

function PostCard({
  row,
  blocked,
}: {
  row: TradingPostView
  blocked: string | null
}) {
  const action = useRow(
    'trading_post:edit',
    'trading_post:close',
    { structure_id: row.structure?.id ?? 0 },
    blocked
  )
  return (
    <Held
      icon={Store}
      tone='gold'
      title={<Ref node={row.structure} empty='a lost post' />}
      caption={
        <>
          <Ref node={row.owner} empty='no house' />
          {' in '}
          <Ref node={row.host} empty='a lost town' />
          {` since epoch ${row.since_epoch}`}
        </>
      }
      removeLabel='Close'
      editTitle='Set the post'
      note='Informants learn the host’s secrets; stored goods let the house play markets.'
      fields={[
        { key: 'informants', label: 'Informants', kind: 'number', min: 0 },
        { key: 'goods', label: 'Goods stored', kind: 'number', min: 0 },
        {
          key: 'owner_entity_id',
          label: 'Owning house (id)',
          kind: 'number',
          min: 1,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Informants', String(row.informants)],
          ['Goods stored', String(row.goods)],
        ]}
      />
    </Held>
  )
}

function ConvoyCard({
  row,
  blocked,
}: {
  row: ConvoyView
  blocked: string | null
}) {
  const action = useRow(
    'convoy:edit',
    'convoy:delete',
    { convoy_id: row.id },
    blocked
  )
  const status = CONVOY_STATUS[row.status]
  const cargo = Object.entries(row.cargo)
  const passengers = Object.entries(row.passengers)
  return (
    <Held
      icon={status.icon}
      tone={status.tone}
      title={
        <>
          <Ref node={row.route} empty='a lost route' />
          {` · ${status.label}`}
        </>
      }
      caption={
        <>
          {'Owned by '}
          <Ref node={row.owner} empty='no one' />
          {` · set out in epoch ${row.departed_epoch}${row.arrived_epoch !== null && row.arrived_epoch !== undefined ? `, arrived in epoch ${row.arrived_epoch}` : ''} · season ${row.season}`}
        </>
      }
      removeLabel='Strike'
      editTitle='Set the convoy'
      note='A route carries what its convoys hold; guards turn raiders away.'
      fields={[
        { key: 'guards', label: 'Guards', kind: 'number', min: 0 },
        { key: 'capacity', label: 'Capacity', kind: 'number', min: 0 },
        { key: 'animals', label: 'Animals', kind: 'number', min: 0 },
        { key: 'vehicles', label: 'Wagons or boats', kind: 'number', min: 0 },
        {
          key: 'status',
          label: 'Status',
          kind: 'pick',
          table: table(CONVOY_STATUS),
        },
        {
          key: 'preservation',
          label: 'Preservation',
          kind: 'pick',
          table: table(PRESERVATION),
        },
        { key: 'season', label: 'Season', kind: 'number', min: 0 },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='flex min-w-0 flex-wrap gap-1.5'>
        <Chip icon={Truck}>{`${row.capacity} capacity`}</Chip>
        <Chip>{`${plural(row.animals, 'animal', 'animals')}, ${plural(row.vehicles, 'vehicle', 'vehicles')}, ${plural(row.guards, 'guard', 'guards')}`}</Chip>
        <Chip icon={PRESERVATION[row.preservation].icon}>
          {PRESERVATION[row.preservation].label}
        </Chip>
        {row.region && <Chip>{`Last seen at ${row.region.name}`}</Chip>}
        <StratumBadge stratum={row.stratum} prefix='Travelling the' />
        {cargo.map(([good, amount]) => (
          <Chip key={good}>{`${amount} ${good.replace('_', ' ')}`}</Chip>
        ))}
        {passengers.map(([kind, count]) => (
          <Chip key={kind} icon={Users}>{`${count} ${kind}`}</Chip>
        ))}
      </div>
    </Held>
  )
}

function FleetCard({
  row,
  blocked,
}: {
  row: FleetView
  blocked: string | null
}) {
  const action = useRow(
    'fleet:edit',
    'fleet:delete',
    { owner_id: row.owner?.id ?? 0, kind: row.kind },
    blocked
  )
  const spec = TRANSPORT[row.kind]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={`${row.count} ${spec.label.toLowerCase()}`}
      caption={
        <>
          {'Of '}
          <Ref node={row.owner} empty='no one' />
          {` · ${plural(row.age, 'epoch', 'epochs')} old`}
        </>
      }
      removeLabel='Take away'
      editTitle='Set the fleet'
      note='A worn fleet carries less and is replaced at a cost.'
      fields={[
        { key: 'count', label: 'Count', kind: 'number', min: 0 },
        { key: 'age', label: 'Age', kind: 'number', min: 0 },
        {
          key: 'condition',
          label: 'Condition',
          kind: 'number',
          min: 0,
          max: 100,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter label='Condition' value={row.condition} tone='success' />
    </Held>
  )
}

function PlayCard({
  row,
  blocked,
}: {
  row: MarketPlayView
  blocked: string | null
}) {
  const action = useRow(
    'market_play:edit',
    'market_play:delete',
    {
      holder_id: row.holder?.id ?? 0,
      settlement_id: row.settlement?.id ?? 0,
      commodity: row.commodity,
      play: row.play,
    },
    blocked
  )
  const spec = PLAYS[row.play]
  return (
    <Held
      icon={spec.icon}
      tone={spec.tone}
      title={`${spec.label}: ${COMMODITIES[row.commodity].toLowerCase()}`}
      caption={
        <>
          <Ref node={row.holder} empty='a lost house' />
          {' at '}
          <Ref node={row.settlement} empty='a lost market' />
          {` · since epoch ${row.since_epoch}${row.until_epoch !== null && row.until_epoch !== undefined ? `, until epoch ${row.until_epoch}` : ''}`}
        </>
      }
      removeLabel='End'
      editTitle='Set the play'
      note='A fair-market law or an association’s monopoly undoes part of it.'
      fields={[
        {
          key: 'strength',
          label: 'Strength',
          kind: 'number',
          min: 0,
          max: 100,
        },
        {
          key: 'until_epoch',
          label: 'Lasts until epoch',
          kind: 'number',
          min: 0,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter label='Strength' value={row.strength} tone='warning' />
    </Held>
  )
}

function CrimeForge({
  nodeId,
  type,
  blocked,
}: {
  nodeId: number
  type: string | null
  blocked: string | null
}) {
  const [faction, setFaction] = useState<number | null>(
    type === 'faction' ? nodeId : null
  )
  const [target, setTarget] = useState<number | null>(null)
  const [racket, setRacket] = useState('protection')
  const [stance, setStance] = useState('suppress')
  const racketSet = useUrbanAction(
    'racket:set',
    (_: void) => ({
      faction_id: faction ?? 0,
      settlement_id: target ?? 0,
      racket: racket as RacketView['racket'],
    }),
    'The racket runs'
  )
  const payroll = useUrbanAction(
    'payroll:add',
    (_: void) => ({ faction_id: faction ?? 0, official_id: target ?? 0 }),
    'On the payroll'
  )
  const stanceSet = useUrbanAction(
    'crime_stance:set',
    (_: void) => ({
      polity_id: target ?? 0,
      faction_id: faction ?? 0,
      stance: stance as CrimeStanceView['stance'],
    }),
    'The realm takes its stance'
  )
  const missing =
    faction === null || target === null
      ? 'Choose a criminal organisation and what it acts on'
      : null
  const busy = why(
    blocked ?? missing,
    racketSet.isPending,
    payroll.isPending,
    stanceSet.isPending
  )
  return (
    <ForgeCard
      icon={RACKETS.gambling.icon}
      tone='danger'
      title='Shape the underworld'
      note='Give an organisation a racket in a town, an official on its payroll, or a realm’s stance against it.'
      columns={4}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => racketSet.mutate()}
          >
            <Plus />
            Racket in that town
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => payroll.mutate()}
          >
            <Coins />
            Pay that official
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => stanceSet.mutate()}
          >
            <Gavel />
            That realm’s stance
          </Button>
        </div>
      }
    >
      <NodePicker
        label='Criminal organisation'
        value={faction}
        onChange={setFaction}
        blocked={blocked}
        types={['faction']}
      />
      <NodePicker
        label='Town, official or realm'
        value={target}
        onChange={setTarget}
        blocked={blocked}
        types={['settlement', 'mortal', 'polity']}
      />
      <MindPicker
        label='Racket'
        value={racket}
        table={table(RACKETS)}
        blocked={blocked}
        onPick={setRacket}
      />
      <MindPicker
        label='Stance'
        value={stance}
        table={table(STANCES)}
        blocked={blocked}
        onPick={setStance}
      />
    </ForgeCard>
  )
}

function TurfForge({
  districts,
  blocked,
}: {
  districts: DistrictUrbanView[]
  blocked: string | null
}) {
  const [district, setDistrict] = useState(
    districts[0] ? String(districts[0].id) : 'none'
  )
  const [faction, setFaction] = useState<number | null>(null)
  const [strength, setStrength] = useState('40')
  const set = useUrbanAction(
    'turf:set',
    (_: void) => ({
      district_id: Number(district),
      faction_id: faction ?? 0,
      strength: Number(strength),
    }),
    'The streets are held'
  )
  const missing =
    districts.length === 0
      ? 'Turf is held in the districts of a town'
      : faction === null
        ? 'Choose a criminal organisation'
        : null
  const busy = why(blocked ?? missing, set.isPending)
  const choices = Object.fromEntries(
    districts.map((row) => [
      String(row.id),
      `${DISTRICT_SPEC[row.kind].label} · level ${row.level}`,
    ])
  )
  return (
    <ForgeCard
      icon={RACKETS.protection.icon}
      tone='danger'
      title='Give an organisation turf'
      note='Turf grows under a weak watch and two organisations on the same streets fight for them.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => set.mutate()}
        >
          <Plus />
          Hold it
        </Button>
      }
    >
      <MindPicker
        label='District'
        value={district}
        table={choices}
        blocked={blocked}
        onPick={setDistrict}
      />
      <NodePicker
        label='Criminal organisation'
        value={faction}
        onChange={setFaction}
        blocked={blocked}
        types={['faction']}
      />
      <MindPicker
        label='Hold'
        value={strength}
        table={STRENGTHS}
        blocked={blocked}
        onPick={setStrength}
      />
    </ForgeCard>
  )
}

function OrderForge({
  orderId,
  blocked,
}: {
  orderId: number | null
  blocked: string | null
}) {
  const [law, setLaw] = useState('share_discoveries')
  const [accused, setAccused] = useState<number | null>(null)
  const set = useUrbanAction(
    'order_law:set',
    (_: void) => ({
      faction_id: orderId ?? 0,
      law: law as OrderLawView['law'],
    }),
    'The order keeps the law'
  )
  const convene = useUrbanAction(
    'tribunal:convene',
    (_: void) => ({
      faction_id: orderId ?? 0,
      law: law as OrderLawView['law'],
      accused_id: accused ?? 0,
    }),
    'The tribunal sits'
  )
  const busy = why(
    blocked ??
      (orderId === null ? 'Laws and tribunals belong to magical orders' : null),
    set.isPending,
    convene.isPending
  )
  return (
    <ForgeCard
      icon={Gavel}
      tone='verdigris'
      title='Laws and tribunals of the order'
      note='Give the order a law, or convene its tribunal against a member who broke one.'
      columns={2}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => set.mutate()}
          >
            <Plus />
            Keep the law
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null || accused === null}
            disabledReason={
              busy ?? (accused === null ? 'Choose the accused' : undefined)
            }
            onClick={() => convene.mutate()}
          >
            <Gavel />
            Convene the tribunal
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Law'
        value={law}
        table={table(ORDER_LAWS)}
        blocked={blocked}
        onPick={setLaw}
      />
      <NodePicker
        label='Accused'
        value={accused}
        onChange={setAccused}
        blocked={blocked}
        types={['mortal']}
      />
    </ForgeCard>
  )
}

function TradeForge({
  nodeId,
  type,
  blocked,
}: {
  nodeId: number
  type: string | null
  blocked: string | null
}) {
  const [house, setHouse] = useState<number | null>(
    type === 'faction' ? nodeId : null
  )
  const [place, setPlace] = useState<number | null>(
    type === 'settlement' ? nodeId : null
  )
  const [route, setRoute] = useState<number | null>(
    type === 'trade_route' ? nodeId : null
  )
  const [good, setGood] = useState('grain')
  const [play, setPlay] = useState('corner')
  const [kind, setKind] = useState('animal_carts')
  const post = useUrbanAction(
    'trading_post:open',
    (_: void) => ({ owner_id: house ?? 0, host_id: place ?? 0 }),
    'The post opens'
  )
  const send = useUrbanAction(
    'convoy:send',
    (_: void) => ({ route_id: route ?? 0 }),
    'A convoy sets out'
  )
  const fleet = useUrbanAction(
    'fleet:set',
    (_: void) => ({
      owner_id: house ?? place ?? 0,
      kind: kind as FleetView['kind'],
      count: 10,
    }),
    'The fleet is set'
  )
  const corner = useUrbanAction(
    'market_play:set',
    (_: void) => ({
      holder_id: house ?? 0,
      settlement_id: place ?? 0,
      commodity: good as MarketPlayView['commodity'],
      play: play as MarketPlayView['play'],
    }),
    'The market is played'
  )
  const pending = why(
    blocked,
    post.isPending,
    send.isPending,
    fleet.isPending,
    corner.isPending
  )
  const pair =
    pending ??
    (house === null || place === null
      ? 'Choose a merchant house and a town'
      : null)
  return (
    <ForgeCard
      icon={Store}
      tone='gold'
      title='Trade, convoys and markets'
      note='Open a trading post, send a convoy, give an owner carriers of any kind, or corner or flood a market.'
      columns={4}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={pair !== null}
            disabledReason={pair ?? undefined}
            onClick={() => post.mutate()}
          >
            <Store />
            Open a post there
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={pending !== null || route === null}
            disabledReason={
              pending ?? (route === null ? 'Choose a trade route' : undefined)
            }
            onClick={() => send.mutate()}
          >
            <Truck />
            Send a convoy
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={pending !== null || (house === null && place === null)}
            disabledReason={
              pending ??
              (house === null && place === null ? 'Choose an owner' : undefined)
            }
            onClick={() => fleet.mutate()}
          >
            <Truck />
            Give a fleet
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={pair !== null}
            disabledReason={pair ?? undefined}
            onClick={() => corner.mutate()}
          >
            <Coins />
            Play the market
          </Button>
        </div>
      }
    >
      <NodePicker
        label='Merchant house'
        value={house}
        onChange={setHouse}
        blocked={blocked}
        types={['faction']}
      />
      <NodePicker
        label='Town'
        value={place}
        onChange={setPlace}
        blocked={blocked}
        types={COMMUNITY_TYPES}
      />
      <NodePicker
        label='Trade route'
        value={route}
        onChange={setRoute}
        blocked={blocked}
        types={['trade_route']}
      />
      <MindPicker
        label='Fleet'
        value={kind}
        table={table(TRANSPORT)}
        blocked={blocked}
        onPick={setKind}
      />
      <MindPicker
        label='Good'
        value={good}
        table={{
          grain: 'Grain',
          timber: 'Timber',
          cloth: 'Cloth',
          luxuries: 'Luxuries',
          ore: 'Ore',
          fish: 'Fish',
        }}
        blocked={blocked}
        onPick={setGood}
      />
      <MindPicker
        label='Play'
        value={play}
        table={table(PLAYS)}
        blocked={blocked}
        onPick={setPlay}
      />
    </ForgeCard>
  )
}

function UrbanBody({
  data,
  type,
  blocked,
}: {
  data: NodeUrbanView
  type: string | null
  blocked: string | null
}) {
  const nodeId = data.node.id
  const order = type === 'faction' ? nodeId : null
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <KpiTile
          label='Districts'
          value={data.districts.length}
          icon={URBAN_ICON}
          tone='verdigris'
        />
        <KpiTile
          label='Homeless'
          value={data.town?.homeless ?? 0}
          icon={Users}
          tone='danger'
        />
        <KpiTile
          label='Criminal holds'
          value={
            data.turf.length +
            data.districts.reduce((sum, row) => sum + row.turf.length, 0)
          }
          icon={RACKETS.protection.icon}
          tone='warning'
        />
        <KpiTile
          label='Convoys'
          value={data.convoys.length}
          icon={Truck}
          tone='gold'
        />
      </div>
      {data.town ? (
        <TownCard townId={nodeId} town={data.town} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          Growth, homes and the homeless belong to towns.
        </Muted>
      )}
      <Listed
        title='Districts'
        items={data.districts}
        empty='No district stands here.'
        noun={['district', 'districts']}
        itemKey={(row) => row.id}
      >
        {(row) => <DistrictCard district={row} blocked={blocked} />}
      </Listed>
      {data.placement ? (
        <PlacementCard
          structureId={nodeId}
          placement={data.placement}
          blocked={blocked}
        />
      ) : (
        <Muted variant='caption'>
          Only a structure in a town stands in a district.
        </Muted>
      )}
      <Listed
        title='Turf it holds'
        items={data.turf}
        empty='It holds no streets.'
        noun={['hold', 'holds']}
        itemKey={(row) => `${row.district_id}-${row.faction?.id}`}
      >
        {(row) => <TurfCard row={row} blocked={blocked} />}
      </Listed>
      <TurfForge districts={data.districts} blocked={blocked} />
      <Listed
        title='Rackets'
        items={data.rackets}
        empty='No racket runs here.'
        noun={['racket', 'rackets']}
        itemKey={(row) =>
          `${row.faction?.id}-${row.settlement?.id}-${row.racket}`
        }
      >
        {(row) => <RacketCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Payroll'
        items={data.payroll}
        empty='No official is bought here.'
        noun={['official', 'officials']}
        itemKey={(row) => `${row.faction?.id}-${row.official?.id}`}
      >
        {(row) => <PayrollCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Stances against crime'
        items={data.stances}
        empty='No realm takes a stance here.'
        noun={['stance', 'stances']}
        itemKey={(row) => `${row.polity?.id}-${row.faction?.id}`}
      >
        {(row) => <StanceCard row={row} blocked={blocked} />}
      </Listed>
      <CrimeForge nodeId={nodeId} type={type} blocked={blocked} />
      <Listed
        title='Laws of the order'
        items={data.laws}
        empty='It keeps no law among mages.'
        noun={['law', 'laws']}
        itemKey={(row) => row.law}
      >
        {(row) => <LawCard orderId={nodeId} row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Tribunals'
        items={data.tribunals}
        empty='No tribunal has sat here.'
        noun={['judgement', 'judgements']}
        itemKey={(row) => row.id}
      >
        {(row) => <TribunalCard row={row} blocked={blocked} />}
      </Listed>
      <OrderForge orderId={order} blocked={blocked} />
      <Listed
        title='Trading posts'
        items={data.posts}
        empty='No trading post stands here.'
        noun={['post', 'posts']}
        itemKey={(row) => row.structure?.id ?? 0}
      >
        {(row) => <PostCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Convoys'
        items={data.convoys}
        empty='No convoy travels here.'
        noun={['convoy', 'convoys']}
        itemKey={(row) => row.id}
      >
        {(row) => <ConvoyCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Fleets'
        items={data.fleets}
        empty='It owns no carriers.'
        noun={['fleet', 'fleets']}
        itemKey={(row) => row.kind}
      >
        {(row) => <FleetCard row={row} blocked={blocked} />}
      </Listed>
      <Listed
        title='Market plays'
        items={data.plays}
        empty='No market is played here.'
        noun={['play', 'plays']}
        itemKey={(row) =>
          `${row.holder?.id}-${row.settlement?.id}-${row.commodity}-${row.play}`
        }
      >
        {(row) => <PlayCard row={row} blocked={blocked} />}
      </Listed>
      <TradeForge nodeId={nodeId} type={type} blocked={blocked} />
    </div>
  )
}

export function UrbanSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeUrban(nodeId)
  const type = useEntityType(nodeId)
  return (
    <Section
      id='section-urban'
      title='Streets, trade and orders'
      description='Districts, their homes, services and land value; the homeless and the slums; criminal turf, rackets and payrolls; magical orders, their laws and tribunals; trading posts, convoys, fleets and the markets merchants play.'
      icon={URBAN_ICON}
      tone='gold'
    >
      <div data-surface='UrbanSection' className='flex min-w-0 flex-col gap-3'>
        {query.isPending ? (
          <LoadingBlock label='Reading the streets' />
        ) : query.isError ? (
          <EmptyState
            icon={URBAN_ICON}
            size='inline'
            title='The streets could not be read'
            description={query.error.message}
          />
        ) : (
          <UrbanBody data={query.data} type={type} blocked={readOnlyReason} />
        )}
      </div>
    </Section>
  )
}
