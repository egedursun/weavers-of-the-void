import { Link } from '@tanstack/react-router'
import { Compass } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ErrorScreen } from './ErrorScreen'

export function NotFoundError() {
  return (
    <ErrorScreen
      code='404'
      icon={Compass}
      title='This place is not on any map'
      description='The page you are looking for does not exist or was removed.'
      action={
        <Button asChild>
          <Link to='/overview'>Back to overview</Link>
        </Button>
      }
    />
  )
}
