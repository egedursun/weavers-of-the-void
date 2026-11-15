import { useState } from 'react'
import { Flag, Plus, Users } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmptyState, LoadingBlock, Section } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { useNodeKind } from '@/features/cycles/model'
import { StepButton, TextField } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/wilds/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type HonoursNodeView, useHonoursAction, useNodeHonours } from './api'
import { GRANTS, HONOURS, HONOURS_ICON, TAB_ICONS } from './labels'
import { MANY, SPAN, useHonoursRow } from './model'

type View = HonoursNodeView
type Unit = View['units'][number]
type Pane = keyof typeof TAB_ICONS
const OWNER_TYPES = ['polity', 'settlement', 'people', 'faction'] as const
const POLITY_TYPES = ['polity'] as const
const TOWN_TYPES = ['settlement'] as const
const WAR_TYPES = ['event'] as const

function HonourCard({
  row,
  blocked,
}: {
  row: Unit['honours'][number]
  blocked: string | null
}) {
  const action = useHonoursRow(
    'unit_honour:edit',
    'unit_honour:delete',
    row.id,
    blocked
  )
  const honour = HONOURS[row.kind]
  return (
    <Held
      icon={honour.icon}
      tone={honour.tone}
      title={honour.label}
      caption={`${row.note || 'Unrecorded'}, epoch ${row.epoch}`}
      removeLabel='Strike it'
      editTitle='Set the honour'
      note='Honours raise the esprit of a unit; a massacre lowers it and is remembered.'
      fields={[
        { key: 'kind', label: 'Honour', kind: 'pick', table: table(HONOURS) },
        { key: 'note', label: 'Where it was won', kind: 'text' },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function UnitCard({ row, blocked }: { row: Unit; blocked: string | null }) {
  const action = useHonoursRow(
    'named_unit:edit',
    'named_unit:delete',
    row.id,
    blocked
  )
  const [kind, setKind] = useState('victory')
  const [place, setPlace] = useState('')
  const bestowing = useHonoursAction(
    'unit_honour:create',
    (_: void) => ({
      named_unit_id: row.id,
      kind: kind as Unit['honours'][number]['kind'],
      note: place.trim(),
    }),
    'The honour is set on the standard'
  )
  const bestowBusy = why(blocked, bestowing.isPending)
  return (
    <Held
      icon={Flag}
      tone={row.disbanded_epoch === null ? 'gold' : 'muted'}
      title={`${row.name}${row.nickname ? `, called ${row.nickname}` : ''}`}
      caption={
        <>
          Of <Ref node={row.owner} empty='no realm' />, raised from{' '}
          <Ref node={row.raised_from} empty='no one land' />; {row.battles}{' '}
          {row.battles === 1 ? 'battle' : 'battles'}; formed epoch{' '}
          {row.formed_epoch}
          {row.disbanded_epoch !== null
            ? `; disbanded epoch ${row.disbanded_epoch}`
            : row.unit_id === null
              ? '; waiting to be raised again'
              : ''}
        </>
      }
      removeLabel='Strike it from the rolls'
      editTitle='Set the unit'
      note='Esprit steadies a unit in battle; disbanding an honoured unit costs its realm renown, and one raised again from its veterans regains part of it.'
      fields={[
        { key: 'name', label: 'Name of the unit', kind: 'text' },
        { key: 'nickname', label: 'Nickname', kind: 'text' },
        { key: 'esprit', label: 'Esprit', kind: 'number', min: 0, max: SPAN },
        { key: 'battles', label: 'Battles', kind: 'number', min: 0, max: MANY },
        {
          key: 'unit_id',
          label: 'Unit of an army',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'owner_entity_id',
          label: 'Realm',
          kind: 'node',
          types: OWNER_TYPES,
        },
        {
          key: 'raised_from_entity_id',
          label: 'Raised from',
          kind: 'node',
          types: OWNER_TYPES,
        },
        {
          key: 'disbanded_epoch',
          label: 'Disbanded in epoch',
          kind: 'number',
          min: 0,
          max: MANY,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Esprit (${row.esprit} of ${SPAN})`}
        value={row.esprit}
        tone='warning'
        icon={Flag}
      />
      <Listed
        title='Honours on its standard'
        items={row.honours}
        empty='No honour stands on this standard yet.'
        noun={['honour', 'honours']}
        itemKey={(item) => item.id}
      >
        {(item) => <HonourCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={HONOURS.victory.icon}
        tone='gold'
        title='Set an honour on its standard'
        note='The honour moves its esprit at once.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={bestowBusy !== null}
            disabledReason={bestowBusy ?? undefined}
            onClick={() => bestowing.mutate()}
          >
            <Plus />
            Set it
          </Button>
        }
      >
        <MindPicker
          label='Honour'
          value={kind}
          table={table(HONOURS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setKind}
        />
        <TextField
          label='Where it was won'
          value={place}
          blocked={blocked}
          onChange={setPlace}
        />
      </ForgeCard>
    </Held>
  )
}

function UnitsPanel({ data, blocked }: { data: View; blocked: string | null }) {
  const choices = Object.fromEntries(
    data.choices.map((row) => [String(row.id), `${row.label} (${row.count})`])
  )
  const [name, setName] = useState('')
  const [unit, setUnit] = useState(
    data.choices[0] ? String(data.choices[0].id) : 'none'
  )
  const [esprit, setEsprit] = useState('40')
  const naming = useHonoursAction(
    'named_unit:create',
    (_: void) => ({
      name: name.trim(),
      unit_id: unit === 'none' ? null : Number(unit),
      owner_id: data.realm?.id ?? null,
      raised_from_id: null,
      esprit: Math.max(0, Math.min(SPAN, Number(esprit) || 0)),
      nickname: null,
    }),
    'The unit takes its name'
  )
  const nameBusy = why(
    blocked ?? (name.trim() === '' ? 'Give the unit a name first' : null),
    naming.isPending
  )
  return (
    <div data-surface='UnitsPanel' className='flex min-w-0 flex-col gap-4'>
      <Facts
        items={[
          ['Realm', <Ref key='realm' node={data.realm} empty='no realm' />],
          ['Units of this army', String(data.choices.length)],
        ]}
      />
      <Bars
        chart='chart-units'
        title='The esprit of each named unit'
        legend={[{ text: 'Esprit', variant: 'warning' }]}
        rows={data.units.map((row) => ({
          key: String(row.id),
          caption: `${row.name}: ${row.esprit}, ${row.honours.length} ${row.honours.length === 1 ? 'honour' : 'honours'}`,
          segments: [{ value: row.esprit, fill: 'fill-warning' }],
        }))}
        max={SPAN}
        noun={['unit', 'units']}
        empty='No unit here bears a name yet; units raised from one land take a name after their first battle.'
      />
      <Listed
        title='Named units'
        items={data.units}
        empty='No unit here bears a name yet.'
        noun={['unit', 'units']}
        itemKey={(item) => item.id}
      >
        {(item) => <UnitCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Flag}
        tone='gold'
        title='Name a unit'
        note='A unit of this army, or one waiting to be raised again, takes a name and a standard.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={nameBusy !== null}
            disabledReason={nameBusy ?? undefined}
            onClick={() => naming.mutate()}
          >
            <Plus />
            Name it
          </Button>
        }
      >
        <TextField
          label='Name of the unit'
          value={name}
          blocked={blocked}
          onChange={setName}
        />
        <MindPicker
          label='Unit of an army'
          value={unit}
          table={{ none: 'None yet', ...choices }}
          placeholder='Choose'
          blocked={blocked}
          onPick={setUnit}
        />
        <NumberField
          label='Esprit'
          value={esprit}
          min={0}
          max={SPAN}
          disabled={blocked !== null}
          onChange={setEsprit}
        />
      </ForgeCard>
    </div>
  )
}

function GrantCard({
  row,
  blocked,
}: {
  row: View['grants'][number]
  blocked: string | null
}) {
  const action = useHonoursRow(
    'veteran_grant:edit',
    'veteran_grant:delete',
    row.id,
    blocked
  )
  const grant = GRANTS[row.kind]
  return (
    <Held
      icon={grant.icon}
      tone={grant.tone}
      title={`${grant.label} for ${row.veterans} ${row.veterans === 1 ? 'veteran' : 'veterans'}`}
      caption={
        <>
          Granted by <Ref node={row.polity} /> in epoch {row.epoch}
          {row.settlement ? (
            <>
              ; settled in <Ref node={row.settlement} />
            </>
          ) : null}
          {row.war ? (
            <>
              ; after <Ref node={row.war} />
            </>
          ) : null}
        </>
      }
      removeLabel='Withdraw it'
      editTitle='Set the grant'
      note='Pensions cost the treasury each epoch and sour the towns when unpaid; a colony holds to the ruler who granted it.'
      fields={[
        { key: 'kind', label: 'Granted', kind: 'pick', table: table(GRANTS) },
        {
          key: 'veterans',
          label: 'Veterans',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'settlement_entity_id',
          label: 'Colony',
          kind: 'node',
          types: TOWN_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    />
  )
}

function VeteransPanel({
  data,
  blocked,
}: {
  data: View
  blocked: string | null
}) {
  const [polity, setPolity] = useState<number | null>(data.realm?.id ?? null)
  const [kind, setKind] = useState('pension')
  const [veterans, setVeterans] = useState('20')
  const [colony, setColony] = useState<number | null>(null)
  const [war, setWar] = useState<number | null>(null)
  const granting = useHonoursAction(
    'veteran_grant:create',
    (_: void) => ({
      polity_id: polity ?? 0,
      kind: kind as View['grants'][number]['kind'],
      veterans: Math.max(0, Math.min(MANY, Number(veterans) || 0)),
      settlement_id: colony,
      war_id: war,
    }),
    'The veterans are granted it'
  )
  const busy = why(
    blocked ??
      (polity === null ? 'Choose the realm that grants it first' : null),
    granting.isPending
  )
  return (
    <div data-surface='VeteransPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-veterans'
        title='Veterans in each grant'
        legend={[{ text: 'Veterans', variant: 'success' }]}
        rows={data.grants.map((row) => ({
          key: String(row.id),
          caption: `${GRANTS[row.kind].label}: ${row.veterans}, epoch ${row.epoch}`,
          segments: [{ value: row.veterans, fill: 'fill-success' }],
        }))}
        max={Math.max(1, ...data.grants.map((row) => row.veterans))}
        noun={['grant', 'grants']}
        empty='No veterans have been granted anything here; realms grant land or pensions when a war ends.'
      />
      <Listed
        title='Grants to veterans'
        items={data.grants}
        empty='No veterans have been granted anything here.'
        noun={['grant', 'grants']}
        itemKey={(item) => item.id}
      >
        {(item) => <GrantCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Users}
        tone='success'
        title='Grant veterans land or pensions'
        note='A pension is paid from the treasury for some epochs; land gives the veterans a colony.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => granting.mutate()}
          >
            <Plus />
            Grant it
          </Button>
        }
      >
        <NodePicker
          label='Realm'
          value={polity}
          onChange={setPolity}
          blocked={blocked}
          types={POLITY_TYPES}
        />
        <MindPicker
          label='Granted'
          value={kind}
          table={table(GRANTS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setKind}
        />
        <NumberField
          label='Veterans'
          value={veterans}
          min={0}
          max={MANY}
          disabled={blocked !== null}
          onChange={setVeterans}
        />
        <NodePicker
          label='Colony'
          value={colony}
          onChange={setColony}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <NodePicker
          label='After the war'
          value={war}
          onChange={setWar}
          blocked={blocked}
          types={WAR_TYPES}
        />
      </ForgeCard>
    </div>
  )
}

const PANES: { key: Pane; label: string; count: (data: View) => number }[] = [
  { key: 'units', label: 'Named units', count: (data) => data.units.length },
  { key: 'veterans', label: 'Veterans', count: (data) => data.grants.length },
]

export function HonoursSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeHonours(nodeId)
  const kind = useNodeKind(nodeId)
  const [pane, setPane] = useState<Pane | null>(null)
  const running = useHonoursAction(
    'honours:run',
    (_: void) => ({}),
    'Every grant to veterans and association is read'
  )
  const blocked = readOnlyReason
  return (
    <Section
      id='section-honours'
      title='Standards and veterans: named units, honours and grants'
      description='The named units of this army or realm, the honours on their standards and their esprit, and the land and pensions its veterans were granted. Every kind of thing shows these where they touch it, and a control that cannot apply here stays on screen and says why.'
      icon={HONOURS_ICON}
      tone='warning'
    >
      <div
        data-surface='HonoursSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading standards and veterans' />
        ) : query.isError ? (
          <EmptyState
            icon={HONOURS_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <Tabs
            value={pane ?? (kind === 'polity' ? 'veterans' : 'units')}
            onValueChange={(value) => setPane(value as Pane)}
          >
            <TabsList aria-label='Named units and veterans'>
              {PANES.map(({ key, label, count }) => {
                const Icon = TAB_ICONS[key]
                const total = count(query.data)
                return (
                  <TabsTrigger key={key} value={key}>
                    <Icon />
                    {label}
                    {total > 0 && (
                      <Badge size='sm' variant='secondary'>
                        {total}
                      </Badge>
                    )}
                  </TabsTrigger>
                )
              })}
            </TabsList>
            <TabsContent value='units' className='flex min-w-0 flex-col gap-6'>
              <UnitsPanel data={query.data} blocked={blocked} />
            </TabsContent>
            <TabsContent
              value='veterans'
              className='flex min-w-0 flex-col gap-6'
            >
              <VeteransPanel data={query.data} blocked={blocked} />
            </TabsContent>
          </Tabs>
        )}
        <StepButton
          icon={HONOURS_ICON}
          label='Read standards and veterans now'
          busy={why(blocked, running.isPending)}
          onClick={() => running.mutate()}
        />
      </div>
    </Section>
  )
}
