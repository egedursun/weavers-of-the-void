import { Layers } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { EmptyState, Section } from '@/components/domain'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import { DepthView } from '@/features/pantheon/DepthView'
import {
  paramEquals,
  useGodGate,
  useRunningJob,
} from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type CreatorRecord } from './api'

export function CreatorDepth({ creator }: { creator: CreatorRecord }) {
  const { reason } = useGodGate()
  const running = useRunningJob((job) =>
    paramEquals(job, 'kind', 'creator_deepen')
  )
  const deepen = useGodAction({
    run: () => unwrap(api.POST('/api/creator/deepen')),
    success: 'Deepening the Creator',
  })
  return (
    <Section
      title='Depth'
      surface='card'
      level={3}
      actions={
        <ActionButton
          label={creator.depth ? 'Deepen again' : 'Deepen'}
          icon={Layers}
          blocked={
            reason({ llm: true }) ??
            (running ? 'Deepening is already under way.' : null)
          }
          pending={deepen.isPending}
          onRun={() => deepen.mutate()}
        />
      }
    >
      <ActionJob
        jobId={deepen.jobId}
        title='Deepening'
        onDismiss={deepen.clearJob}
      />
      {creator.depth ? (
        <DepthView depth={creator.depth} />
      ) : (
        <EmptyState
          icon={Layers}
          size='compact'
          title='The Creator is not deepened yet'
          description="The Creator's names, secrets, fears and prohibitions are not written."
        />
      )}
    </Section>
  )
}
