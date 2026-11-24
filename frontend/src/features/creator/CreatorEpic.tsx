import { BookOpen, Feather } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { EmptyState, Section } from '@/components/domain'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import { EpicView } from '@/features/pantheon/EpicView'
import {
  paramEquals,
  useGodGate,
  useRunningJob,
} from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type CreatorRecord } from './api'

export function CreatorEpic({ creator }: { creator: CreatorRecord }) {
  const { reason } = useGodGate()
  const running = useRunningJob((job) =>
    paramEquals(job, 'kind', 'creator_epic')
  )
  const write = useGodAction({
    run: () => unwrap(api.POST('/api/creator/epic')),
    success: "The bard is writing the Creator's epic",
  })
  return (
    <Section
      id='section-creator-epic'
      title='Epic'
      surface='card'
      level={3}
      actions={
        <ActionButton
          label={creator.epic ? 'Rewrite the epic' : 'Write the epic'}
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
      {creator.epic ? (
        <EpicView epic={creator.epic} />
      ) : (
        <EmptyState
          icon={BookOpen}
          size='compact'
          title="No bard has written the Creator's epic"
          description="It is born from the Creator's traces, the sons and the peoples' tales."
        />
      )}
    </Section>
  )
}
