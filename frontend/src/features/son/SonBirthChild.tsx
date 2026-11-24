import { useState } from 'react'
import { Baby } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, Section } from '@/components/domain'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import { type SonRecord } from '@/features/pantheon/api'
import {
  paramEquals,
  useGodGate,
  useRuleLookup,
  useRunningJob,
} from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type SonDetail } from './api'

const ALONE = 'alone'
const INSPIRATION_RULE = 'god_actions.inspiration_max_chars'

export function SonBirthChild({
  son,
  siblings,
}: {
  son: SonRecord
  siblings: SonDetail['siblings']
}) {
  const [partner, setPartner] = useState(ALONE)
  const [inspiration, setInspiration] = useState('')
  const { reason } = useGodGate()
  const rule = useRuleLookup()
  const running = useRunningJob(
    (job) => job.kind === 'summon' && paramEquals(job, 'son_id', son.id)
  )
  const birth = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/son:birth_child', {
          body: {
            son_id: son.id,
            inspiration: inspiration.trim(),
            co_parent_id: partner === ALONE ? null : Number(partner),
          },
        })
      ),
    success: `${son.name} is bearing a child`,
    onDone: () => setInspiration(''),
  })
  return (
    <Section
      id='section-son-child'
      title='Bear a child'
      description='Fate rolls the child below their own class; the lowest class bears at the floor.'
      level={3}
    >
      <FormRow label='Other parent' description='Optional; another living son'>
        {(id) => (
          <Select value={partner} onValueChange={setPartner}>
            <SelectTrigger id={id} className='w-full sm:w-72'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALONE}>{`${son.name} alone`}</SelectItem>
              {siblings.map((sibling) => (
                <SelectItem key={sibling.son.id} value={String(sibling.son.id)}>
                  {sibling.son.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow
        label='Inspiration'
        description='Optional; what the child should carry'
      >
        {(id) => (
          <Textarea
            id={id}
            maxLength={rule(INSPIRATION_RULE)}
            value={inspiration}
            onChange={(event) => setInspiration(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <ActionButton
          label='Bear a child'
          icon={Baby}
          variant='default'
          blocked={
            reason({ world: true, llm: true }) ??
            (running ? 'A birth is already under way.' : null)
          }
          pending={birth.isPending}
          confirm={{
            title: `Let ${son.name} bear a child?`,
            description:
              'A new son joins the pantheon. The language model writes them; watch the progress here.',
          }}
          onRun={() => birth.mutate()}
        />
      </div>
      <ActionJob
        jobId={birth.jobId}
        title={`${son.name}'s child`}
        onDismiss={birth.clearJob}
      />
    </Section>
  )
}
