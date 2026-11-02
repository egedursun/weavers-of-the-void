import { useState } from 'react'
import { Users } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Muted } from '@/components/typography'
import { ActionButton } from './ActionButton'
import { ActionJob } from './ActionJob'
import { WorldChoice } from './WorldChoice'
import { FATE_CHOOSES, worldIdOf } from './fateChoice'
import { useCostText, useGodGate, useRuleLookup } from './gate'
import { useGodAction } from './godAction'

function defaultCount(schema: Record<string, unknown> | undefined): string {
  const properties = schema?.properties as
    Record<string, { default?: unknown }> | undefined
  const value = properties?.count?.default
  return typeof value === 'number' ? String(value) : '1'
}

export function AwakenPeoplesControl() {
  const catalogue = useCostText()
  const item = catalogue('awaken_peoples')
  const [count, setCount] = useState<string | null>(null)
  const [world, setWorld] = useState(FATE_CHOOSES)
  const rule = useRuleLookup()
  const perBatch = rule('balance.awaken_peoples')
  const batchCap = rule('awakening.batch_cap')
  const { reason } = useGodGate()
  const shown = count ?? defaultCount(item?.input_schema)
  const amount = Number(shown)
  const batches = batchCap ? Math.ceil(amount / batchCap) : 1
  const cost = perBatch !== undefined ? perBatch * batches : undefined
  const awaken = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/peoples/awaken', {
          body: { count: amount, world_id: worldIdOf(world) },
        })
      ),
    success: 'Peoples are awakening',
  })
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <FieldLabel htmlFor='awaken-count' className='sr-only'>
          Peoples to awaken
        </FieldLabel>
        <Input
          id='awaken-count'
          type='number'
          min={1}
          value={shown}
          className='w-24'
          onChange={(event) => setCount(event.target.value)}
        />
        <WorldChoice
          value={world}
          onChange={setWorld}
          label='World for the new peoples'
        />
        <ActionButton
          label='Awaken peoples'
          icon={Users}
          cost={cost}
          rule='balance.awaken_peoples'
          costText={item?.cost}
          blocked={
            reason({ cost, world: true, llm: true }) ??
            (amount >= 1 && Number.isInteger(amount)
              ? null
              : 'Choose how many.')
          }
          pending={awaken.isPending}
          onRun={() => awaken.mutate()}
        />
      </div>
      <Muted variant='caption'>
        {`New peoples wake on empty lands, each with a language, settlement, resource, knowledge, tradition and faith.${batchCap ? ` Every ${batchCap} peoples are one batch, paid per batch.` : ''}`}
      </Muted>
      <ActionJob
        jobId={awaken.jobId}
        title='Awakening'
        onDismiss={awaken.clearJob}
      />
    </div>
  )
}
