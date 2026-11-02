import { useState } from 'react'
import { MessageSquare, Users } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components, spokenIntentValues } from '@/api/generated/schema'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  EmptyState,
  EntityLink,
  ExpandableText,
  FormRow,
  PagedList,
  Portrait,
  Section,
} from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import { Label, Stat } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { DivergingBar } from '@/features/pantheon/DivergingBar'
import { RELATION_SCALE } from '@/features/pantheon/constants'
import { useGodGate, useRuleLookup } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { mediaUrl } from '@/features/pantheon/media'
import { relationLabel, signed } from '@/features/pantheon/relations'
import { type SonDetail } from './api'

type SpokenIntent = components['schemas']['SpokenIntent']

export function RelationEditor({
  sonId,
  options,
}: {
  sonId: number
  options: { id: number; name: string; value: number }[]
}) {
  const [other, setOther] = useState('')
  const [value, setValue] = useState('')
  const { reason } = useGodGate()
  const set = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/son:relation', {
          body: {
            first_id: sonId,
            second_id: Number(other),
            value: Number(value),
          },
        })
      ),
    success: 'The relation was set',
  })
  if (options.length === 0) return null
  return (
    <FormRow
      label='Set a relation'
      description='Shared domains, councils and deeds move it on their own.'
    >
      {(id) => (
        <>
          <Select
            value={other}
            onValueChange={(next) => {
              setOther(next)
              setValue(
                String(
                  options.find((item) => String(item.id) === next)?.value ?? ''
                )
              )
            }}
          >
            <SelectTrigger id={id} className='w-48'>
              <SelectValue placeholder='Pick a sibling' />
            </SelectTrigger>
            <SelectContent>
              {options.map((item) => (
                <SelectItem key={item.id} value={String(item.id)}>
                  {item.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            aria-label='Relation value'
            type='number'
            min={-RELATION_SCALE}
            max={RELATION_SCALE}
            value={value}
            className='w-32'
            onChange={(event) => setValue(event.target.value)}
          />
          <ActionButton
            label='Set'
            blocked={
              reason() ??
              (!other || value === '' ? 'Pick a sibling and a value.' : null)
            }
            pending={set.isPending}
            onRun={() => set.mutate()}
          />
        </>
      )}
    </FormRow>
  )
}

const INTENT_LABEL: Record<SpokenIntent, string> = {
  friendship: 'Friendship',
  alliance: 'Alliance',
  love: 'Love',
  threat: 'Threat',
  mockery: 'Mockery',
  warning: 'Warning',
  bargain: 'Bargain',
}

const SPEECH_MAX = 600

export function AddressSibling({
  sonId,
  alive,
  options,
}: {
  sonId: number
  alive: boolean
  options: { id: number; name: string }[]
}) {
  const [other, setOther] = useState('')
  const [intent, setIntent] = useState<SpokenIntent>('friendship')
  const [text, setText] = useState('')
  const { reason } = useGodGate()
  const speak = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/son:address_sibling', {
          body: {
            son_id: sonId,
            sibling_id: Number(other),
            intent,
            text: text.trim(),
          },
        })
      ),
    onDone: () => setText(''),
  })
  if (options.length === 0) return null
  return (
    <FormRow
      label='Order him to speak'
      description='The intent moves their relation; his charisma decides how far.'
    >
      {(id) => (
        <div className='flex min-w-0 flex-col gap-2'>
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <Select value={other} onValueChange={setOther}>
              <SelectTrigger
                id={id}
                className='w-48'
                aria-label='Sibling to address'
              >
                <SelectValue placeholder='Pick a sibling' />
              </SelectTrigger>
              <SelectContent>
                {options.map((item) => (
                  <SelectItem key={item.id} value={String(item.id)}>
                    {item.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={intent}
              onValueChange={(next) => setIntent(next as SpokenIntent)}
            >
              <SelectTrigger className='w-40' aria-label='Intent'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {spokenIntentValues.map((value) => (
                  <SelectItem key={value} value={value}>
                    {INTENT_LABEL[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Textarea
            aria-label='The words he must say'
            placeholder='The words he must say'
            maxLength={SPEECH_MAX}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <div className='flex min-w-0 flex-wrap items-center gap-2'>
            <ActionButton
              label='Speak'
              icon={MessageSquare}
              blocked={
                reason() ??
                (alive ? null : 'A dead son cannot speak.') ??
                (!other ? 'Pick a sibling.' : null) ??
                (text.trim() === '' ? 'Write the words he must say.' : null)
              }
              pending={speak.isPending}
              onRun={() => speak.mutate()}
            />
          </div>
        </div>
      )}
    </FormRow>
  )
}

export function SonSiblings({
  sonId,
  siblings,
  alive = true,
}: {
  sonId: number
  siblings: SonDetail['siblings']
  alive?: boolean
}) {
  const rule = useRuleLookup()
  return (
    <Section title='Siblings' level={3}>
      {siblings.length === 0 ? (
        <EmptyState
          icon={Users}
          size='compact'
          title='No siblings'
          description='Other sons appear here once they are summoned or born.'
        />
      ) : (
        <PagedList
          items={siblings}
          initial={8}
          noun={['sibling', 'siblings']}
          className='flex min-w-0 flex-col gap-2'
          itemKey={(sibling) => sibling.son.id}
        >
          {(sibling) => (
            <li className='grid min-w-0 grid-cols-1 items-center gap-2 rounded-lg border bg-card p-2.5 sm:grid-cols-3'>
              <div className='flex min-w-0 items-center gap-2'>
                <Portrait
                  name={sibling.son.name}
                  src={mediaUrl(sibling.cover)}
                  size='sm'
                />
                <EntityLink kind='son' id={String(sibling.son.id)}>
                  {sibling.son.name}
                </EntityLink>
              </div>
              <DivergingBar
                value={sibling.value}
                label={`Relation with ${sibling.son.name}`}
              />
              <div className='flex min-w-0 flex-col gap-0.5'>
                <span className='flex min-w-0 items-baseline gap-2'>
                  <Label>{relationLabel(sibling.value, rule)}</Label>
                  <Stat value={signed(sibling.value)} />
                </span>
                {sibling.note && (
                  <ExpandableText variant='caption' tone='muted' lines={2}>
                    <MentionText text={sibling.note} />
                  </ExpandableText>
                )}
              </div>
            </li>
          )}
        </PagedList>
      )}
      <RelationEditor
        sonId={sonId}
        options={siblings.map((sibling) => ({
          id: sibling.son.id,
          name: sibling.son.name,
          value: sibling.value,
        }))}
      />
      <AddressSibling
        sonId={sonId}
        alive={alive}
        options={siblings.map((sibling) => ({
          id: sibling.son.id,
          name: sibling.son.name,
        }))}
      />
    </Section>
  )
}
