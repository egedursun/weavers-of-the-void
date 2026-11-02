import { useRouter } from '@tanstack/react-router'
import { TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorScreen } from './ErrorScreen'

export function GeneralError() {
  const router = useRouter()
  return (
    <ErrorScreen
      code='500'
      icon={TriangleAlert}
      title='Something went wrong'
      description='The screen failed to render. Reloading usually helps.'
      action={<Button onClick={() => router.invalidate()}>Try again</Button>}
    />
  )
}
