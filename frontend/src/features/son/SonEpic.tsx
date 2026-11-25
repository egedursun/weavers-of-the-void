import { BookOpen, Feather } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { EmptyState, Section } from '@/components/domain'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import { EpicView } from '@/features/pantheon/EpicView'
import { type SonRecord } from '@/features/pantheon/api'
import {
  paramEquals,
  useGodGate,
  useRunningJob,
} from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'

export function SonEpic({ son }: { son: SonRecord }) {
  const { reason } = useGodGate()
  const running = useRunningJob(
    (job) => job.kind === 'content' && paramEquals(job, 'son_id', son.id)
  )
  const write = useGodAction({
    writes: [{ lever: 'son:epic' }],
    run: () =>
      unwrap(
        api.POST('/api/sons/{son_id}/epic', {
          params: { path: { son_id: son.id } },
        })
      ),
    success: 'The bard is writing',
  })
  return (
    <Section
      id='section-son-epic'
      title='Epic'
      surface='card'
      level={3}
      actions={
        <ActionButton
          act={write}
          label={son.epic ? 'Rewrite epic' : 'Write epic'}
          icon={Feather}
          blocked={
            reason({ llm: true }) ??
            (running ? 'The bard is already writing.' : null)
          }
          pending={write.isPending}
          onRun={() => write.mutate()}
        />
      }
    >
      <ActionJob jobId={write.jobId} title='Epic' onDismiss={write.clearJob} />
      {son.epic ? (
        <EpicView epic={son.epic} />
      ) : (
        <EmptyState
          icon={BookOpen}
          size='compact'
          title="No bard has written this son's epic yet"
          description='The bard writes from their deeds, their worshippers and the chronicle.'
        />
      )}
    </Section>
  )
}
