import { ScrollText } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

type PastEpochBannerProps = {
  epoch: number
  snapshot: boolean
  onToday: () => void
}

export function PastEpochBanner({
  epoch,
  snapshot,
  onToday,
}: PastEpochBannerProps) {
  return (
    <Alert data-map-past>
      <ScrollText />
      <AlertTitle>{`The world in Epoch ${epoch}`}</AlertTitle>
      <AlertDescription className='flex min-w-0 flex-wrap items-center gap-3'>
        <span className='min-w-0 flex-1'>
          {snapshot
            ? "Photo taken at that epoch's end: the living and their populations."
            : 'No photo for that epoch; showing those born up to then.'}
        </span>
        <Button size='sm' onClick={onToday}>
          Back to today
        </Button>
      </AlertDescription>
    </Alert>
  )
}
