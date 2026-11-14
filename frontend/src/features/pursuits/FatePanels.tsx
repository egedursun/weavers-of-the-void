import { useState } from 'react'
import { BookMarked, Coins, Crosshair, Flame, Star, Target } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { KpiTile } from '@/components/domain'
import { Muted } from '@/components/typography'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { FUNCTIONS } from '@/features/entity/body/labels'
import { NumberField } from '@/features/entity/realm/parts'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { Tag } from '@/features/wars/military/parts'
import { type PursuitsNodeView, usePursuitsAction } from './api'
import {
  CONTRACT_STATUS,
  HUNT_ICON,
  INFLUENCES,
  REMADE_ICON,
  SIGN_ICON,
} from './labels'
import {
  BEAST_TYPES,
  MANY,
  MORTAL_TYPES,
  REALM_TYPES,
  SKY_TYPES,
  SPAN,
  TOWN_TYPES,
  usePursuitsRow,
  usePursuitsStep,
  withNone,
} from './model'

type Contract = PursuitsNodeView['contracts'][number]
type Sign = NonNullable<PursuitsNodeView['sign']>
type Remade = NonNullable<PursuitsNodeView['remade']>

const FORTUNE_LIMIT = 20
const SEASONS = 1000
const FUNCTION_TABLE = withNone(table(FUNCTIONS), 'Nothing')
const CLOSED = 'That contract is closed'

function functionLabel(value: string | null): string {
  return value === null
    ? 'nothing'
    : (FUNCTIONS[value]?.label.toLowerCase() ?? value)
}

function ContractCard({
  row,
  blocked,
}: {
  row: Contract
  blocked: string | null
}) {
  const action = usePursuitsRow(
    'monster_contract:edit',
    'monster_contract:delete',
    { contract_id: row.id },
    blocked
  )
  const status = CONTRACT_STATUS[row.status]
  const [hunter, setHunter] = useState<number | null>(null)
  const open = row.status === 'posted' || row.status === 'taken'
  const assigning = usePursuitsStep(
    'monster_contract:assign',
    { contract_id: row.id, hunter_id: hunter ?? 0 },
    blocked ?? (!open ? CLOSED : hunter === null ? 'Choose a hunter' : null),
    'The hunter takes the contract'
  )
  return (
    <Held
      icon={status.icon}
      tone={status.tone}
      title={`${row.bounty} on ${row.beast.name}`}
      caption={`Posted by ${row.community.name} in epoch ${row.posted_epoch}${row.closed_epoch !== null ? ` · closed in epoch ${row.closed_epoch}` : ''}`}
      removeLabel='Tear up the contract'
      editTitle='Set the contract'
      note='A town raided by a beast posts a bounty on it. A hunter of the beast’s world takes it, studies the quarry each epoch and hunts it: study and strength against the beast’s danger. A slain beast earns the hunter the bounty and renown; a failed hunt wounds them, and one too badly hurt gives up.'
      fields={[
        {
          key: 'community_entity_id',
          label: 'Town that pays',
          kind: 'node',
          types: TOWN_TYPES,
        },
        {
          key: 'beast_entity_id',
          label: 'Quarry',
          kind: 'node',
          types: BEAST_TYPES,
        },
        { key: 'bounty', label: 'Bounty', kind: 'number', min: 0, max: MANY },
        {
          key: 'hunter_entity_id',
          label: 'Hunter',
          kind: 'node',
          types: MORTAL_TYPES,
        },
        {
          key: 'status',
          label: 'Standing',
          kind: 'pick',
          table: table(CONTRACT_STATUS),
        },
        {
          key: 'study',
          label: 'Study of the quarry',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={status} />}
    >
      <Meter
        label={`Study of the quarry (${row.study} of ${SPAN})`}
        value={row.study}
        tone='info'
        icon={BookMarked}
      />
      <div className='@container/tiles min-w-0'>
        <div className='grid min-w-0 grid-cols-2 gap-2'>
          <KpiTile label='Bounty' value={row.bounty} icon={Coins} tone='gold' />
          <KpiTile
            label='Standing'
            value={status.label}
            icon={status.icon}
            tone={status.tone}
          />
        </div>
      </div>
      <Facts
        items={[
          [
            'Town that pays',
            <Ref key='town' node={row.community} empty='none' />,
          ],
          ['Quarry', <Ref key='beast' node={row.beast} empty='gone' />],
          ['Hunter', <Ref key='hunter' node={row.hunter} empty='no one yet' />],
        ]}
      />
      <div className='grid min-w-0 grid-cols-1 items-end gap-2 sm:grid-cols-2'>
        <NodePicker
          label='Set a hunter on it'
          value={hunter}
          onChange={setHunter}
          blocked={action.busy}
          types={MORTAL_TYPES}
        />
        <StepButton
          icon={Crosshair}
          label='Send them'
          busy={assigning.busy}
          onClick={assigning.run}
        />
      </div>
    </Held>
  )
}

export function ContractPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  const [town, setTown] = useState<number | null>(
    kind === 'settlement' ? nodeId : null
  )
  const [beast, setBeast] = useState<number | null>(
    kind === 'beast' ? nodeId : null
  )
  const [bounty, setBounty] = useState('30')
  const posting = usePursuitsAction(
    'monster_contract:create',
    (_: void) => ({
      town_id: town ?? 0,
      beast_id: beast ?? 0,
      bounty: Number(bounty || '0'),
    }),
    'A bounty is posted'
  )
  const busy = why(
    blocked ??
      (town === null
        ? 'Choose the town that pays'
        : beast === null
          ? 'Choose the beast'
          : null),
    posting.isPending
  )
  return (
    <div data-surface='ContractPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-contracts'
        title='Study of each hunt'
        legend={[
          { text: 'Study of the quarry', variant: 'secondary' },
          { text: 'Slain', variant: 'success' },
          { text: 'Failed', variant: 'destructive' },
        ]}
        rows={data.contracts.map((row) => ({
          key: row.id,
          caption: `${row.beast.name}: bounty ${row.bounty}, study ${row.study}, ${CONTRACT_STATUS[row.status].label.toLowerCase()}`,
          segments: [
            {
              value: row.study,
              fill:
                row.status === 'slain'
                  ? 'fill-success'
                  : row.status === 'failed'
                    ? 'fill-destructive'
                    : 'fill-info',
            },
          ],
        }))}
        max={SPAN}
        noun={['contract', 'contracts']}
        empty='No contract touches this.'
      />
      <Listed
        title='Contracts on beasts'
        items={data.contracts}
        empty='No contract touches this.'
        noun={['contract', 'contracts']}
        itemKey={(item) => item.id}
      >
        {(item) => <ContractCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Target}
        tone='warning'
        title='Post a bounty'
        note='The town offers coin for the beast; hunters of its world may take the contract.'
        columns={3}
        action={
          <Button
            size='sm'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => posting.mutate()}
          >
            <HUNT_ICON />
            Post it
          </Button>
        }
      >
        <NodePicker
          label='Town that pays'
          value={town}
          onChange={setTown}
          blocked={blocked}
          types={TOWN_TYPES}
        />
        <NodePicker
          label='Beast'
          value={beast}
          onChange={setBeast}
          blocked={blocked}
          types={BEAST_TYPES}
        />
        <NumberField
          label='Bounty'
          value={bounty}
          min={0}
          max={MANY}
          blocked={blocked}
          onChange={setBounty}
        />
      </ForgeCard>
    </div>
  )
}

function SignCard({ row, blocked }: { row: Sign; blocked: string | null }) {
  const action = usePursuitsRow(
    'birth_sign:edit',
    'birth_sign:delete',
    { mortal_id: row.mortal.id },
    blocked
  )
  const influence = INFLUENCES[row.influence]
  return (
    <Held
      icon={SIGN_ICON}
      tone={row.dreaded ? 'danger' : influence.tone}
      title={`${row.dreaded ? 'A dreaded sign' : 'A sign'} over ${row.mortal.name}`}
      caption={`Born in epoch ${row.born_epoch} · season ${row.season}${row.exposed ? ' · sent away' : ''}`}
      removeLabel='Forget the sign'
      editTitle='Set the birth sign'
      note='A mortal is born under the ruling body of the sky. Where that body’s influence is great, the sign truly shapes the born, for good or, under a dreaded sign, for ill; elsewhere it is only believed. A people that reads the stars may send away a child of a dreaded sign.'
      fields={[
        {
          key: 'season',
          label: 'Season',
          kind: 'number',
          min: 0,
          max: SEASONS,
        },
        {
          key: 'ruling_celestial_entity_id',
          label: 'Ruling body of the sky',
          kind: 'node',
          types: SKY_TYPES,
        },
        { key: 'dreaded', label: 'Dreaded', kind: 'pick', table: YES_NO },
        {
          key: 'influence',
          label: 'Its hold',
          kind: 'pick',
          table: table(INFLUENCES),
        },
        {
          key: 'fortune',
          label: 'Fortune',
          kind: 'number',
          min: -FORTUNE_LIMIT,
          max: FORTUNE_LIMIT,
        },
        { key: 'exposed', label: 'Sent away', kind: 'pick', table: YES_NO },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
      extra={<Tag item={influence} />}
    >
      <Meter
        label={`Fortune (${row.fortune}, from ${-FORTUNE_LIMIT} to ${FORTUNE_LIMIT})`}
        value={row.fortune + FORTUNE_LIMIT}
        max={FORTUNE_LIMIT * 2}
        tone={row.fortune >= 0 ? 'success' : 'destructive'}
        icon={Star}
      />
      <Facts
        items={[
          [
            'Ruling body of the sky',
            <Ref key='sky' node={row.ruling_celestial} empty='none' />,
          ],
          ['Dreaded', row.dreaded ? 'yes' : 'no'],
          [
            'Sent away',
            row.exposed ? 'yes, by those who read the stars' : 'no',
          ],
        ]}
      />
    </Held>
  )
}

export function BirthSignPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  const reading = usePursuitsStep(
    'birth_sign:create',
    { mortal_id: nodeId },
    blocked ??
      (kind === 'mortal' ? null : 'Only a mortal is born under a sign'),
    'The sign is read'
  )
  return (
    <div data-surface='BirthSignPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-birth-signs'
        title='Fortune of the sign'
        legend={[
          { text: 'Kindly', variant: 'success' },
          { text: 'Dreaded', variant: 'destructive' },
        ]}
        rows={
          data.sign
            ? [
                {
                  key: data.sign.mortal.id,
                  caption: `${data.sign.mortal.name}: fortune ${data.sign.fortune}, ${INFLUENCES[data.sign.influence].label.toLowerCase()}`,
                  segments: [
                    {
                      value: Math.abs(data.sign.fortune),
                      fill: data.sign.dreaded
                        ? 'fill-destructive'
                        : 'fill-success',
                    },
                  ],
                },
              ]
            : []
        }
        max={FORTUNE_LIMIT}
        noun={['sign', 'signs']}
        empty='No sign is read for this.'
      />
      {data.sign ? (
        <SignCard row={data.sign} blocked={blocked} />
      ) : (
        <Muted variant='caption'>No sign is read for this.</Muted>
      )}
      <ForgeCard
        icon={SIGN_ICON}
        tone='gold'
        title='Read the sign anew'
        note='The sign of the mortal’s birth is read again from the sky as it stands now.'
        columns={2}
        action={
          <StepButton
            icon={Star}
            label='Read it'
            busy={reading.busy}
            onClick={reading.run}
            variant='default'
          />
        }
      >
        <Muted variant='caption'>Reads the sign of this mortal.</Muted>
      </ForgeCard>
    </div>
  )
}

function RemadeCard({ row, blocked }: { row: Remade; blocked: string | null }) {
  const action = usePursuitsRow(
    'remade:edit',
    'remade:delete',
    { mortal_id: row.mortal.id },
    blocked
  )
  return (
    <Held
      icon={REMADE_ICON}
      tone={row.grievance >= SPAN / 2 ? 'danger' : 'warning'}
      title={`${row.mortal.name}, remade in body`}
      caption={`Remade in epoch ${row.epoch}: took ${functionLabel(row.lost_function)}, forced ${functionLabel(row.forced_function)}`}
      removeLabel='Undo the remaking'
      editTitle='Set the remaking'
      note='A cruel court of a people deep in magic may remake the condemned in body instead of another punishment: a part is taken and a labour forced. The remade work for their town, gather grievance each epoch, and where enough of them gather in one town with grievance high they rise.'
      fields={[
        {
          key: 'lost_function',
          label: 'Taken from the body',
          kind: 'pick',
          table: FUNCTION_TABLE,
        },
        {
          key: 'forced_function',
          label: 'Forced on the body',
          kind: 'pick',
          table: FUNCTION_TABLE,
        },
        {
          key: 'sentenced_by_entity_id',
          label: 'Sentenced by',
          kind: 'node',
          types: REALM_TYPES,
        },
        {
          key: 'grievance',
          label: 'Grievance',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'bound_to_entity_id',
          label: 'Labours for',
          kind: 'node',
          types: TOWN_TYPES,
        },
      ]}
      locked={row.locked}
      blocked={action.busy}
      onEdit={action.onEdit}
      onRemove={action.onRemove}
    >
      <Meter
        label={`Grievance (${row.grievance} of ${SPAN})`}
        value={row.grievance}
        tone='destructive'
        icon={Flame}
      />
      <Facts
        items={[
          [
            'Sentenced by',
            <Ref key='realm' node={row.sentenced_by} empty='no realm' />,
          ],
          [
            'Labours for',
            <Ref key='town' node={row.bound_to} empty='no town' />,
          ],
          [
            'Sentenced in a court case',
            row.case_id !== null ? 'yes' : 'no, by a god',
          ],
        ]}
      />
    </Held>
  )
}

export function RemadePanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: PursuitsNodeView
  blocked: string | null
}) {
  const remaking = usePursuitsStep(
    'remade:create',
    { mortal_id: nodeId },
    blocked ??
      (kind !== 'mortal'
        ? 'Only a mortal can be remade'
        : data.remade
          ? 'This mortal is already remade'
          : null),
    'The mortal is remade'
  )
  return (
    <div data-surface='RemadePanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-remade'
        title='Grievance of the remade'
        legend={[{ text: 'Grievance', variant: 'destructive' }]}
        rows={
          data.remade
            ? [
                {
                  key: data.remade.mortal.id,
                  caption: `${data.remade.mortal.name}: grievance ${data.remade.grievance}`,
                  segments: [
                    { value: data.remade.grievance, fill: 'fill-destructive' },
                  ],
                },
              ]
            : []
        }
        max={SPAN}
        noun={['mortal', 'mortals']}
        empty='This mortal was never remade.'
      />
      {data.remade ? (
        <RemadeCard row={data.remade} blocked={blocked} />
      ) : (
        <Muted variant='caption'>This was never remade.</Muted>
      )}
      <ForgeCard
        icon={REMADE_ICON}
        tone='danger'
        title='Remake in body'
        note='The mortal is remade as a court of their realm would remake the condemned.'
        columns={2}
        action={
          <StepButton
            icon={REMADE_ICON}
            label='Remake'
            busy={remaking.busy}
            onClick={remaking.run}
            variant='default'
          />
        }
      >
        <Muted variant='caption'>Remakes this mortal.</Muted>
      </ForgeCard>
    </div>
  )
}
