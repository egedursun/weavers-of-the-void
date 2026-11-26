import { Hourglass } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useRulesWait } from './api'

export function RulesWaitAlert() {
  const wait = useRulesWait()
  if (wait === null) return null
  return (
    <Alert>
      <Hourglass className='text-warning' />
      <AlertTitle>Saving waits for the epoch</AlertTitle>
      <AlertDescription>
        {`${wait} You can keep choosing; nothing is saved until you press Save after it ends.`}
      </AlertDescription>
    </Alert>
  )
}
