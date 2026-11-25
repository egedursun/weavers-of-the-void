import { useState } from 'react'
import { Gavel, Plus, Trash2 } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import {
  ConfirmDialog,
  EmptyState,
  EntityLink,
  FormRow,
  PagedList,
  Section,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Text } from '@/components/typography'
import { type EntityContext } from '../actions/context'
import { optionsFor } from '../actions/pickers'
import { usePickerData } from '../actions/usePickerData'
import { useLoreMutation } from '../api/mutations'
import { type FactView } from '../api/types'
import { FACT_OBJECT_MAX, FACT_PREDICATE_MAX } from '../constants'

type CanonFactsProps = {
  ctx: EntityContext
  readOnlyReason: string | null
}

function FactRow({
  fact,
  selfId,
  onDelete,
  blocked,
}: {
  fact: FactView
  selfId: number
  onDelete: () => void
  blocked: string | null
}) {
  const subject = fact.subject
  return (
    <li className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2'>
      <Text as='div' className='min-w-0 flex-1'>
        {subject && subject.id !== selfId ? (
          <EntityLink kind='entity' id={String(subject.id)}>
            {subject.name}
          </EntityLink>
        ) : (
          <Text as='strong' weight='semibold'>
            {subject?.name ?? 'It'}
          </Text>
        )}{' '}
        <Text as='span' tone='muted'>
          {fact.predicate}
        </Text>{' '}
        {fact.object ? (
          <EntityLink kind='entity' id={String(fact.object.id)}>
            {fact.object.name}
          </EntityLink>
        ) : (
          (fact.object_text ?? '—')
        )}
      </Text>
      <Label>{`Epoch ${formatInteger(fact.epoch)}`}</Label>
      <Button
        variant='ghost'
        size='icon-sm'
        aria-label='Retire this fact'
        disabled={blocked !== null}
        disabledReason={blocked ?? undefined}
        onClick={onDelete}
      >
        <Trash2 />
      </Button>
    </li>
  )
}

export function CanonFacts({ ctx, readOnlyReason }: CanonFactsProps) {
  const data = usePickerData()
  const [predicate, setPredicate] = useState('')
  const [objectId, setObjectId] = useState<number | null>(null)
  const [objectText, setObjectText] = useState('')
  const [removing, setRemoving] = useState<FactView | null>(null)
  const add = useLoreMutation({
    writes: [{ lever: 'fact:add' }],
    run: () =>
      unwrap(
        api.POST('/api/facts', {
          body: {
            subject_id: ctx.entity.id,
            relation: predicate.trim(),
            object_id: objectId,
            object_text: objectId === null ? objectText.trim() : null,
          },
        })
      ),
    success: 'Fact written into canon',
    onDone: () => {
      setPredicate('')
      setObjectId(null)
      setObjectText('')
    },
  })
  const remove = useLoreMutation({
    writes: [{ lever: 'fact:remove' }],
    run: (factId: number) =>
      unwrap(
        api.DELETE('/api/facts/{fact_id}', {
          params: { path: { fact_id: factId } },
        })
      ),
    success: 'Fact removed from canon',
  })
  const facts = ctx.detail.facts
  const addReason =
    readOnlyReason ??
    (predicate.trim() === '' ? 'Write the predicate first.' : null) ??
    (objectId === null && objectText.trim() === ''
      ? 'Choose a record or write the object.'
      : null) ??
    (add.isPending ? 'Working on it.' : null)
  return (
    <Section
      id='section-facts'
      title='Canon facts'
      description='What Fate and you have fixed about this record; every agent obeys them.'
    >
      {facts.length === 0 ? (
        <EmptyState
          size='compact'
          icon={Gavel}
          title='No fixed facts'
          description='No fact has been fixed about this record yet.'
        />
      ) : (
        <PagedList
          items={facts}
          initial={6}
          noun={['fact', 'facts']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(fact) => fact.id}
        >
          {(fact) => (
            <FactRow
              fact={fact}
              selfId={ctx.entity.id}
              blocked={
                readOnlyReason ?? (remove.isPending ? 'Working on it.' : null)
              }
              onDelete={() => setRemoving(fact)}
            />
          )}
        </PagedList>
      )}
      <Collapsible className='flex min-w-0 flex-col gap-3'>
        <CollapsibleTrigger asChild>
          <Button act={add} variant='outline' className='self-start'>
            <Plus />
            Add fact
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
          <FormRow
            label='Predicate'
            description='forbids, opens only at night…'
          >
            {(id) => (
              <Input
                id={id}
                maxLength={FACT_PREDICATE_MAX}
                value={predicate}
                onChange={(event) => setPredicate(event.target.value)}
              />
            )}
          </FormRow>
          <FormRow
            label='Object record'
            description='Optional; or write it below'
          >
            {(id) => (
              <RecordCombobox
                id={id}
                options={optionsFor(
                  {
                    source: 'entity',
                    statuses: ['canon', 'dead', 'destroyed'],
                  },
                  ctx,
                  data
                )}
                value={objectId === null ? null : String(objectId)}
                onChange={(value) =>
                  setObjectId(value === null ? null : Number(value))
                }
                placeholder='Choose a record'
                clearable
                aria-label='Object record'
              />
            )}
          </FormRow>
          <FormRow label='Or plain text'>
            {(id) => (
              <Input
                id={id}
                maxLength={FACT_OBJECT_MAX}
                disabled={objectId !== null}
                value={objectText}
                onChange={(event) => setObjectText(event.target.value)}
              />
            )}
          </FormRow>
          <Button
            act={add}
            className='self-start'
            disabled={addReason !== null}
            disabledReason={addReason ?? undefined}
            onClick={() => add.mutate()}
          >
            <Gavel />
            Fix it in canon
          </Button>
        </CollapsibleContent>
      </Collapsible>
      <ConfirmDialog
        act={remove}
        open={removing !== null}
        onOpenChange={(open) => !open && setRemoving(null)}
        title='Retire this fact?'
        desc={
          removing
            ? `"${removing.predicate}" will no longer bind the agents.`
            : ''
        }
        destructive
        confirmText='Retire'
        isLoading={remove.isPending}
        handleConfirm={() => {
          if (removing) remove.mutate(removing.id)
          setRemoving(null)
        }}
      />
    </Section>
  )
}
