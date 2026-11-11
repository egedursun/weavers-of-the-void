import { useState } from 'react'
import {
  Beef,
  Droplets,
  Footprints,
  Leaf,
  Route,
  Split,
  Tent,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Chip, Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { type ConfederationView, type CyclesView, useCycleAction } from './api'
import { MOBILITY } from './labels'
import { clamp, MANY, SPAN, useRow, useStep } from './model'
import { NodeChips, NodeListPicker, StepButton } from './parts'

type Camp = NonNullable<CyclesView['camp']>

const NOT_TOWN = 'Only a settlement can take to the move'

function CampCard({
  townId,
  row,
  blocked,
}: {
  townId: number
  row: Camp
  blocked: string | null
}) {
  const action = useRow(
    'camp:edit',
    'camp:delete',
    { town_id: townId },
    blocked
  )
  const moving = useStep(
    'camp:move',
    { town_id: townId },
    blocked,
    'The camp moves on'
  )
  const [regions, setRegions] = useState<number[]>(
    row.circuit.map((region) => region.id)
  )
  const routing = useCycleAction(
    'camp:route',
    (_: void) => ({ town_id: townId, regions }),
    'The camp follows new pastures'
  )
  const mode = MOBILITY[row.mode]
  const here =
    row.circuit.length > 0
      ? row.circuit[row.season_index % row.circuit.length]
      : null
  return (
    <Held
      icon={mode.icon}
      tone={mode.tone}
      title={mode.label}
      caption={
        row.last_moved_epoch !== null
          ? `Last moved in epoch ${row.last_moved_epoch}`
          : 'Has not moved yet'
      }
      removeLabel='Strike the camp'
      editTitle='Set the camp'
      note='A camp follows its pastures each epoch; its herd grows on grazing and water and wears the land; strong riders take tribute from settled neighbours or raid them.'
      fields={[
        {
          key: 'mode',
          label: 'How it moves',
          kind: 'pick',
          table: table(MOBILITY),
        },
        {
          key: 'season_index',
          label: 'Pasture it is at',
          kind: 'number',
          min: 0,
        },
        { key: 'herd', label: 'Herd', kind: 'number', min: 0 },
        { key: 'grazing', label: 'Grazing', kind: 'number', min: 0, max: SPAN },
        { key: 'water', label: 'Water', kind: 'number', min: 0, max: SPAN },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-1 gap-2 @xl/tiles:grid-cols-3'>
          <KpiTile label='Herd' value={row.herd} icon={Beef} tone='gold' />
          <KpiTile
            label='Grazing'
            value={row.grazing}
            icon={Leaf}
            tone='success'
          />
          <KpiTile
            label='Water'
            value={row.water}
            icon={Droplets}
            tone='info'
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'At the pasture of',
            <Ref key='here' node={here} empty='no pasture' />,
          ],
        ]}
      />
      <NodeChips
        nodes={row.circuit}
        empty='No pastures on its circuit'
        icon={Footprints}
      />
      <NodeListPicker
        label='Pastures'
        value={regions}
        types={['region']}
        blocked={why(blocked, routing.isPending)}
        onChange={setRegions}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Route}
          label='Follow these pastures'
          busy={why(
            blocked ?? (regions.length === 0 ? 'Choose a pasture first' : null),
            routing.isPending
          )}
          onClick={() => routing.mutate()}
        />
        <StepButton
          icon={Footprints}
          label='Move on now'
          busy={
            row.mode === 'sedentary'
              ? 'A settled camp does not move'
              : moving.busy
          }
          onClick={moving.run}
        />
      </div>
    </Held>
  )
}

function CampForge({
  townId,
  isTown,
  blocked,
}: {
  townId: number
  isTown: boolean
  blocked: string | null
}) {
  const [mode, setMode] = useState<keyof typeof MOBILITY>('nomadic')
  const [herd, setHerd] = useState('200')
  const setting = useCycleAction(
    'camp:set',
    (_: void) => ({ town_id: townId, mode, herd: clamp(herd, MANY) }),
    'The camp takes to the move'
  )
  const busy = why(isTown ? blocked : NOT_TOWN, setting.isPending)
  return (
    <ForgeCard
      icon={Tent}
      tone='gold'
      title='Set it moving with its herds'
      note='Its circuit is drawn from the best pastures around it.'
      columns={2}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setting.mutate()}
        >
          <Tent />
          Take to the move
        </Button>
      }
    >
      <MindPicker
        label='How it moves'
        value={mode}
        table={table(MOBILITY)}
        blocked={busy}
        onPick={(value) => setMode(value as keyof typeof MOBILITY)}
      />
      <NumberField
        label='Herd'
        value={herd}
        min={0}
        blocked={busy}
        onChange={setHerd}
      />
    </ForgeCard>
  )
}

export function ConfederationCard({
  row,
  blocked,
}: {
  row: ConfederationView
  blocked: string | null
}) {
  const action = useRow(
    'confederation:edit',
    'confederation:delete',
    { confederation_id: row.id },
    blocked
  )
  const breaking = useStep(
    'confederation:dissolve',
    { confederation_id: row.id },
    blocked,
    'It breaks apart'
  )
  const [members, setMembers] = useState<number[]>(
    row.members.map((member) => member.id)
  )
  const joining = useCycleAction(
    'confederation:members',
    (_: void) => ({ confederation_id: row.id, members }),
    'Its camps are set'
  )
  const gone = row.dissolved_epoch !== null
  return (
    <Held
      icon={Users}
      tone={gone ? 'muted' : 'gold'}
      title={row.name}
      caption={
        gone
          ? `Formed in epoch ${row.formed_epoch}, broke apart in epoch ${row.dissolved_epoch}`
          : `Formed in epoch ${row.formed_epoch}`
      }
      removeLabel='Strike the confederation'
      editTitle='Set the confederation'
      note='Camps gathered under a charismatic leader raid as one and spare each other; when the leader dies the confederation breaks apart.'
      fields={[
        { key: 'name', label: 'Called', kind: 'text' },
        {
          key: 'leader_entity_id',
          label: 'Leader',
          kind: 'node',
          types: ['mortal'],
        },
        {
          key: 'dissolved_epoch',
          label: 'Broke apart in epoch',
          kind: 'number',
          min: 0,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Facts
        items={[
          ['Leader', <Ref key='leader' node={row.leader} empty='no leader' />],
        ]}
      />
      <NodeChips nodes={row.members} empty='No camps' icon={Tent} />
      <NodeListPicker
        label='Camps'
        value={members}
        types={['settlement']}
        blocked={why(blocked, joining.isPending)}
        onChange={setMembers}
      />
      <div className='flex min-w-0 flex-wrap gap-2'>
        <StepButton
          icon={Users}
          label='Gather these camps'
          busy={why(
            blocked ??
              (members.length < 2 ? 'A confederation joins two camps' : null),
            joining.isPending
          )}
          onClick={() => joining.mutate()}
        />
        <StepButton
          icon={Split}
          label='Break it apart'
          busy={gone ? 'It has already broken apart' : breaking.busy}
          onClick={breaking.run}
        />
      </div>
    </Held>
  )
}

function ConfederationForge({
  townId,
  isCamp,
  blocked,
}: {
  townId: number
  isCamp: boolean
  blocked: string | null
}) {
  const [name, setName] = useState('')
  const [leader, setLeader] = useState<number | null>(null)
  const [members, setMembers] = useState<number[]>(isCamp ? [townId] : [])
  const creating = useCycleAction(
    'confederation:create',
    (_: void) => ({ name: name.trim(), leader_id: leader, members }),
    'The camps are gathered'
  )
  const busy = why(
    blocked ??
      (name.trim() === ''
        ? 'Name the confederation first'
        : members.length < 2
          ? 'Choose at least two camps'
          : null),
    creating.isPending
  )
  return (
    <ForgeCard
      icon={Users}
      tone='gold'
      title='Gather camps into a confederation'
      note='Choose its leader and its camps.'
      columns={3}
      action={
        <Button
          size='sm'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => creating.mutate()}
        >
          <Users />
          Gather them
        </Button>
      }
    >
      <div className='flex min-w-0 flex-col gap-1.5'>
        <FieldLabel htmlFor={`league-name-${townId}`}>Called</FieldLabel>
        <Input
          id={`league-name-${townId}`}
          value={name}
          disabled={blocked !== null}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <NodePicker
        label='Leader'
        value={leader}
        onChange={setLeader}
        blocked={blocked}
        types={['mortal']}
      />
      <NodeListPicker
        label='Camps'
        value={members}
        types={['settlement']}
        blocked={blocked}
        onChange={setMembers}
      />
    </ForgeCard>
  )
}

export function NomadPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: CyclesView
  blocked: string | null
}) {
  const isTown = kind === 'settlement'
  return (
    <div data-surface='NomadPanel' className='flex min-w-0 flex-col gap-4'>
      {data.camp ? (
        <CampCard townId={nodeId} row={data.camp} blocked={blocked} />
      ) : (
        <Muted variant='caption'>
          {isTown ? 'This settlement stays where it stands.' : NOT_TOWN}
        </Muted>
      )}
      <CampForge townId={nodeId} isTown={isTown} blocked={blocked} />
      <Listed
        title='Confederations'
        items={data.confederations}
        empty='No confederation gathers this one.'
        noun={['confederation', 'confederations']}
        itemKey={(item) => item.id}
      >
        {(item) => <ConfederationCard row={item} blocked={blocked} />}
      </Listed>
      <ConfederationForge
        townId={nodeId}
        isCamp={data.camp !== null}
        blocked={blocked}
      />
      {data.camp && (
        <Chip
          icon={Footprints}
        >{`${data.camp.circuit.length} pastures on its circuit`}</Chip>
      )}
      {data.camp && (
        <Meter
          label='Grazing left'
          value={data.camp.grazing}
          max={SPAN}
          tone='success'
          icon={Leaf}
        />
      )}
    </div>
  )
}
