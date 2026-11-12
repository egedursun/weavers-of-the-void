import { useState } from 'react'
import {
  Coins,
  Gem,
  Handshake,
  Landmark,
  Scale,
  Shield,
  Swords,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { clamp, MANY, SPAN } from '@/features/cycles/model'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { OFFICES } from '@/features/entity/realm/labels'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type RegimeNodeView, useRegimeAction } from './api'
import { CLIENT_ROLES, STANCES } from './labels'
import { PATRON_TYPES, useRegimeRow, useRegimeStep } from './model'

type Tie = RegimeNodeView['ties'][number]
type Venal = RegimeNodeView['offices'][number]
type Base = NonNullable<RegimeNodeView['power_base']>

const NOT_REALM = 'Only a realm sells its seats and weighs its great subjects'
const KEPT = new Set(['ruler', 'heir_designate', 'regent'])

function seatLabel(kind: string) {
  return OFFICES[kind]?.label ?? kind.replace(/_/g, ' ')
}

function TieCard({ row, blocked }: { row: Tie; blocked: string | null }) {
  const action = useRegimeRow(
    'patronage:edit',
    'patronage:delete',
    { tie_id: row.id },
    blocked
  )
  const role = CLIENT_ROLES[row.role]
  return (
    <Held
      icon={role.icon}
      tone={role.tone}
      title={`${row.client.name}, client of ${row.patron.name}`}
      caption={`${role.label} · since epoch ${row.since_epoch}`}
      removeLabel='Cut the tie'
      editTitle='Set the tie'
      note='Favours owed and appointments bind clients to patrons; where institutions are weak, patrons place their clients in office and towns whose lords are clients vote for their patron.'
      fields={[
        {
          key: 'role',
          label: 'Client as',
          kind: 'pick',
          table: table(CLIENT_ROLES),
        },
        {
          key: 'strength',
          label: 'Strength of the tie',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Strength of the tie'
        value={row.strength}
        tone='verdigris'
        icon={Handshake}
      />
      <Facts
        items={[
          ['Patron', <Ref key='patron' node={row.patron} />],
          ['Client', <Ref key='client' node={row.client} />],
        ]}
      />
    </Held>
  )
}

function TieForge({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const [patron, setPatron] = useState<number | null>(nodeId)
  const [client, setClient] = useState<number | null>(null)
  const [role, setRole] = useState<keyof typeof CLIENT_ROLES>('retainer')
  const [strength, setStrength] = useState('40')
  const binding = useRegimeAction(
    'patronage:bind',
    (_: void) => ({
      patron_id: patron ?? 0,
      client_id: client ?? 0,
      role,
      strength: clamp(strength),
    }),
    'A patron takes a client'
  )
  const busy = why(
    patron === null || client === null
      ? 'Choose a patron and a client'
      : blocked,
    binding.isPending
  )
  return (
    <ForgeCard
      icon={Handshake}
      tone='verdigris'
      title='Bind a client to a patron'
      note='Any mortal can be the client of a mortal, house, realm or company.'
      columns={4}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => binding.mutate()}
        >
          <Handshake />
          Bind them
        </Button>
      }
    >
      <NodePicker
        label='Patron'
        value={patron}
        onChange={setPatron}
        blocked={blocked}
        types={PATRON_TYPES}
      />
      <NodePicker
        label='Client'
        value={client}
        onChange={setClient}
        blocked={blocked}
        types={['mortal']}
      />
      <MindPicker
        label='Client as'
        value={role}
        table={table(CLIENT_ROLES)}
        blocked={blocked}
        onPick={(value) => setRole(value as keyof typeof CLIENT_ROLES)}
      />
      <NumberField
        label='Strength'
        value={strength}
        min={0}
        max={SPAN}
        blocked={blocked}
        onChange={setStrength}
      />
    </ForgeCard>
  )
}

function VenalCard({ row, blocked }: { row: Venal; blocked: string | null }) {
  const action = useRegimeRow(
    'venal_office:edit',
    'venal_office:delete',
    { office_id: row.office_id },
    blocked
  )
  return (
    <Held
      icon={row.sinecure ? Gem : Coins}
      tone={row.sinecure ? 'verdigris' : 'gold'}
      title={`${row.sinecure ? 'Sinecure' : 'Bought seat'}: ${seatLabel(row.office_kind)} of ${row.polity.name}`}
      caption={`Since epoch ${row.sold_epoch}`}
      removeLabel='Free the seat from its purchase'
      editTitle='Set the seat'
      note='A bought seat repays its buyer each epoch until the buyer is content, and each one still repaying adds to the realm’s corruption. A sinecure gives its holder the income without the duty.'
      fields={[
        {
          key: 'price',
          label: 'Price paid',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'buyer_entity_id',
          label: 'Buyer',
          kind: 'node',
          types: ['mortal'],
        },
        { key: 'sinecure', label: 'A sinecure', kind: 'pick', table: YES_NO },
        {
          key: 'recouped',
          label: 'Recouped so far',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={
        <Chip
          icon={Landmark}
        >{`${row.recouped} of ${row.price} recouped`}</Chip>
      }
    >
      <Facts
        items={[
          [
            'Holder',
            <Ref key='holder' node={row.holder} empty='the seat is empty' />,
          ],
          [
            'Bought by',
            <Ref key='buyer' node={row.buyer} empty='granted, not sold' />,
          ],
        ]}
      />
    </Held>
  )
}

function SellForge({
  data,
  isRealm,
  blocked,
}: {
  data: RegimeNodeView
  isRealm: boolean
  blocked: string | null
}) {
  const seats = data.seats.filter((seat) => !KEPT.has(seat.kind))
  const [seat, setSeat] = useState<string>(
    seats[0] ? String(seats[0].office_id) : ''
  )
  const [buyer, setBuyer] = useState<number | null>(null)
  const [price, setPrice] = useState('300')
  const selling = useRegimeAction(
    'venal_office:sell',
    (_: void) => ({
      office_id: Number(seat),
      buyer_id: buyer ?? 0,
      price: clamp(price, MANY),
    }),
    'The seat is sold'
  )
  const granting = useRegimeAction(
    'venal_office:sinecure',
    (_: void) => ({ office_id: Number(seat), holder_id: buyer ?? 0 }),
    'The seat becomes a sinecure'
  )
  const reason = !isRealm
    ? NOT_REALM
    : seats.length === 0
      ? 'The realm has no seat that can be sold'
      : buyer === null
        ? 'Choose who takes the seat'
        : blocked
  const busy = why(reason, selling.isPending, granting.isPending)
  const pick = Object.fromEntries(
    seats.map((row) => [
      String(row.office_id),
      `${seatLabel(row.kind)}${row.holder ? ` (held by ${row.holder.name})` : ' (empty)'}`,
    ])
  )
  return (
    <ForgeCard
      icon={Coins}
      tone='gold'
      title='Sell a seat or make it a sinecure'
      note='The buyer pays the treasury and the seat repays the buyer; a sinecure is handed to a member of the ruling circle with its income and none of its duties.'
      columns={3}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => selling.mutate()}
          >
            <Coins />
            Sell it
          </Button>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => granting.mutate()}
          >
            <Gem />
            Make it a sinecure
          </Button>
        </div>
      }
    >
      <MindPicker
        label='Seat'
        value={seat}
        table={pick}
        blocked={isRealm ? blocked : NOT_REALM}
        onPick={setSeat}
      />
      <NodePicker
        label='Buyer or holder'
        value={buyer}
        onChange={setBuyer}
        blocked={isRealm ? blocked : NOT_REALM}
        types={['mortal']}
      />
      <NumberField
        label='Price'
        value={price}
        min={0}
        blocked={isRealm ? blocked : NOT_REALM}
        onChange={setPrice}
      />
    </ForgeCard>
  )
}

function BaseCard({ row, blocked }: { row: Base; blocked: string | null }) {
  const action = useRegimeRow(
    'power_base:edit',
    'power_base:delete',
    { mortal_id: row.mortal.id },
    blocked
  )
  const stance = STANCES[row.stance]
  return (
    <Held
      icon={stance.icon}
      tone={stance.tone}
      title={`${row.mortal.name}: ${stance.label.toLowerCase()}`}
      caption={`A power base of ${row.total} · weighed in epoch ${row.updated_epoch}`}
      removeLabel='Let it be weighed anew'
      editTitle='Set the power base'
      note='Holdings, troops led by the character and their clients, offices, wealth and renown make a power base. Against the ruler’s own it becomes a threat: defiance shakes the realm, extortion drains the treasury, a plot leads the next coup.'
      fields={[
        { key: 'holdings', label: 'Towns held', kind: 'number', min: 0 },
        {
          key: 'troops',
          label: 'Hundreds of loyal troops',
          kind: 'number',
          min: 0,
        },
        {
          key: 'offices',
          label: 'Offices held with clients',
          kind: 'number',
          min: 0,
        },
        { key: 'wealth', label: 'Wealth', kind: 'number', min: 0 },
        {
          key: 'popularity',
          label: 'Renown',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'threat',
          label: 'Threat to the throne',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'stance',
          label: 'Stance toward the ruler',
          kind: 'pick',
          table: table(STANCES),
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label='Threat to the throne'
        value={row.threat}
        tone='destructive'
        icon={Swords}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2 @xl/tiles:grid-cols-5'>
          <KpiTile
            label='Towns'
            value={row.holdings}
            icon={Landmark}
            tone='info'
          />
          <KpiTile
            label='Troops'
            value={row.troops}
            icon={Shield}
            tone='danger'
          />
          <KpiTile
            label='Offices'
            value={row.offices}
            icon={Users}
            tone='gold'
          />
          <KpiTile label='Wealth' value={row.wealth} icon={Coins} tone='gold' />
          <KpiTile
            label='Renown'
            value={row.popularity}
            icon={Scale}
            tone='verdigris'
          />
        </div>
      </div>
      <Facts
        items={[
          ['Realm', <Ref key='realm' node={row.polity} empty='no realm' />],
        ]}
      />
    </Held>
  )
}

function BaseForge({
  nodeId,
  isRealm,
  blocked,
}: {
  nodeId: number
  isRealm: boolean
  blocked: string | null
}) {
  const [mortal, setMortal] = useState<number | null>(null)
  const [threat, setThreat] = useState('50')
  const setting = useRegimeAction(
    'power_base:set',
    (_: void) => ({
      mortal_id: mortal ?? 0,
      polity_id: nodeId,
      threat: clamp(threat),
    }),
    'The power base is set'
  )
  const measuring = useRegimeStep(
    'power_base:measure',
    { polity_id: nodeId },
    isRealm ? blocked : NOT_REALM,
    'Weighed'
  )
  const busy = why(
    isRealm ? (mortal === null ? 'Choose a mortal' : blocked) : NOT_REALM,
    setting.isPending
  )
  return (
    <ForgeCard
      icon={Swords}
      tone='danger'
      title='Raise a power base'
      note='Make a subject of this realm as dangerous as you like, or weigh every great subject now.'
      columns={2}
      action={
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => setting.mutate()}
          >
            <Swords />
            Set it
          </Button>
          <StepButton
            icon={Scale}
            label='Weigh them all'
            busy={measuring.busy}
            onClick={measuring.run}
          />
        </div>
      }
    >
      <NodePicker
        label='Subject'
        value={mortal}
        onChange={setMortal}
        blocked={isRealm ? blocked : NOT_REALM}
        types={['mortal']}
      />
      <NumberField
        label='Threat'
        value={threat}
        min={0}
        max={SPAN}
        blocked={isRealm ? blocked : NOT_REALM}
        onChange={setThreat}
      />
    </ForgeCard>
  )
}

export function PatronagePanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: RegimeNodeView
  blocked: string | null
}) {
  const isRealm = kind === 'polity'
  const bases = [...(data.power_base ? [data.power_base] : []), ...data.bases]
  return (
    <div data-surface='PatronagePanel' className='flex min-w-0 flex-col gap-4'>
      <Listed
        title='Patrons and clients'
        items={data.ties}
        empty='No ties of patronage run through here.'
        noun={['tie', 'ties']}
        itemKey={(item) => item.id}
      >
        {(item) => <TieCard row={item} blocked={blocked} />}
      </Listed>
      <TieForge nodeId={nodeId} blocked={blocked} />
      <Listed
        title='Bought seats and sinecures'
        items={data.offices}
        empty='No seat here was bought or handed out as a sinecure.'
        noun={['seat', 'seats']}
        itemKey={(item) => item.office_id}
      >
        {(item) => <VenalCard row={item} blocked={blocked} />}
      </Listed>
      <SellForge data={data} isRealm={isRealm} blocked={blocked} />
      <Listed
        title='Power bases'
        items={bases}
        empty='No great subject has been weighed here.'
        noun={['power base', 'power bases']}
        itemKey={(item) => item.mortal.id}
      >
        {(item) => <BaseCard row={item} blocked={blocked} />}
      </Listed>
      <BaseForge nodeId={nodeId} isRealm={isRealm} blocked={blocked} />
    </div>
  )
}
