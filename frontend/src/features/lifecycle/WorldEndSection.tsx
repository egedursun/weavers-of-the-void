import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import type { components } from '@/api/generated/schema'
import { Button } from '@/components/ui/button'
import { EmptyState, KpiTile, LoadingBlock, Section } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  Facts,
  type Field,
  ForgeCard,
  RecordEditor,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { Ref } from '@/features/gatherings/parts'
import { humanize } from '@/features/pantheon/labels'
import { Bars } from '@/features/sacred/parts'
import { ChoiceField } from '@/features/wars/military/parts'
import { useEndsAction, useNodeWorldEnd } from './api'
import {
  WORLD_END_CAUSES,
  WORLD_END_ICON,
  WORLD_ENDS,
  WORLD_KINDS,
} from './labels'

type WorldType = components['schemas']['WorldType']

const FIELDS: readonly Field[] = [
  {
    key: 'state',
    label: 'How it ended',
    kind: 'pick',
    table: table(WORLD_ENDS),
  },
  {
    key: 'cause',
    label: 'What ended it',
    kind: 'pick',
    table: table(WORLD_END_CAUSES),
  },
]

export function WorldEndSection({
  nodeId,
  readOnlyReason = null,
}: {
  nodeId: number
  readOnlyReason?: string | null
}) {
  const query = useNodeWorldEnd(nodeId)
  const data = query.data
  const worldId = data?.world?.id ?? null
  const absent = data?.absent_reason ?? null
  const blocked = readOnlyReason ?? absent
  const [state, setState] = useState<keyof typeof WORLD_ENDS>('frozen_dead')
  const [cause, setCause] =
    useState<keyof typeof WORLD_END_CAUSES>('divine_wrath')
  const [kind, setKind] = useState<string>('ordinary')
  const declaring = useEndsAction(
    'world_end:declare',
    (_: void) => ({
      world_id: worldId ?? 0,
      state,
      cause,
      new_type: state === 'transfigured' ? (kind as WorldType) : null,
    }),
    'The world comes to its end'
  )
  const editing = useEndsAction(
    'world_end:edit',
    (vars: {
      values: Record<string, number | string | boolean | null>
      release: string[]
    }) => ({ world_id: worldId ?? 0, ...vars }),
    'The record of its end is set'
  )
  const removing = useEndsAction(
    'world_end:remove',
    (_: void) => ({ world_id: worldId ?? 0 }),
    'The record of its end is struck out'
  )
  const ended = data?.state ?? null
  const declareBlocked =
    blocked ??
    (state === 'transfigured' && kind === data?.world_type
      ? 'A world is transfigured into another kind; choose a different kind'
      : null)
  return (
    <Section
      id='section-world-end'
      title='End of the world: shattered, swallowed, frozen, sunk, forgotten or transfigured'
      description='Whether the world this thing stands on has come to its end, how, and what that ended: lives, roads, the homeward ties of peoples abroad and the anchors of gods. Things on no world have no world to end, and the controls say so.'
      icon={WORLD_END_ICON}
      tone='danger'
    >
      <div
        data-surface='WorldEndSection'
        className='flex min-w-0 flex-col gap-6'
      >
        {query.isPending ? (
          <LoadingBlock label='Reading the fate of its world' />
        ) : query.isError ? (
          <EmptyState
            icon={WORLD_END_ICON}
            size='inline'
            title='This could not be read'
            description={query.error.message}
          />
        ) : (
          <>
            <Facts
              items={[
                [
                  'World',
                  <Ref key='world' node={query.data.world} empty='no world' />,
                ],
                [
                  'Kind of world',
                  query.data.world_type
                    ? humanize(query.data.world_type)
                    : 'none',
                ],
                [
                  'Ended',
                  ended && query.data.epoch !== null
                    ? `epoch ${query.data.epoch}`
                    : 'it lives on',
                ],
              ]}
            />
            {ended ? (
              <div className='grid min-w-0 grid-cols-2 gap-3 lg:grid-cols-4'>
                <KpiTile
                  label='How it ended'
                  value={WORLD_ENDS[ended].label}
                  icon={WORLD_ENDS[ended].icon}
                  tone={WORLD_ENDS[ended].tone}
                  hint={
                    query.data.cause
                      ? WORLD_END_CAUSES[query.data.cause].label
                      : undefined
                  }
                />
                <KpiTile
                  label='Lives ended'
                  value={String(query.data.lives_ended)}
                  icon={WORLD_END_ICON}
                  tone='danger'
                />
                <KpiTile
                  label='Homeward ties cut abroad'
                  value={String(query.data.homeless)}
                  icon={WORLD_END_ICON}
                  tone='warning'
                />
                <KpiTile
                  label='Anchors lost and roads closed'
                  value={`${query.data.anchors_lost} / ${query.data.routes_closed}`}
                  icon={WORLD_END_ICON}
                  tone='muted'
                  hint={
                    query.data.former_type
                      ? `once ${humanize(query.data.former_type)}${query.data.new_type ? `, now ${humanize(query.data.new_type)}` : ''}`
                      : undefined
                  }
                />
              </div>
            ) : (
              <EmptyState
                icon={WORLD_END_ICON}
                size='inline'
                title={worldId ? 'This world lives on' : 'No world to end'}
                description={absent ?? 'Nothing has ended it.'}
              />
            )}
            <Bars
              chart='chart-world-end'
              title='What the end of this world ended'
              legend={[{ text: 'Ended', variant: 'warning' }]}
              rows={
                ended
                  ? [
                      ['lives', 'Lives ended', query.data.lives_ended],
                      [
                        'homeless',
                        'Homeward ties cut abroad',
                        query.data.homeless,
                      ],
                      [
                        'anchors',
                        'Anchors of gods lost',
                        query.data.anchors_lost,
                      ],
                      ['routes', 'Roads closed', query.data.routes_closed],
                    ].map(([key, label, value]) => ({
                      key: String(key),
                      caption: `${label}: ${value}`,
                      segments: [
                        { value: Number(value), fill: 'fill-destructive' },
                      ],
                    }))
                  : []
              }
              noun={['loss', 'losses']}
              empty='This world has not come to an end, so nothing was lost.'
            />
            <ForgeCard
              icon={WORLD_END_ICON}
              tone='danger'
              title='Bring this world to its end'
              note='Lives on it end unless it is forgotten or transfigured; what is lost stays lost.'
              columns={3}
              action={
                <Button
                  size='sm'
                  variant='destructive'
                  disabled={why(declareBlocked, declaring.isPending) !== null}
                  disabledReason={
                    why(declareBlocked, declaring.isPending) ?? undefined
                  }
                  onClick={() => declaring.mutate()}
                >
                  <WORLD_END_ICON />
                  End it ({query.data.end_cost} essence)
                </Button>
              }
            >
              <ChoiceField
                label='How it ends'
                value={state}
                table={WORLD_ENDS}
                blocked={blocked}
                onPick={(next) => setState(next as keyof typeof WORLD_ENDS)}
              />
              <ChoiceField
                label='What ends it'
                value={cause}
                table={WORLD_END_CAUSES}
                blocked={blocked}
                onPick={(next) =>
                  setCause(next as keyof typeof WORLD_END_CAUSES)
                }
              />
              <ChoiceField
                label='Kind it becomes if transfigured'
                value={kind}
                table={WORLD_KINDS}
                blocked={
                  state === 'transfigured'
                    ? blocked
                    : 'Only a transfigured world becomes another kind'
                }
                onPick={setKind}
              />
            </ForgeCard>
            <RecordEditor
              title='Set the record of its end'
              note='This changes only the record; what the end did to the world stays done.'
              fields={FIELDS}
              locked={query.data.locked}
              busy={why(
                blocked ?? (ended ? null : 'This world has not come to an end'),
                editing.isPending
              )}
              onSave={(values) => editing.mutate({ values, release: [] })}
              onRelease={(keys) =>
                editing.mutate({ values: {}, release: keys })
              }
            />
            <StepButton
              icon={Trash2}
              label='Strike out the record of its end'
              busy={why(
                blocked ?? (ended ? null : 'This world has not come to an end'),
                removing.isPending
              )}
              onClick={() => removing.mutate()}
            />
          </>
        )}
      </div>
    </Section>
  )
}
