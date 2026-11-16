import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BookA,
  Globe2,
  Languages,
  Plus,
  Quote,
  Trash2,
  TriangleAlert,
} from 'lucide-react'
import { type ActionBody, postAction } from '@/api/actions'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  EntityLink,
  LoadingBlock,
  Medallion,
  Paged,
  PagedList,
  Section,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { loreKeys } from '../api/keys'

const WORKING = 'Working on it.'
function useRow<
  Name extends 'record_row:edit' | 'record_row:create' | 'record_row:delete',
>(name: Name) {
  return useGodAction<ActionBody<Name>>({
    run: (body) => postAction(name, body),
  })
}

function TextEditor({
  label,
  value,
  blocked,
  onSave,
}: {
  label: string
  value: string
  blocked: string | null
  onSave: (next: string) => void
}) {
  const [draft, setDraft] = useState(value)
  const problem =
    draft.trim() === ''
      ? 'Write something first'
      : draft === value
        ? 'This is the present value'
        : null
  return (
    <form
      className='flex min-w-0 items-end gap-2'
      onSubmit={(event) => {
        event.preventDefault()
        if ((blocked ?? problem) === null) onSave(draft.trim())
      }}
    >
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <Label>{label}</Label>
        <Input
          aria-label={label}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
      </div>
      <Button
        type='submit'
        size='sm'
        variant='outline'
        disabled={(blocked ?? problem) !== null}
        disabledReason={blocked ?? problem ?? undefined}
      >
        Set
      </Button>
    </form>
  )
}

export function NameSection({ nodeId }: { nodeId: number }) {
  const view = useQuery({
    queryKey: [...loreKeys.entity(nodeId), 'name'],
    queryFn: () =>
      unwrap(
        api.GET('/api/nodes/{node_id}/name', {
          params: { path: { node_id: nodeId } },
        })
      ),
  })
  const edit = useRow('record_row:edit')
  const create = useRow('record_row:create')
  const remove = useRow('record_row:delete')
  const [tongue, setTongue] = useState<number | null>(null)
  const [form, setForm] = useState('')
  const { reason } = useGodGate()
  const pending = edit.isPending || create.isPending || remove.isPending
  const blocked = reason() ?? (pending ? WORKING : null)
  const card = view.data
  return (
    <Section
      id='section-name'
      title='Name and meaning'
      description='What its name means in its own tongue, what neighbours call it and the epithet the world gives it.'
      icon={BookA}
    >
      {view.isPending && <LoadingBlock label='Reading its name' />}
      {view.isError && (
        <EmptyState
          icon={TriangleAlert}
          title='Its name could not be read'
          description={view.error.message}
        />
      )}
      {card && (
        <div data-surface='NameMeaning' className='flex min-w-0 flex-col gap-4'>
          <div className='flex min-w-0 items-start gap-3 rounded-md border surface-well border-gild/20 bg-muted/60 p-3'>
            <Medallion icon={BookA} tone='gold' />
            <div className='flex min-w-0 flex-1 flex-col gap-1'>
              <Text as='span' weight='semibold'>
                {card.current_name}
              </Text>
              {card.meaning ? (
                <>
                  <Muted variant='caption'>
                    {card.meaning.gloss
                      ? `Means “${card.meaning.gloss}”`
                      : 'Its meaning is not yet known.'}
                  </Muted>
                  <div className='flex min-w-0 flex-col gap-2'>
                    <PagedList
                      items={card.meaning.morphemes}
                      initial={12}
                      noun={['entry', 'entries']}
                      as='div'
                      className='flex min-w-0 flex-wrap gap-1.5'
                      itemKey={(part, index) => `${part}-${index}`}
                    >
                      {(part, index) => (
                        <Badge
                          key={`${part}-${index}`}
                          size='sm'
                          variant='outline'
                        >
                          {part}
                        </Badge>
                      )}
                    </PagedList>
                    <div className='flex min-w-0 flex-wrap gap-1.5'>
                      {card.meaning.language && (
                        <Badge size='sm' variant='secondary'>
                          <Languages aria-hidden='true' />
                          {card.meaning.language.name}
                        </Badge>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <Muted variant='caption'>
                  No meaning has been given to its name yet; the world gives one
                  after the next epoch, or you can.
                </Muted>
              )}
            </div>
          </div>
          {card.meaning ? (
            <div className='flex min-w-0 flex-col gap-2'>
              <TextEditor
                key={`gloss-${card.meaning.gloss}`}
                label='Its meaning'
                value={card.meaning.gloss}
                blocked={blocked}
                onSave={(gloss) =>
                  edit.mutate({
                    table: 'name_meanings',
                    key: { node_id: nodeId },
                    values: { gloss },
                    hold: true,
                  })
                }
              />
              <Button
                size='sm'
                variant='ghost'
                className='self-start'
                disabled={blocked !== null}
                disabledReason={blocked ?? undefined}
                onClick={() =>
                  remove.mutate({
                    table: 'name_meanings',
                    key: { node_id: nodeId },
                  })
                }
              >
                <Trash2 />
                Forget its meaning
              </Button>
            </div>
          ) : (
            <TextEditor
              label='Give its name a meaning'
              value=''
              blocked={blocked}
              onSave={(gloss) =>
                create.mutate({
                  table: 'name_meanings',
                  values: {
                    node_id: nodeId,
                    name: card.current_name,
                    gloss,
                    morphemes: [card.current_name],
                    epoch: 0,
                  },
                })
              }
            />
          )}
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>What neighbours call it</Label>
            {card.exonyms.length === 0 ? (
              <Muted>No other tongue has a name for it yet.</Muted>
            ) : (
              <ul className='flex min-w-0 flex-col gap-1.5'>
                <Paged items={card.exonyms} as='li'>
                  {(row) => (
                    <li
                      key={row.language.id}
                      className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card px-2.5 py-1.5'
                    >
                      <Medallion icon={Globe2} tone='info' size='sm' />
                      <Text as='span' weight='medium'>
                        {row.form}
                      </Text>
                      <Muted as='span' variant='caption' className='flex-1'>
                        in{' '}
                        <EntityLink kind='entity' id={String(row.language.id)}>
                          {row.language.name}
                        </EntityLink>
                      </Muted>
                      <Button
                        size='icon-sm'
                        variant='ghost'
                        aria-label={`Forget the name in ${row.language.name}`}
                        disabled={blocked !== null}
                        disabledReason={blocked ?? undefined}
                        onClick={() =>
                          remove.mutate({
                            table: 'name_exonyms',
                            key: {
                              node_id: nodeId,
                              language_entity_id: row.language.id,
                            },
                          })
                        }
                      >
                        <Trash2 />
                      </Button>
                    </li>
                  )}
                </Paged>
              </ul>
            )}
            <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
              <div className='flex min-w-0 flex-col gap-1'>
                <Label>Tongue</Label>
                <EntityPicker
                  types={['language']}
                  value={tongue}
                  onChange={setTongue}
                  placeholder='Choose a tongue'
                />
              </div>
              <div className='flex min-w-0 flex-col gap-1'>
                <Label>Its name there</Label>
                <Input
                  aria-label='Its name there'
                  value={form}
                  onChange={(event) => setForm(event.target.value)}
                />
              </div>
            </div>
            <Button
              size='sm'
              variant='outline'
              className='self-start'
              disabled={
                blocked !== null || tongue === null || form.trim() === ''
              }
              disabledReason={
                blocked ??
                (tongue === null
                  ? 'Choose a tongue'
                  : form.trim() === ''
                    ? 'Write the name'
                    : undefined)
              }
              onClick={() => {
                if (tongue === null) return
                create.mutate({
                  table: 'name_exonyms',
                  values: {
                    node_id: nodeId,
                    language_entity_id: tongue,
                    form: form.trim(),
                    gloss: card.meaning?.gloss ?? '',
                    epoch: 0,
                  },
                })
                setForm('')
              }}
            >
              <Plus />
              Give it that name
            </Button>
          </div>
          <div className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>Epithet</Label>
            {!card.epithets_allowed ? (
              <Muted>
                Epithets are given to the beings and things of the worlds; a
                god, a world or a star is known by its name alone.
              </Muted>
            ) : card.epithet ? (
              <div className='flex min-w-0 flex-col gap-2'>
                <div className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-primary/40 bg-primary/5 px-2.5 py-1.5'>
                  <Medallion icon={Quote} tone='gold' size='sm' />
                  <Text as='span' weight='semibold'>
                    {card.epithet.epithet}
                  </Text>
                  <Muted as='span' variant='caption'>
                    {card.epithet.gloss}
                  </Muted>
                </div>
                <TextEditor
                  key={`epithet-${card.epithet.epithet}`}
                  label='The epithet'
                  value={card.epithet.epithet}
                  blocked={blocked}
                  onSave={(epithet) =>
                    edit.mutate({
                      table: 'epithets',
                      key: { mortal_entity_id: nodeId },
                      values: { epithet },
                      hold: true,
                    })
                  }
                />
                <Button
                  size='sm'
                  variant='ghost'
                  className='self-start'
                  disabled={blocked !== null}
                  disabledReason={blocked ?? undefined}
                  onClick={() =>
                    remove.mutate({
                      table: 'epithets',
                      key: { mortal_entity_id: nodeId },
                    })
                  }
                >
                  <Trash2 />
                  Take the epithet away
                </Button>
              </div>
            ) : (
              <TextEditor
                label='Give it an epithet'
                value=''
                blocked={blocked}
                onSave={(epithet) =>
                  create.mutate({
                    table: 'epithets',
                    values: {
                      mortal_entity_id: nodeId,
                      epithet,
                      gloss: '',
                      deed: '',
                      epoch: 0,
                    },
                  })
                }
              />
            )}
          </div>
        </div>
      )}
    </Section>
  )
}
