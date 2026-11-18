import { useId, useMemo, useState } from 'react'
import { Feather, Pencil, Trash2 } from 'lucide-react'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  EntityLink,
  Paged,
  Section,
  FieldTile,
} from '@/components/domain'
import { Label, Text } from '@/components/typography'
import { fixedCost } from '@/features/entity/actions/gate'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { useNames } from '@/features/pantheon/api'
import { useCostText, useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import {
  type HistorianView,
  deleteHistorianView,
  editHistorianView,
  fateKeys,
} from './api'

export const HISTORIAN_TEXT_MAX = 6000

type HistorianViewsPanelProps = {
  views: HistorianView[]
  epoch: number | null
}

function usePeopleNames() {
  const names = useNames()
  return useMemo(() => {
    const table = new Map<number, string>()
    for (const entry of names.data ?? [])
      if (entry.kind === 'entity') table.set(entry.id, entry.name)
    return table
  }, [names.data])
}

function ViewRow({
  view,
  people,
  cost,
}: {
  view: HistorianView
  people: string
  cost: number | null
}) {
  const fieldId = useId()
  const { reason } = useGodGate()
  const [draft, setDraft] = useState<string | null>(null)
  const edit = useGodAction({
    run: editHistorianView,
    invalidate: [fateKeys.controls],
    onDone: () => setDraft(null),
  })
  const strike = useGodAction({
    run: deleteHistorianView,
    invalidate: [fateKeys.controls],
  })
  const blocked = reason({ cost: cost ?? undefined })
  const trimmed = draft?.trim() ?? ''
  return (
    <li
      data-historian-view={view.id}
      className='flex min-w-0 flex-col gap-2 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <div className='flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2'>
        <div className='flex min-w-0 flex-1 basis-60 flex-col gap-0.5'>
          <Text weight='medium' truncate={2}>
            <EntityLink kind='entity' id={String(view.people_entity_id)}>
              {people}
            </EntityLink>
          </Text>
          <Label truncate>{view.historian ?? 'An unnamed historian'}</Label>
        </div>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          {draft === null && (
            <Button
              variant='outline'
              size='sm'
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={() => setDraft(view.text)}
            >
              <Pencil />
              Amend
            </Button>
          )}
          <ActionButton
            label='Strike'
            icon={Trash2}
            size='sm'
            variant='destructive'
            cost={cost ?? undefined}
            blocked={blocked}
            pending={strike.isPending}
            confirm={{
              title: 'Strike this account?',
              description: `The account of ${people} by ${view.historian ?? 'an unnamed historian'} is removed from history.`,
            }}
            onRun={() => strike.mutate(view.id)}
          />
        </div>
      </div>
      {draft === null ? (
        <Text variant='prose'>{view.text}</Text>
      ) : (
        <div className='flex min-w-0 flex-col gap-2'>
          <FieldTile id={fieldId} label='The amended account'>
            <Textarea
              id={fieldId}
              value={draft}
              maxLength={HISTORIAN_TEXT_MAX}
              onChange={(event) => setDraft(event.target.value)}
            />
          </FieldTile>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <ActionButton
              label='Save the account'
              size='sm'
              cost={cost ?? undefined}
              rule='costs.edit_historian_view'
              blocked={
                blocked ??
                (trimmed === '' ? 'An account cannot be empty.' : null)
              }
              pending={edit.isPending}
              onRun={() => edit.mutate({ viewId: view.id, text: trimmed })}
            />
            <Button variant='ghost' size='sm' onClick={() => setDraft(null)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </li>
  )
}

export function HistorianViewsPanel({
  views,
  epoch,
}: HistorianViewsPanelProps) {
  const people = usePeopleNames()
  const costOf = useCostText()
  const cost = fixedCost(costOf('voices:edit_view')?.cost)
  return (
    <Section
      title='Historian accounts'
      description={
        epoch === null
          ? 'The voices of the peoples write after every epoch.'
          : `What the historians of each people wrote about epoch ${formatInteger(epoch)}. Amend or strike any of them.`
      }
      surface='card'
      level={3}
      icon={Feather}
      tone='verdigris'
    >
      {views.length === 0 ? (
        <EmptyState
          size='compact'
          icon={Feather}
          title='No accounts yet'
          description='The historians write once the voices of the peoples have run for an epoch.'
        />
      ) : (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={views} as='li'>
            {(view) => (
              <ViewRow
                key={view.id}
                view={view}
                cost={cost}
                people={
                  people.get(view.people_entity_id) ??
                  `People ${view.people_entity_id}`
                }
              />
            )}
          </Paged>
        </ul>
      )}
    </Section>
  )
}
