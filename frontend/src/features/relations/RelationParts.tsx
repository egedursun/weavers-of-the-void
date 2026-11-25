import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BookOpen,
  CirclePlus,
  Coins,
  Flame,
  HandHeart,
  Languages,
  Scale,
  Swords,
  Trash2,
  Users,
  Zap,
} from 'lucide-react'
import { type EditValues } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { queryKeys } from '@/api/queryKeys'
import { LoadingBlock, ShowMore, useShowMore } from '@/components/domain'
import { Muted } from '@/components/typography'
import {
  type Field,
  ForgeCard,
  RecordEditor,
  RecordRow,
} from '@/features/cosmography/parts'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { type Named } from '@/features/entity/environment/labels'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField, NumberField } from '@/features/wars/military/parts'

type Component = components['schemas']['RelationComponent']
type Part = components['schemas']['RelationPartView']
type Edit = { values: EditValues; release: string[] }

const HOLD =
  'A value you set is held against the engine and shifts the whole relation until you release it.'
const PART_FIELDS: readonly Field[] = [
  {
    key: 'value',
    label: 'Weight in the relation',
    kind: 'number',
    min: -100,
    max: 100,
  },
]

export const RELATION_PARTS: Record<Component, Named> = {
  trade: { label: 'Trade', icon: Coins, tone: 'gold' },
  kinship: { label: 'Kinship', icon: Users, tone: 'success' },
  faith: { label: 'Faith', icon: BookOpen, tone: 'info' },
  war_memory: { label: 'Memory of war', icon: Swords, tone: 'danger' },
  help: { label: 'Help received', icon: HandHeart, tone: 'success' },
  insult: { label: 'Insults', icon: Zap, tone: 'warning' },
  rivalry: { label: 'Rivalry', icon: Flame, tone: 'danger' },
  language: { label: 'Shared tongue', icon: Languages, tone: 'verdigris' },
  values: { label: 'Kinship of values', icon: Scale, tone: 'info' },
}

const PARTS_SHOWN = 5

function useRelationParts(firstId: number, secondId: number) {
  return useQuery({
    queryKey: [
      ...queryKeys.world.all,
      'relation-parts',
      firstId,
      secondId,
    ] as const,
    queryFn: () =>
      unwrap(
        api.GET('/api/relations/{first_id}/{second_id}/parts', {
          params: { path: { first_id: firstId, second_id: secondId } },
        })
      ),
  })
}

function PartRow({
  part,
  firstId,
  secondId,
  blocked,
}: {
  part: Part
  firstId: number
  secondId: number
  blocked: string | null
}) {
  const named = RELATION_PARTS[part.component]
  const key = {
    first_id: firstId,
    second_id: secondId,
    component: part.component,
  }
  const editing = useMadeAction(
    'relation_component:edit',
    (vars: Edit) => ({
      ...key,
      values: vars.values,
      release: vars.release,
      hold: true,
    }),
    'That part of the relation is set'
  )
  const removing = useMadeAction(
    'relation_component:delete',
    (_: void) => key,
    'That part of the relation is struck out'
  )
  return (
    <RecordRow
      icon={named.icon}
      tone={part.value > 0 ? 'success' : part.value < 0 ? 'danger' : 'muted'}
      title={`${named.label} ${part.value > 0 ? '+' : ''}${part.value}`}
      caption={`reckoned in epoch ${part.updated_epoch}${part.locked.includes('value') ? ', held' : ''}`}
    >
      <RecordEditor
        act={editing}
        title='Set this part'
        note={HOLD}
        fields={PART_FIELDS}
        locked={part.locked}
        busy={why(blocked, editing.isPending)}
        onSave={(values) => editing.mutate({ values, release: [] })}
        onRelease={(keys) => editing.mutate({ values: {}, release: keys })}
      />
      <StepButton
        act={removing}
        icon={Trash2}
        label='Strike it'
        busy={why(blocked, removing.isPending)}
        onClick={() => removing.mutate()}
      />
    </RecordRow>
  )
}

export function RelationParts({
  firstId,
  secondId,
  blocked,
}: {
  firstId: number
  secondId: number
  blocked: string | null
}) {
  const query = useRelationParts(firstId, secondId)
  const shown = useShowMore(query.data?.parts ?? [], PARTS_SHOWN, PARTS_SHOWN)
  const [component, setComponent] = useState<string>('trade')
  const [value, setValue] = useState('10')
  const setting = useMadeAction(
    'relation_component:set',
    (_: void) => ({
      first_id: firstId,
      second_id: secondId,
      component: component as Component,
      value: Math.min(100, Math.max(-100, Number(value) || 0)),
    }),
    'That part of the relation is set and held'
  )
  if (query.isPending)
    return <LoadingBlock label='Reading what the relation is made of' />
  if (query.isError)
    return <Muted variant='caption'>{query.error.message}</Muted>
  return (
    <div data-surface='relation-parts' className='flex min-w-0 flex-col gap-2'>
      {query.data.parts.length ? (
        <>
          <ul className='flex min-w-0 flex-col gap-2'>
            {shown.visible.map((part) => (
              <PartRow
                key={part.component}
                part={part}
                firstId={firstId}
                secondId={secondId}
                blocked={blocked}
              />
            ))}
          </ul>
          <ShowMore state={shown} />
        </>
      ) : (
        <Muted variant='caption'>
          Its parts are reckoned at the next epoch.
        </Muted>
      )}
      <ForgeCard
        icon={CirclePlus}
        tone='info'
        title='Set a part of the relation'
        note='Trade, kinship, faith, memory of war, help, insults, rivalry, tongue and values add up to the relation between two communities.'
        columns={2}
        action={
          <StepButton
            act={setting}
            icon={CirclePlus}
            label='Set it'
            busy={why(blocked, setting.isPending)}
            onClick={() => setting.mutate()}
          />
        }
      >
        <ChoiceField
          label='Part'
          value={component}
          table={RELATION_PARTS}
          blocked={blocked}
          onPick={setComponent}
        />
        <NumberField
          label='Weight'
          value={value}
          min={-100}
          max={100}
          onChange={setValue}
        />
      </ForgeCard>
    </div>
  )
}
