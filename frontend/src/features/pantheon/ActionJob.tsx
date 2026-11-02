import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { queryKeys } from '@/api/queryKeys'
import { fetchJob } from '@/api/system'
import { Button } from '@/components/ui/button'
import { JobProgress } from '@/components/domain'

type ActionJobProps = {
  jobId: string | null
  title?: string
  onDismiss: () => void
}

export function ActionJob({ jobId, title, onDismiss }: ActionJobProps) {
  const job = useQuery({
    queryKey: queryKeys.jobs.detail(jobId ?? ''),
    queryFn: () => fetchJob(jobId ?? ''),
    enabled: jobId !== null,
  })
  if (jobId === null || !job.data) return null
  return (
    <JobProgress
      job={job.data}
      title={title}
      action={
        <Button
          variant='ghost'
          size='icon-sm'
          aria-label='Dismiss progress'
          onClick={onDismiss}
        >
          <X />
        </Button>
      }
    />
  )
}
