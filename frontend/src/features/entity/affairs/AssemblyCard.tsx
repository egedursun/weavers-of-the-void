import { useState } from 'react'
import { Lock, Plus, Trash2, Unlock, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Paged, StatBar } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  AddBar,
  ItemRow,
  MindCard,
  MindPicker,
  NodePicker,
} from '../mind/parts'
import { RefLink, Tag } from '../realm/parts'
import {
  type Affairs,
  type Resolution,
  type ResolutionKind,
  type ResolutionState,
  type ResolutionVote,
} from './api'
import {
  ASSEMBLY_ICON,
  RESOLUTION_KINDS,
  RESOLUTION_STATES,
  labelTable,
  spec,
} from './labels'

const WORKING = 'Working on it.'
type Ctx = { view: Affairs; blocked: string | null; hold: boolean }
type NodeRef = { id: number; kind: string; name: string }

function why(blocked: string | null, ...pending: boolean[]): string | null {
  return blocked ?? (pending.some(Boolean) ? WORKING : null)
}

function Ref({
  node,
  empty = 'none',
}: {
  node: NodeRef | null | undefined
  empty?: string
}) {
  if (!node) return <span>{empty}</span>
  return <RefLink node={node} />
}

function VoteRow({
  resolution,
  item,
  ctx,
}: {
  resolution: Resolution
  item: ResolutionVote
  ctx: Ctx
}) {
  const flip = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/vote:set', {
          body: {
            resolution_id: resolution.id,
            member_id: item.member.id,
            aye: !item.aye,
            weight: item.weight,
            hold: ctx.hold,
          },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/vote:remove', {
          body: { resolution_id: resolution.id, member_id: item.member.id },
        })
      ),
  })
  const busy = why(ctx.blocked, flip.isPending, strike.isPending)
  return (
    <ItemRow
      icon={ASSEMBLY_ICON}
      tone={item.aye ? 'success' : 'danger'}
      title={<Ref node={item.member} />}
      meta={`${item.aye ? 'For' : 'Against'}, weight ${item.weight}`}
      badges={item.locked ? <Badge variant='outline'>Held</Badge> : undefined}
      actions={
        <>
          <Button
            size='sm'
            variant='outline'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => flip.mutate()}
          >
            {item.aye ? 'Vote against' : 'Vote for'}
          </Button>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={`Strike the vote of ${item.member.name}`}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <X />
          </Button>
        </>
      }
    />
  )
}

function ResolutionRow({ row, ctx }: { row: Resolution; ctx: Ctx }) {
  const held = row.locked.length > 0
  const [state, setState] = useState<string>(row.state)
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resolution:edit', {
          body: {
            resolution_id: row.id,
            state: state as ResolutionState,
            hold: ctx.hold,
          },
        })
      ),
  })
  const hold = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resolution:hold', {
          body: { resolution_id: row.id, hold: !held },
        })
      ),
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resolution:delete', {
          body: { resolution_id: row.id },
        })
      ),
  })
  const busy = why(
    ctx.blocked,
    edit.isPending,
    hold.isPending,
    strike.isPending
  )
  const look = spec(RESOLUTION_KINDS, row.kind)
  const total = Math.max(1, row.votes_for + row.votes_against)
  return (
    <ItemRow
      icon={look.icon}
      tone={look.tone}
      title={
        <>
          {look.label}
          {row.target && (
            <>
              {': '}
              <Ref node={row.target} />
            </>
          )}
        </>
      }
      meta={
        <>
          {'Before '}
          <Ref node={row.assembly} empty='a dissolved assembly' />
          {`, since epoch ${row.proposed_epoch}${row.until_epoch !== null ? `, binding until epoch ${row.until_epoch}` : ''}`}
        </>
      }
      badges={
        <>
          <Tag spec={spec(RESOLUTION_STATES, row.state)} />
          {held && <Badge variant='outline'>Held</Badge>}
        </>
      }
      actions={
        <>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label={held ? 'Let the resolution run' : 'Hold the resolution'}
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => hold.mutate()}
          >
            {held ? <Unlock /> : <Lock />}
          </Button>
          <Button
            size='icon-sm'
            variant='ghost'
            aria-label='Strike the resolution'
            disabled={busy !== null}
            disabledReason={busy ?? undefined}
            onClick={() => strike.mutate()}
          >
            <Trash2 />
          </Button>
        </>
      }
      editLabel='the resolution'
      editor={
        <div className='flex min-w-0 flex-col gap-3'>
          <AdjustStats
            id={`resolution-${row.id}`}
            inline
            groups={[
              {
                title: 'Votes and term',
                fields: [
                  {
                    key: 'votes_for',
                    label: 'For',
                    value: row.votes_for,
                    min: 0,
                    max: 1_000_000,
                  },
                  {
                    key: 'votes_against',
                    label: 'Against',
                    value: row.votes_against,
                    min: 0,
                    max: 1_000_000,
                  },
                  {
                    key: 'until_epoch',
                    label: 'Binding until epoch',
                    value: row.until_epoch ?? 0,
                    min: 0,
                    max: 100_000,
                  },
                ],
              },
            ]}
            run={({ key, value }) =>
              unwrap(
                api.POST('/api/actions/resolution:edit', {
                  body: { resolution_id: row.id, [key]: value, hold: ctx.hold },
                })
              )
            }
          />
          <div className='grid min-w-0 grid-cols-1 items-end gap-3 sm:grid-cols-2'>
            <MindPicker
              label='State'
              value={state}
              table={labelTable(RESOLUTION_STATES)}
              blocked={busy}
              onPick={setState}
            />
            <Button
              size='sm'
              variant='outline'
              disabled={busy !== null || state === row.state}
              disabledReason={
                busy ??
                (state === row.state ? 'Choose another state.' : undefined)
              }
              onClick={() => edit.mutate()}
            >
              Set the state
            </Button>
          </div>
          {row.votes.length > 0 && (
            <div className='flex min-w-0 flex-col gap-2'>
              <Label variant='overline'>Votes</Label>
              <Paged items={row.votes} initial={4} noun={['vote', 'votes']}>
                {(item) => (
                  <VoteRow
                    key={item.member.id}
                    resolution={row}
                    item={item}
                    ctx={ctx}
                  />
                )}
              </Paged>
            </div>
          )}
        </div>
      }
    >
      <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
        <StatBar label='For' value={row.votes_for} max={total} tone='success' />
        <StatBar
          label='Against'
          value={row.votes_against}
          max={total}
          tone='destructive'
        />
      </div>
    </ItemRow>
  )
}

function ProposeResolution({ ctx }: { ctx: Ctx }) {
  const [kind, setKind] = useState('')
  const [target, setTarget] = useState<number | null>(null)
  const propose = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/resolution:propose', {
          body: {
            assembly_id: ctx.view.node_id,
            kind: kind as ResolutionKind,
            target_id: target,
          },
        })
      ),
    success: () => {
      setKind('')
      setTarget(null)
      return 'Brought to the vote'
    },
  })
  const busy = why(ctx.blocked, propose.isPending)
  const needs = kind === 'embargo' || kind === 'sanction'
  const missing = !kind
    ? 'Choose a resolution.'
    : needs && target === null
      ? 'Choose its target.'
      : null
  return (
    <AddBar
      title='Bring a resolution to the vote'
      action={
        <Button
          size='sm'
          disabled={busy !== null || missing !== null}
          disabledReason={busy ?? missing ?? undefined}
          onClick={() => propose.mutate()}
        >
          <Plus />
          Propose
        </Button>
      }
    >
      <MindPicker
        label='Resolution'
        value={kind}
        table={labelTable(RESOLUTION_KINDS)}
        blocked={busy}
        onPick={setKind}
      />
      <NodePicker
        label={kind === 'sanction' ? 'The god' : 'Target'}
        types={
          kind === 'sanction' ? ['son'] : ['polity', 'settlement', 'people']
        }
        value={target}
        onChange={setTarget}
        blocked={busy}
      />
    </AddBar>
  )
}

export function AssemblyCard({ ctx }: { ctx: Ctx }) {
  return (
    <MindCard
      title='Interworld assembly'
      icon={ASSEMBLY_ICON}
      hint='An assembly of realms across worlds votes resolutions by the weight of its members, clients voting with their powers. A binding resolution makes every member embargo a realm, cut off a god’s world, ban rites of the void or guard the routes between them; a member that breaks it loses the others’ trust.'
    >
      {ctx.view.resolutions.length === 0 ? (
        <Muted variant='caption'>
          {ctx.view.is_assembly
            ? 'No resolution stands before this assembly.'
            : 'No resolution touches it.'}
        </Muted>
      ) : (
        <Paged
          items={ctx.view.resolutions}
          initial={3}
          noun={['resolution', 'resolutions']}
        >
          {(row) => <ResolutionRow key={row.id} row={row} ctx={ctx} />}
        </Paged>
      )}
      {ctx.view.is_assembly && <ProposeResolution ctx={ctx} />}
    </MindCard>
  )
}
