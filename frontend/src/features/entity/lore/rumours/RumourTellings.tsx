import { useState } from 'react'
import { Lock, PenLine, Plus, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import type { components } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EntityLink, Paged } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodAction } from '@/features/pantheon/godAction'
import { spokenKey } from '@/features/records/format'
import {
  INCIDENT_ROLE,
  RUMOUR_DISTORTION,
  STEP_ACTION,
  STEP_OUTCOME,
} from '@/features/records/labels'
import { NodeRef } from '@/features/records/parts'
import { AdjustBlock, ChoiceSelect } from '../LoreFields'
import type { LoreNamed } from '../model'
import type { Rumour } from './rumourModel'

type Distortion = NonNullable<Rumour['distortions']>[number]
type DistortionKind = components['schemas']['RumourDistortion']
type Role = components['schemas']['IncidentRole']
type Action = components['schemas']['StepAction']
type Outcome = components['schemas']['StepOutcome']
type Keys = readonly (readonly unknown[])[]

const ANY_RECORD = [
  'mortal',
  'settlement',
  'people',
  'polity',
  'army',
  'item',
  'beast',
  'faction',
  'cult',
] as const
const ROLE_CHOICES: readonly DistortionKind[] = [
  'doer_swapped',
  'target_swapped',
  'role_changed',
]
const STEP_CHOICES: readonly DistortionKind[] = ['step_added', 'step_dropped']
const FACT_CHOICES: readonly DistortionKind[] = [
  'amount_changed',
  'outcome_changed',
]

function lore(
  table: Record<string, { label: string; icon: LoreNamed['icon'] }>
): Record<string, LoreNamed> {
  return Object.fromEntries(
    Object.entries(table).map(([key, spec]) => [
      key,
      { label: spec.label, icon: spec.icon, tone: 'warning' as const },
    ])
  )
}

function ToldValue({ item }: { item: Distortion }) {
  if (item.told) return <NodeRef id={item.told.id} name={item.told.name} />
  if (item.told_number !== null)
    return <Text as='span'>{String(item.told_number)}</Text>
  if (item.told_year !== null)
    return <Text as='span'>{`year ${item.told_year}`}</Text>
  if (item.told_action !== null)
    return <Text as='span'>{STEP_ACTION[item.told_action].label}</Text>
  if (item.told_outcome !== null)
    return <Text as='span'>{STEP_OUTCOME[item.told_outcome].label}</Text>
  if (item.told_incident_id !== null)
    return (
      <EntityLink kind='incident' id={String(item.told_incident_id)} showIcon>
        another happening
      </EntityLink>
    )
  if (item.told_enum_value !== null)
    return <Text as='span'>{spokenKey(item.told_enum_value)}</Text>
  return <Muted as='span'>left out of the telling</Muted>
}

function Target({ item }: { item: Distortion }) {
  if (item.role !== null)
    return (
      <Muted as='span'>{`${INCIDENT_ROLE[item.role].label}${item.step_id !== null ? ', in one step' : ''}`}</Muted>
    )
  if (item.fact_key !== null)
    return <Muted as='span'>{spokenKey(item.fact_key)}</Muted>
  if (item.step_id !== null) return <Muted as='span'>one step</Muted>
  return null
}

type Draft = {
  distortion: DistortionKind
  role: Role | null
  fact_key: string
  step_id: string
  told_node_id: number | null
  told_number: string
  told_year: string
  told_action: Action | null
  told_outcome: Outcome | null
  told_enum_value: string
  told_incident_id: string
}

const EMPTY: Draft = {
  distortion: 'moment_changed',
  role: null,
  fact_key: '',
  step_id: '',
  told_node_id: null,
  told_number: '',
  told_year: '',
  told_action: null,
  told_outcome: null,
  told_enum_value: '',
  told_incident_id: '',
}

function numberOrNull(text: string): number | null {
  const value = Number(text)
  return text.trim() === '' || Number.isNaN(value) ? null : value
}

function payload(draft: Draft) {
  return {
    distortion: draft.distortion,
    role: draft.role,
    fact_key: draft.fact_key.trim() || null,
    step_id: numberOrNull(draft.step_id),
    told_node_id: draft.told_node_id,
    told_number: numberOrNull(draft.told_number),
    told_year: numberOrNull(draft.told_year),
    told_action: draft.told_action,
    told_outcome: draft.told_outcome,
    told_enum_value: draft.told_enum_value.trim() || null,
    told_incident_id: numberOrNull(draft.told_incident_id),
  }
}

function missing(draft: Draft): string | null {
  const kind = draft.distortion
  const noStep = draft.step_id.trim() === ''
  if (ROLE_CHOICES.includes(kind) && noStep && draft.role === null)
    return 'Choose the role told otherwise'
  if (ROLE_CHOICES.includes(kind) && noStep && draft.told_node_id === null)
    return 'Choose who is told in their place'
  if (STEP_CHOICES.includes(kind) && noStep)
    return 'Give the step by its number'
  if (kind === 'step_added' && draft.told_action === null)
    return 'Choose what is said to have been done'
  if (FACT_CHOICES.includes(kind) && noStep && draft.fact_key.trim() === '')
    return 'Name the fact told otherwise'
  if (kind === 'amount_changed' && draft.told_number.trim() === '')
    return 'Give the amount told instead'
  if (kind === 'place_changed' && draft.told_node_id === null)
    return 'Choose the place told instead'
  if (kind === 'moment_changed' && draft.told_year.trim() === '')
    return 'Give the year told instead'
  if (kind === 'cause_changed' && draft.told_incident_id.trim() === '')
    return 'Give the happening told as its cause'
  return null
}

function DraftFields({
  draft,
  setDraft,
  blocked,
}: {
  draft: Draft
  setDraft: (next: Draft) => void
  blocked: string | null
}) {
  const kind = draft.distortion
  const byRole = ROLE_CHOICES.includes(kind)
  const byStep = STEP_CHOICES.includes(kind) || kind === 'role_changed'
  const byFact = FACT_CHOICES.includes(kind)
  const set = (patch: Partial<Draft>) => setDraft({ ...draft, ...patch })
  return (
    <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
      <ChoiceSelect
        label='How the telling changes'
        value={draft.distortion}
        table={lore(RUMOUR_DISTORTION)}
        blocked={blocked}
        onPick={(value) => set({ distortion: value as DistortionKind })}
      />
      {byRole && (
        <ChoiceSelect
          label='Role told otherwise'
          value={draft.role ?? ''}
          table={lore(INCIDENT_ROLE)}
          blocked={blocked}
          placeholder='Choose a role…'
          onPick={(value) => set({ role: value as Role })}
        />
      )}
      {(byRole || kind === 'place_changed') && (
        <EntityPicker
          types={[...ANY_RECORD]}
          value={draft.told_node_id}
          onChange={(id) => set({ told_node_id: id })}
          placeholder='Who or where is told instead…'
        />
      )}
      {(byStep || kind === 'outcome_changed') && (
        <Input
          type='number'
          min={0}
          aria-label='Number of the step told otherwise'
          placeholder='Step number'
          value={draft.step_id}
          onChange={(event) => set({ step_id: event.target.value })}
        />
      )}
      {kind === 'step_added' && (
        <ChoiceSelect
          label='What is said to have been done'
          value={draft.told_action ?? ''}
          table={lore(STEP_ACTION)}
          blocked={blocked}
          placeholder='Choose a deed…'
          onPick={(value) => set({ told_action: value as Action })}
        />
      )}
      {kind === 'outcome_changed' && (
        <ChoiceSelect
          label='Outcome told instead'
          value={draft.told_outcome ?? ''}
          table={lore(STEP_OUTCOME)}
          blocked={blocked}
          placeholder='Choose an outcome…'
          onPick={(value) => set({ told_outcome: value as Outcome })}
        />
      )}
      {byFact && (
        <Input
          aria-label='Key of the fact told otherwise'
          placeholder='Fact key'
          value={draft.fact_key}
          onChange={(event) => set({ fact_key: event.target.value })}
        />
      )}
      {kind === 'amount_changed' && (
        <Input
          type='number'
          aria-label='Amount told instead'
          placeholder='Amount told'
          value={draft.told_number}
          onChange={(event) => set({ told_number: event.target.value })}
        />
      )}
      {(byFact || kind === 'role_changed') && (
        <Input
          aria-label='Value told instead'
          placeholder='Value told'
          value={draft.told_enum_value}
          onChange={(event) => set({ told_enum_value: event.target.value })}
        />
      )}
      {kind === 'moment_changed' && (
        <Input
          type='number'
          min={0}
          aria-label='Year told instead'
          placeholder='Year told'
          value={draft.told_year}
          onChange={(event) => set({ told_year: event.target.value })}
        />
      )}
      {kind === 'cause_changed' && (
        <Input
          type='number'
          min={0}
          aria-label='Number of the happening told as its cause'
          placeholder='Happening number'
          value={draft.told_incident_id}
          onChange={(event) => set({ told_incident_id: event.target.value })}
        />
      )}
    </div>
  )
}

function draftOf(item: Distortion): Draft {
  return {
    distortion: item.distortion,
    role: item.role,
    fact_key: item.fact_key ?? '',
    step_id: item.step_id !== null ? String(item.step_id) : '',
    told_node_id: item.told?.id ?? null,
    told_number: item.told_number !== null ? String(item.told_number) : '',
    told_year: item.told_year !== null ? String(item.told_year) : '',
    told_action: item.told_action,
    told_outcome: item.told_outcome,
    told_enum_value: item.told_enum_value ?? '',
    told_incident_id:
      item.told_incident_id !== null ? String(item.told_incident_id) : '',
  }
}

function DistortionRow({
  item,
  blocked,
  invalidate,
}: {
  item: Distortion
  blocked: string | null
  invalidate: Keys
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<Draft>(() => draftOf(item))
  const edit = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/rumour_distortion:edit', {
          body: {
            rumour_distortion_id: item.id,
            ...payload(draft),
            hold: ['told'],
          },
        })
      ),
    invalidate: [...invalidate],
  })
  const strike = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/rumour_distortion:delete', {
          body: { rumour_distortion_id: item.id },
        })
      ),
    invalidate: [...invalidate],
  })
  const spec = RUMOUR_DISTORTION[item.distortion]
  const Icon = spec.icon
  const busy =
    blocked ??
    (edit.isPending || strike.isPending ? 'Saving the telling…' : null)
  const lacking = missing(draft)
  return (
    <li className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant='outline'>
          <Icon aria-hidden='true' />
          {spec.label}
        </Badge>
        <Target item={item} />
        <Muted as='span'>told as</Muted>
        <ToldValue item={item} />
        <Muted variant='caption'>{`since age ${item.epoch}`}</Muted>
        {item.locked.length > 0 && (
          <Badge variant='default'>
            <Lock aria-hidden='true' />
            Held
          </Badge>
        )}
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => setEditing(!editing)}
        >
          <PenLine />
          {editing ? 'Close' : 'Rewrite'}
        </Button>
        <Button
          size='sm'
          variant='ghost'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => strike.mutate()}
        >
          <Trash2 />
          Set it right
        </Button>
      </div>
      {editing && (
        <div className='flex min-w-0 flex-col gap-2'>
          <DraftFields draft={draft} setDraft={setDraft} blocked={busy} />
          <Button
            size='sm'
            className='self-start'
            disabled={busy !== null || lacking !== null}
            disabledReason={busy ?? lacking ?? undefined}
            onClick={() => edit.mutate()}
          >
            <Lock />
            Keep it told so
          </Button>
        </div>
      )}
    </li>
  )
}

export function RumourTellings({
  rumourId,
  distortions,
  blocked,
  invalidate,
}: {
  rumourId: number
  distortions: readonly Distortion[]
  blocked: string | null
  invalidate: Keys
}) {
  const [draft, setDraft] = useState<Draft>(EMPTY)
  const add = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/rumour_distortion:create', {
          body: { rumour_id: rumourId, ...payload(draft) },
        })
      ),
    invalidate: [...invalidate],
  })
  const busy = blocked ?? (add.isPending ? 'Saving the telling…' : null)
  const lacking = missing(draft)
  return (
    <section
      aria-label='How this telling differs from what happened'
      className='flex min-w-0 flex-col gap-2'
    >
      <Label>How this telling differs from what happened</Label>
      {distortions.length === 0 ? (
        <Muted variant='caption'>
          This telling keeps to the happening as it was set down.
        </Muted>
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={distortions} as='li'>
            {(item) => (
              <DistortionRow
                key={item.id}
                item={item}
                blocked={blocked}
                invalidate={invalidate}
              />
            )}
          </Paged>
        </ul>
      )}
      <AdjustBlock title='Change how it is told' icon={Plus}>
        <DraftFields draft={draft} setDraft={setDraft} blocked={busy} />
        <Button
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null || lacking !== null}
          disabledReason={busy ?? lacking ?? undefined}
          onClick={() => add.mutate()}
        >
          <Plus />
          Tell it so
        </Button>
      </AdjustBlock>
    </section>
  )
}
