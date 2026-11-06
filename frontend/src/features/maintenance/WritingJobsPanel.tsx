import { useState } from 'react'
import { type UseMutationResult } from '@tanstack/react-query'
import { Feather, PenLine, ScrollText, Sparkles } from 'lucide-react'
import { Section } from '@/components/domain'
import { Text } from '@/components/typography'
import { NamePicker } from '@/features/pantheon/NamePicker'
import { useGodGate } from '@/features/pantheon/gate'
import { JobRunRow } from './JobRunRow'
import {
  type JobAccepted,
  useMissingContent,
  useWriteCosmosPrompts,
  useWriteMissingChronicles,
  useWriteSonPowers,
} from './api'

type Job<TVariables> = UseMutationResult<JobAccepted, Error, TVariables>

function useJobSlot<TVariables>(mutation: Job<TVariables>) {
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const start = (variables: TVariables) => {
    setError(null)
    mutation.mutate(variables, {
      onSuccess: (accepted) => setJobId(accepted.job_id),
      onError: (failure) => setError(failure.message),
    })
  }
  return {
    jobId,
    error,
    pending: mutation.isPending,
    start,
    dismiss: () => setJobId(null),
  }
}

export function WritingJobsPanel() {
  const { reason } = useGodGate()
  const missing = useMissingContent()
  const powers = useJobSlot(useWriteSonPowers())
  const cosmos = useJobSlot(useWriteCosmosPrompts())
  const chronicles = useJobSlot(useWriteMissingChronicles())
  const [picked, setPicked] = useState<string | null>(null)
  const suggested = missing.data?.son_powers[0]
  const sonId = picked ?? (suggested !== undefined ? String(suggested) : null)
  const modelReason = reason({ llm: true })
  return (
    <Section
      title='Writing jobs'
      description='Ask the model to write what is missing in one place. Each runs in the background and shows its progress here.'
      surface='card'
      level={3}
      icon={PenLine}
      tone='verdigris'
    >
      {modelReason && (
        <Text variant='caption' tone='warning'>
          {modelReason}
        </Text>
      )}
      <ul className='flex min-w-0 flex-col gap-2'>
        <JobRunRow
          id='son-powers'
          title="Write a son's powers"
          description='Writes or rewrites the powers of one son from their rarity, domains and deeds.'
          note={
            missing.data && missing.data.son_powers.length > 0
              ? `${missing.data.son_powers.length} son${missing.data.son_powers.length === 1 ? ' has' : 's have'} no powers yet.`
              : undefined
          }
          control={
            <div className='min-w-0 flex-1 basis-60'>
              <NamePicker
                value={sonId}
                onChange={setPicked}
                kinds={['son']}
                placeholder='Pick a son'
              />
            </div>
          }
          label='Write powers'
          icon={Sparkles}
          blocked={modelReason ?? (sonId === null ? 'Pick a son first.' : null)}
          pending={powers.pending}
          error={powers.error}
          jobId={powers.jobId}
          onRun={() => sonId !== null && powers.start(Number(sonId))}
          onDismiss={powers.dismiss}
        />
        <JobRunRow
          id='cosmos-prompts'
          title='Write cosmos image prompts'
          description='Writes the missing image prompts of stars, worlds and the cosmos itself.'
          label='Write prompts'
          icon={Feather}
          blocked={modelReason}
          pending={cosmos.pending}
          error={cosmos.error}
          jobId={cosmos.jobId}
          onRun={() => cosmos.start(undefined)}
          onDismiss={cosmos.dismiss}
        />
        <JobRunRow
          id='chronicles'
          title='Write missing chronicles'
          description='Writes the narrative of every past epoch that closed without one.'
          note={
            missing.data && missing.data.past_narratives.length > 0
              ? `Epochs without a narrative: ${missing.data.past_narratives.join(', ')}.`
              : undefined
          }
          label='Write chronicles'
          icon={ScrollText}
          blocked={modelReason}
          pending={chronicles.pending}
          error={chronicles.error}
          jobId={chronicles.jobId}
          onRun={() => chronicles.start(undefined)}
          onDismiss={chronicles.dismiss}
        />
      </ul>
    </Section>
  )
}
