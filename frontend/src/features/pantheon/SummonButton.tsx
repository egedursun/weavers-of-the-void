import { useState } from 'react'
import { Crown } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { ActionButton } from './ActionButton'
import { ActionJob } from './ActionJob'
import { WorldChoice } from './WorldChoice'
import { FATE_CHOOSES, worldIdOf } from './fateChoice'
import { useGodGate, useRuleLookup, useRunningJob } from './gate'
import { useGodAction } from './godAction'

export function SummonButton({
  variant = 'default',
  size = 'default',
}: {
  variant?: 'default' | 'outline'
  size?: 'sm' | 'default'
}) {
  const [world, setWorld] = useState(FATE_CHOOSES)
  const rule = useRuleLookup()
  const cost = rule('costs.summon_son')
  const { reason } = useGodGate()
  const running = useRunningJob((job) => job.kind === 'summon')
  const summon = useGodAction({
    writes: [{ lever: 'summon_son' }],
    run: () =>
      unwrap(
        api.POST('/api/sons/summon', {
          body: { world_id: worldIdOf(world), inspiration: '' },
        })
      ),
    success: 'A son is answering your call',
  })
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <WorldChoice
          value={world}
          onChange={setWorld}
          label='World for the new son'
          size={size}
        />
        <ActionButton
          act={summon}
          label='Summon a son'
          icon={Crown}
          variant={variant}
          size={size}
          cost={cost}
          rule='costs.summon_son'
          blocked={
            reason({ cost, world: true, llm: true }) ??
            (running ? 'A son is already being summoned.' : null)
          }
          pending={summon.isPending}
          onRun={() => summon.mutate()}
        />
      </div>
      <ActionJob
        jobId={summon.jobId}
        title='Summoning'
        onDismiss={summon.clearJob}
      />
    </div>
  )
}
