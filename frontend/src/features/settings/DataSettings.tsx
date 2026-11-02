import { Skeleton } from '@/components/ui/skeleton'
import { Text } from '@/components/typography'
import { BackupsPanel } from '@/features/backups/BackupsPanel'
import { ShareWorld } from '@/features/backups/ShareWorld'
import { useWorldState } from '@/features/overview/api'
import { HealthPanel } from './HealthPanel'
import { ResetWorld } from './ResetWorld'

export function DataSettings() {
  const state = useWorldState()
  if (state.isPending) return <Skeleton className='h-48 w-full' />
  if (state.isError)
    return <Text tone='destructive'>{state.error.message}</Text>
  const hasWorld = state.data.world !== null
  const readOnly = state.data.read_only
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <ShareWorld hasWorld={hasWorld} readOnly={readOnly} />
      <BackupsPanel readOnly={readOnly} />
      <HealthPanel />
      <ResetWorld hasWorld={hasWorld} readOnly={readOnly} />
    </div>
  )
}
