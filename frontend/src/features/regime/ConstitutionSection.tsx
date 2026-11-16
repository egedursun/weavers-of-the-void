import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, GitBranch, GitMerge, ScrollText, Trash2 } from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { EmptyState, KpiTile, LoadingBlock } from '@/components/domain'
import { table } from '@/features/arcana/labels'
import {
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { TENETS } from '@/features/entity/lore/model'
import { Ref, ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField } from '@/features/wars/military/parts'
import { SELECTORATES } from './labels'

type Edit = { values: EditValues; release: string[] }
type Tenet = components['schemas']['IdeologyTenet']

const HOLD =
  'Values you set are held against the engine until you release them.'
const NOT_REALM = 'Only a realm is governed by a constitution'
const CREEDS = ['ideology'] as const
const PLACES = ['settlement', 'people'] as const
const KEEP = 'keep'
const KEEP_TENET = {
  [KEEP]: { label: 'None', icon: ScrollText, tone: 'muted' as const },
}
const FIELDS: readonly Field[] = [
  {
    key: 'selectorate',
    label: 'Who chooses the ruler',
    kind: 'pick',
    table: table(SELECTORATES),
  },
  {
    key: 'offices',
    label: 'Offices it sets up',
    kind: 'number',
    min: 0,
    max: 50,
  },
  {
    key: 'rights',
    label: 'Breadth of rights',
    kind: 'number',
    min: 0,
    max: 100,
  },
  {
    key: 'ideology_entity_id',
    label: 'Creed it was written for',
    kind: 'node',
    types: ['ideology'],
  },
]

function useConstitution(nodeId: number) {
  return useQuery({
    queryKey: [...queryKeys.world.all, 'constitution-of', nodeId] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/constitutions/of/{node_id}', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
}

function CreedChanges({ blocked }: { blocked: string | null }) {
  const [creed, setCreed] = useState<number | null>(null)
  const [place, setPlace] = useState<number | null>(null)
  const [dropped, setDropped] = useState<string>(KEEP)
  const [added, setAdded] = useState<string>(KEEP)
  const [other, setOther] = useState<number | null>(null)
  const splitting = useMadeAction(
    'ideology:split',
    (_: void) => ({
      ideology_id: creed ?? 0,
      community_id: place ?? 0,
      dropped: dropped === KEEP ? null : (dropped as Tenet),
      added: added === KEEP ? null : (added as Tenet),
    }),
    'A creed splits away'
  )
  const merging = useMadeAction(
    'ideology:merge',
    (_: void) => ({ keeper_id: creed ?? 0, absorbed_id: other ?? 0 }),
    'The two creeds are one'
  )
  const noSplit =
    creed === null || place === null
      ? 'Pick the creed and the follower that splits from it'
      : null
  const noMerge =
    creed === null || other === null
      ? 'Pick the creed that stays and the one it takes in'
      : creed === other
        ? 'A creed cannot merge with itself'
        : null
  return (
    <div className='grid min-w-0 grid-cols-1 gap-3 lg:grid-cols-2'>
      <ForgeCard
        icon={GitBranch}
        tone='warning'
        title='Split a creed'
        note='A follower breaks away with a creed of its own, dropping one tenet or taking up another.'
        columns={2}
        action={
          <StepButton
            icon={GitBranch}
            label='Split it'
            busy={why(blocked ?? noSplit, splitting.isPending)}
            onClick={() => splitting.mutate()}
          />
        }
      >
        <ThingPicker
          label='Creed'
          value={creed}
          onChange={setCreed}
          blocked={blocked}
          types={CREEDS}
        />
        <ThingPicker
          label='Follower that splits'
          value={place}
          onChange={setPlace}
          blocked={blocked}
          types={PLACES}
        />
        <ChoiceField
          label='Tenet it drops'
          value={dropped}
          table={{ ...KEEP_TENET, ...TENETS }}
          blocked={blocked}
          onPick={setDropped}
        />
        <ChoiceField
          label='Tenet it takes up'
          value={added}
          table={{ ...KEEP_TENET, ...TENETS }}
          blocked={blocked}
          onPick={setAdded}
        />
      </ForgeCard>
      <ForgeCard
        icon={GitMerge}
        tone='info'
        title='Merge two creeds'
        note='The first creed takes in the second: its tenets, its followers and the realms that hold it.'
        columns={2}
        action={
          <StepButton
            icon={GitMerge}
            label='Merge them'
            busy={why(blocked ?? noMerge, merging.isPending)}
            onClick={() => merging.mutate()}
          />
        }
      >
        <ThingPicker
          label='Creed that stays'
          value={creed}
          onChange={setCreed}
          blocked={blocked}
          types={CREEDS}
        />
        <ThingPicker
          label='Creed it takes in'
          value={other}
          onChange={setOther}
          blocked={blocked}
          types={CREEDS}
        />
      </ForgeCard>
    </div>
  )
}

export function ConstitutionSection({
  nodeId,
  blocked,
}: {
  nodeId: number
  blocked: string | null
}) {
  const query = useConstitution(nodeId)
  const [creed, setCreed] = useState<number | null>(null)
  const editing = useMadeAction(
    'constitution:edit',
    (vars: Edit) => ({
      polity_id: nodeId,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'The constitution is set'
  )
  const writing = useMadeAction(
    'constitution:write',
    (_: void) => ({ polity_id: nodeId, ideology_id: creed }),
    'The realm has a constitution'
  )
  const tearing = useMadeAction(
    'constitution:delete',
    (_: void) => ({ polity_id: nodeId }),
    'The constitution is torn up'
  )
  if (query.isPending) return <LoadingBlock label='Reading the constitution' />
  if (query.isError)
    return (
      <EmptyState
        icon={FileText}
        size='inline'
        title='This could not be read'
        description={query.error.message}
      />
    )
  const notRealm = query.data.is_realm ? null : NOT_REALM
  const row = query.data.constitution
  return (
    <div
      id='section-constitution'
      data-surface='ConstitutionSection'
      className='flex min-w-0 flex-col gap-3'
    >
      {row ? (
        <>
          <div className='grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-3'>
            <KpiTile
              label='Chosen by'
              value={SELECTORATES[row.selectorate].label}
              icon={SELECTORATES[row.selectorate].icon}
              tone='gold'
            />
            <KpiTile
              label='Offices'
              value={String(row.offices)}
              icon={ScrollText}
              tone='info'
            />
            <KpiTile
              label='Rights'
              value={String(row.rights)}
              icon={FileText}
              tone='success'
            />
          </div>
          <RecordRow
            icon={FileText}
            tone='gold'
            title={`A constitution written in epoch ${row.written_epoch}`}
            caption='It sets who chooses the ruler and how wide the public share runs'
          >
            <Ref node={row.ideology} empty='written for no creed' />
            <RecordEditor
              title='Set the constitution'
              note={HOLD}
              fields={FIELDS}
              locked={row.locked}
              busy={why(blocked, editing.isPending)}
              onSave={(values) => editing.mutate({ values, release: [] })}
              onRelease={(keys) =>
                editing.mutate({ values: {}, release: keys })
              }
            />
            <StepButton
              icon={Trash2}
              label='Tear it up'
              busy={why(blocked, tearing.isPending)}
              onClick={() => tearing.mutate()}
            />
          </RecordRow>
        </>
      ) : (
        <ForgeCard
          icon={FileText}
          tone='gold'
          title='Write a constitution'
          note={
            notRealm ??
            'A realm that holds a creed writes one by itself; write one now, for a creed or for none.'
          }
          columns={2}
          action={
            <StepButton
              icon={FileText}
              label='Write it'
              busy={why(blocked ?? notRealm, writing.isPending)}
              onClick={() => writing.mutate()}
            />
          }
        >
          <ThingPicker
            label='Creed it is written for'
            value={creed}
            onChange={setCreed}
            blocked={blocked ?? notRealm}
            types={CREEDS}
          />
        </ForgeCard>
      )}
      <CreedChanges blocked={blocked} />
    </div>
  )
}
