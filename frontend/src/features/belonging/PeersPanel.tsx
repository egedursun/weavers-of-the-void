import { useState } from 'react'
import { Baby, Plus, UserPlus, Users } from 'lucide-react'
import { plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { table } from '@/features/arcana/labels'
import { Held, Listed } from '@/features/collective/parts'
import { Facts, ForgeCard, Meter } from '@/features/cosmography/parts'
import { YES_NO } from '@/features/cycles/labels'
import { why } from '@/features/dominion/model'
import { NodePicker } from '@/features/dominion/parts'
import { MindPicker } from '@/features/entity/mind/parts'
import { CLASS_SPEC } from '@/features/entity/society/labels'
import { Ref } from '@/features/gatherings/parts'
import { Bars } from '@/features/sacred/parts'
import { type BelongingNodeView, useBelongingAction } from './api'
import { PLAYS } from './labels'
import {
  MANY,
  MORTAL_TYPES,
  SETTLEMENT_TYPES,
  SPAN,
  useBelongingRow,
} from './model'

type View = BelongingNodeView
type Group = View['peer_groups'][number]
type Member = Group['members'][number]

function MemberCard({
  row,
  groupId,
  blocked,
}: {
  row: Member
  groupId: number
  blocked: string | null
}) {
  const action = useBelongingRow(
    'peer_member:edit',
    'peer_member:delete',
    { group_id: groupId, mortal_id: row.mortal.id },
    blocked
  )
  return (
    <Held
      icon={Baby}
      tone={row.deprived_epochs > 0 ? 'warning' : 'success'}
      title={row.mortal.name}
      caption={`Joined in epoch ${row.joined_epoch} · ${plural(row.deprived_epochs, 'epoch', 'epochs')} without play`}
      removeLabel='Take the child out'
      editTitle='Set the child'
      note='A child kept from play loses cheer, and carries stress into adulthood for every epoch it went without.'
      fields={[
        {
          key: 'deprived_epochs',
          label: 'Epochs without play',
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
      <Facts
        items={[
          ['Child', <Ref key='child' node={row.mortal} empty='no one' />],
        ]}
      />
    </Held>
  )
}

function GroupCard({ row, blocked }: { row: Group; blocked: string | null }) {
  const action = useBelongingRow(
    'peer_group:edit',
    'peer_group:delete',
    { record_id: row.id },
    blocked
  )
  const play = PLAYS[row.play]
  const rank = CLASS_SPEC[row.social_class]
  return (
    <Held
      icon={play.icon}
      tone={row.deprived ? 'warning' : play.tone}
      title={`${rank.label} children of ${row.settlement.name}`}
      caption={`${play.label} · ${plural(row.children, 'child', 'children')} · cohesion ${row.cohesion} · formed in epoch ${row.formed_epoch}${row.dissolved_epoch !== null ? ` · grown up by epoch ${row.dissolved_epoch}` : ''}`}
      removeLabel='Break up the group'
      editTitle='Set the group'
      note='Children of one town and rank play together. Their play shapes their temper and teaches a skill, they become friends or rivals, and those who grow up together stay companions; a ruler favours childhood companions for the council. Hunger or war in the land leaves them no time to play.'
      fields={[
        {
          key: 'settlement_entity_id',
          label: 'Town',
          kind: 'node',
          types: SETTLEMENT_TYPES,
        },
        {
          key: 'social_class',
          label: 'Rank',
          kind: 'pick',
          table: table(CLASS_SPEC),
        },
        { key: 'play', label: 'Play', kind: 'pick', table: table(PLAYS) },
        {
          key: 'children',
          label: 'Children',
          kind: 'number',
          min: 0,
          max: MANY,
        },
        {
          key: 'cohesion',
          label: 'Cohesion',
          kind: 'number',
          min: 0,
          max: SPAN,
        },
        {
          key: 'deprived',
          label: 'Kept from play',
          kind: 'pick',
          table: YES_NO,
        },
        {
          key: 'dissolved_epoch',
          label: 'Grown up by epoch',
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
        row.deprived ? (
          <Badge size='sm' variant='warning'>
            No time to play
          </Badge>
        ) : null
      }
    >
      <Meter
        label={`Cohesion (${row.cohesion} of ${SPAN})`}
        value={row.cohesion}
        tone={row.deprived ? 'warning' : 'success'}
        icon={Users}
      />
      <Listed
        title='Named children'
        items={row.members}
        empty='No named child plays here.'
        noun={['child', 'children']}
        itemKey={(item) => item.mortal.id}
      >
        {(item) => <MemberCard row={item} groupId={row.id} blocked={blocked} />}
      </Listed>
    </Held>
  )
}

export function PeersPanel({
  nodeId,
  kind,
  data,
  blocked,
}: {
  nodeId: number
  kind: string | null
  data: View
  blocked: string | null
}) {
  const town = kind === 'settlement'
  const [rank, setRank] = useState('farmer')
  const [play, setPlay] = useState('games')
  const [group, setGroup] = useState(
    data.peer_groups[0] ? String(data.peer_groups[0].id) : ''
  )
  const [child, setChild] = useState<number | null>(
    kind === 'mortal' ? nodeId : null
  )
  const gathering = useBelongingAction(
    'peer_group:create',
    (_: void) => ({
      settlement_entity_id: nodeId,
      social_class: rank as Group['social_class'],
      play: play as Group['play'],
    }),
    'The children gather to play'
  )
  const joining = useBelongingAction(
    'peer_member:set',
    (_: void) => ({ group_id: Number(group), mortal_id: child ?? 0 }),
    'The child joins the group'
  )
  const gatherBusy = why(
    blocked ?? (!town ? 'Only a town gathers its children into groups' : null),
    gathering.isPending
  )
  const joinBusy = why(
    blocked ??
      (!group
        ? 'No peer group touches this yet; gather one in its town first'
        : child === null
          ? 'Choose the child'
          : null),
    joining.isPending
  )
  return (
    <div data-surface='PeersPanel' className='flex min-w-0 flex-col gap-4'>
      <Bars
        chart='chart-peers'
        title='Peer groups and their cohesion'
        legend={[
          { text: 'Playing', variant: 'success' },
          { text: 'Kept from play', variant: 'warning' },
        ]}
        rows={data.peer_groups.map((row) => ({
          key: String(row.id),
          caption: `${CLASS_SPEC[row.social_class].label} of ${row.settlement.name}: ${plural(row.members.length, 'named child', 'named children')}, cohesion ${row.cohesion}`,
          segments: [
            {
              value: row.cohesion,
              fill: row.deprived ? 'fill-warning' : 'fill-success',
            },
          ],
        }))}
        max={SPAN}
        noun={['group', 'groups']}
        empty='No peer group touches this.'
      />
      <Listed
        title='Peer groups'
        items={data.peer_groups}
        empty='No peer group touches this.'
        noun={['group', 'groups']}
        itemKey={(item) => item.id}
      >
        {(item) => <GroupCard row={item} blocked={blocked} />}
      </Listed>
      <ForgeCard
        icon={Baby}
        tone='success'
        title='Gather the children'
        note='A peer group for the children of one rank of this town.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={gatherBusy !== null}
            disabledReason={gatherBusy ?? undefined}
            onClick={() => gathering.mutate()}
          >
            <Plus />
            Gather them
          </Button>
        }
      >
        <MindPicker
          label='Rank'
          value={rank}
          table={table(CLASS_SPEC)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setRank}
        />
        <MindPicker
          label='Play'
          value={play}
          table={table(PLAYS)}
          placeholder='Choose'
          blocked={blocked}
          onPick={setPlay}
        />
      </ForgeCard>
      <ForgeCard
        icon={UserPlus}
        tone='info'
        title='Bring a child into a group'
        note='A named child joins a peer group and plays with it.'
        columns={2}
        action={
          <Button
            size='sm'
            disabled={joinBusy !== null}
            disabledReason={joinBusy ?? undefined}
            onClick={() => joining.mutate()}
          >
            <Plus />
            Bring them in
          </Button>
        }
      >
        <MindPicker
          label='Peer group'
          value={group}
          table={Object.fromEntries(
            data.peer_groups.map((row) => [
              String(row.id),
              `${CLASS_SPEC[row.social_class].label} of ${row.settlement.name}`,
            ])
          )}
          placeholder='Choose'
          blocked={blocked}
          onPick={setGroup}
        />
        <NodePicker
          label='Child'
          value={child}
          onChange={setChild}
          blocked={blocked}
          types={MORTAL_TYPES}
        />
      </ForgeCard>
    </div>
  )
}
