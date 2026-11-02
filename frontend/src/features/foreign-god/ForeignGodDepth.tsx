import { Layers } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { EmptyState, Section } from '@/components/domain'
import { Muted } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import { DepthView } from '@/features/pantheon/DepthView'
import {
  paramEquals,
  useGodGate,
  useRunningJob,
} from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { type ForeignGodRecord } from './api'

export function ForeignGodDepth({ god }: { god: ForeignGodRecord }) {
  const { reason } = useGodGate()
  const running = useRunningJob((job) => paramEquals(job, 'god_id', god.id))
  const deepen = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/foreign-gods/{god_id}/deepen', {
          params: { path: { god_id: god.id } },
        })
      ),
    success: 'Deepening',
  })
  return (
    <Section
      title='Depth'
      surface='card'
      level={3}
      actions={
        <ActionButton
          label={god.depth ? 'Deepen again' : 'Deepen'}
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
      {god.depth ? (
        <DepthView depth={god.depth} />
      ) : (
        <EmptyState
          icon={Layers}
          size='compact'
          title='Not deepened yet'
          description='Deepening writes personality, existence, powers and depth; it also happens by itself at epoch end.'
        />
      )}
      <Muted variant='caption'>
        Personality and existence fields and powers you wrote by hand are kept;
        empty ones are filled and the depth is rewritten.
      </Muted>
    </Section>
  )
}
