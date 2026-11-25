import { useState } from 'react'
import { BookHeart, Eraser, PenLine, RefreshCw } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
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
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from './ActionButton'
import { type FolkView } from './api'
import { useGodGate } from './gate'
import { useGodAction } from './godAction'
import { usePeoples } from './peoples'

const VIEWS_SHOWN = 4

type Believed = { sonId: number | null; godId: number | null }

function RenameBelief({ view, god }: { view: FolkView; god: Believed }) {
  const { reason } = useGodGate()
  const rename = useGodAction({
    writes: [{ lever: 'belief:rename' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/belief:rename', {
          body: {
            people_id: view.people_id,
            son_id: god.sonId,
            ...(god.godId === null ? {} : { god_id: god.godId }),
          },
        })
      ),
  })
  return (
    <ActionButton
      act={rename}
      label='Derive the name anew'
      icon={RefreshCw}
      variant='ghost'
      size='sm'
      blocked={reason()}
      pending={rename.isPending}
      onRun={() => rename.mutate()}
    />
  )
}

function ForgetBelief({ view, god }: { view: FolkView; god: Believed }) {
  const { reason } = useGodGate()
  const forget = useGodAction({
    writes: [{ lever: 'belief:forget' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/belief:forget', {
          body: {
            people_id: view.people_id,
            son_id: god.sonId,
            ...(god.godId === null ? {} : { god_id: god.godId }),
          },
        })
      ),
    success: `${view.people_name} no longer tells that tale`,
  })
  return (
    <ActionButton
      act={forget}
      label='Make them forget'
      icon={Eraser}
      variant='ghost'
      size='sm'
      blocked={reason()}
      pending={forget.isPending}
      onRun={() => forget.mutate()}
    />
  )
}

function BeliefCard({ view, god }: { view: FolkView; god: Believed }) {
  return (
    <li className='flex min-w-0 flex-col gap-1.5 rounded-md border surface-framed border-gild/70 bg-card p-3'>
      <div className='flex min-w-0 flex-wrap items-baseline gap-x-2'>
        <EntityLink kind='entity' id={String(view.people_id)}>
          {view.people_name}
        </EntityLink>
        <Label>{`remembers this god so · Epoch ${view.epoch}`}</Label>
        <ForgetBelief view={view} god={god} />
      </div>
      {view.local_name && (
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Text variant='caption' italic>{`"${view.local_name}"`}</Text>
          <RenameBelief view={view} god={god} />
        </div>
      )}
      <ExpandableText lines={3}>{view.account}</ExpandableText>
      {view.misconception && (
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant='ghost' size='sm'>
              God's eye: the truth
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <Muted>{view.misconception}</Muted>
          </CollapsibleContent>
        </Collapsible>
      )}
    </li>
  )
}

type BeliefSectionProps = {
  views: FolkView[]
  sonId: number | null
  godId?: number | null
  godName: string
}

export function BeliefSection({
  views,
  sonId,
  godId = null,
  godName,
}: BeliefSectionProps) {
  const god = { sonId, godId }
  const [open, setOpen] = useState(false)
  const [peopleId, setPeopleId] = useState('')
  const [name, setName] = useState('')
  const [narrative, setNarrative] = useState('')
  const [misconception, setMisconception] = useState('')
  const peoples = usePeoples(open)
  const { reason } = useGodGate()
  const save = useGodAction({
    writes: [{ lever: 'belief:edit' }],
    run: () =>
      unwrap(
        api.PUT('/api/beliefs', {
          body: {
            people_id: Number(peopleId),
            son_id: sonId,
            ...(godId === null ? {} : { god_id: godId }),
            name: name.trim() || null,
            narrative: narrative.trim(),
            misconception: misconception.trim() || null,
          },
        })
      ),
    success: 'Account written to canon',
    onDone: () => {
      setName('')
      setNarrative('')
      setMisconception('')
    },
  })
  const list = peoples.data?.items ?? []
  const page = useShowMore(views, VIEWS_SHOWN)
  return (
    <Section
      id='section-god-belief'
      title="Through the peoples' eyes"
      level={3}
    >
      {views.length === 0 ? (
        <EmptyState
          icon={BookHeart}
          size='compact'
          title={`No people tells of ${godName} yet`}
          description='Peoples who worship write their own stories as epochs pass.'
        />
      ) : (
        <div className='flex min-w-0 flex-col gap-3'>
          <ul className='grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-2'>
            {page.visible.map((view) => (
              <BeliefCard
                key={`${view.people_id}-${view.epoch}`}
                view={view}
                god={god}
              />
            ))}
          </ul>
          <ShowMore state={page} noun={['account', 'accounts']} />
        </div>
      )}
      <Collapsible
        open={open}
        onOpenChange={setOpen}
        className='flex min-w-0 flex-col gap-3'
      >
        <CollapsibleTrigger asChild>
          <Button act={save} variant='ghost' size='sm' className='self-start'>
            <PenLine />
            Add or change a people's account
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
          {peoples.isSuccess && list.length === 0 ? (
            <Muted>
              There is no people in the world yet; when one is born you can
              write its account here.
            </Muted>
          ) : (
            <>
              <FormRow label='People'>
                {(id) => (
                  <Select value={peopleId} onValueChange={setPeopleId}>
                    <SelectTrigger id={id} className='w-full'>
                      <SelectValue placeholder='Pick a people' />
                    </SelectTrigger>
                    <SelectContent>
                      {list.map((people) => (
                        <SelectItem key={people.id} value={String(people.id)}>
                          {people.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </FormRow>
              <FormRow label='Name they gave this god'>
                {(id) => (
                  <Input
                    id={id}
                    value={name}
                    placeholder='The name in their own tongue'
                    onChange={(event) => setName(event.target.value)}
                  />
                )}
              </FormRow>
              <FormRow label='What they tell'>
                {(id) => (
                  <Textarea
                    id={id}
                    value={narrative}
                    onChange={(event) => setNarrative(event.target.value)}
                  />
                )}
              </FormRow>
              <FormRow
                label='What they got wrong'
                description='Only you see this.'
              >
                {(id) => (
                  <Textarea
                    id={id}
                    value={misconception}
                    onChange={(event) => setMisconception(event.target.value)}
                  />
                )}
              </FormRow>
              <div>
                <ActionButton
                  act={save}
                  label='Write into canon'
                  variant='default'
                  blocked={
                    reason() ??
                    (!peopleId
                      ? 'Pick a people first.'
                      : !narrative.trim()
                        ? 'Write what they tell.'
                        : null)
                  }
                  pending={save.isPending}
                  onRun={() => save.mutate()}
                />
              </div>
            </>
          )}
        </CollapsibleContent>
      </Collapsible>
    </Section>
  )
}
