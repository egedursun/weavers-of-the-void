import { useState } from 'react'
import { BookMarked, Save } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  ExpandableText,
  FormRow,
  PagedList,
  Section,
} from '@/components/domain'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label } from '@/components/typography'
import { KeeperByline } from '@/features/chronicle/KeeperByline'
import { type EntityContext } from '../actions/context'
import { optionsFor } from '../actions/pickers'
import { usePickerData } from '../actions/usePickerData'
import { useLoreMutation } from '../api/mutations'

const BELIEF_NAME_MAX = 80
const BELIEF_TEXT_MAX = 2000

function BeliefForm({
  ctx,
  readOnlyReason,
}: {
  ctx: EntityContext
  readOnlyReason: string | null
}) {
  const data = usePickerData()
  const [sonId, setSonId] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [narrative, setNarrative] = useState('')
  const [misconception, setMisconception] = useState('')
  const save = useLoreMutation({
    run: () =>
      unwrap(
        api.PUT('/api/beliefs', {
          body: {
            people_id: ctx.entity.id,
            son_id: sonId,
            name: name.trim() || null,
            narrative: narrative.trim(),
            misconception: misconception.trim() || null,
          },
        })
      ),
    success: 'The account was written',
    onDone: () => {
      setName('')
      setNarrative('')
      setMisconception('')
    },
  })
  const reason =
    readOnlyReason ??
    (narrative.trim() === '' ? 'Write what they tell.' : null) ??
    (save.isPending ? 'Working on it.' : null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <FormRow label='About the god' description='Empty means the Creator'>
        {(id) => (
          <RecordCombobox
            id={id}
            options={optionsFor({ source: 'son', status: 'any' }, ctx, data)}
            value={sonId === null ? null : String(sonId)}
            onChange={(value) =>
              setSonId(value === null ? null : Number(value))
            }
            placeholder='The Creator'
            clearable
            aria-label='About the god'
          />
        )}
      </FormRow>
      <FormRow label='The name they use' description='Optional'>
        {(id) => (
          <Input
            id={id}
            maxLength={BELIEF_NAME_MAX}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='What they tell'>
        {(id) => (
          <Textarea
            id={id}
            maxLength={BELIEF_TEXT_MAX}
            value={narrative}
            onChange={(event) => setNarrative(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow
        label="God's eye: the truth"
        description='Optional; what they get wrong'
      >
        {(id) => (
          <Textarea
            id={id}
            maxLength={BELIEF_TEXT_MAX}
            value={misconception}
            onChange={(event) => setMisconception(event.target.value)}
          />
        )}
      </FormRow>
      <Button
        className='self-start'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => save.mutate()}
      >
        <Save />
        Save the account
      </Button>
    </div>
  )
}

export function PeopleBeliefs({
  ctx,
  readOnlyReason,
}: {
  ctx: EntityContext
  readOnlyReason: string | null
}) {
  if (ctx.type !== 'people') return null
  const perspectives = ctx.detail.perspectives
  return (
    <>
      <Section
        id='section-beliefs'
        title='Beliefs'
        description='Write or rewrite how this people tells of a god; the same people and god pair is overwritten.'
      >
        <BeliefForm ctx={ctx} readOnlyReason={readOnlyReason} />
      </Section>
      <Section id='section-historians' title='What its historians wrote'>
        {perspectives.length === 0 ? (
          <EmptyState
            size='compact'
            icon={BookMarked}
            title='No historian yet'
            description='As epochs close, this people writes history from its own eyes.'
          />
        ) : (
          <PagedList
            items={perspectives}
            initial={3}
            noun={['history', 'histories']}
            className='flex min-w-0 flex-col gap-3'
            itemKey={(item) => item.id}
          >
            {(item) => (
              <li className='flex min-w-0 flex-col gap-1 rounded-md border surface-sheen border-gild/60 bg-card px-3 py-2'>
                <Label>{`Epoch ${formatInteger(item.epoch)}`}</Label>
                <KeeperByline
                  lead='Written by'
                  id={item.historian_entity_id}
                  name={item.historian}
                  fallback='a historian whose name is lost'
                />
                <ExpandableText lines={4}>{item.text}</ExpandableText>
              </li>
            )}
          </PagedList>
        )}
      </Section>
    </>
  )
}
