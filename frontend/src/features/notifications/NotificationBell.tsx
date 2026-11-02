import { Link } from '@tanstack/react-router'
import { useEvent } from '@/realtime'
import { Bell, Trophy } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { useWorldState } from '@/features/overview/api'

const BADGE_CAP = 99

function unreadText(count: number): string {
  return count > BADGE_CAP ? `${BADGE_CAP}+` : String(count)
}

export function NotificationBell() {
  const state = useWorldState()
  const unread = state.data?.notifications_unread ?? 0
  useEvent('notification.created', (event) => {
    if (event.payload.category === 'achievement')
      toast.success(event.payload.title, {
        icon: <Trophy aria-hidden='true' className='size-icon-md' />,
        description: event.payload.body ?? undefined,
      })
    else if (event.payload.toast)
      toast(event.payload.title, {
        description: event.payload.body ?? event.payload.label,
      })
  })
  const label = unread > 0 ? `${unread} unread notifications` : 'Notifications'
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant='ghost' size={unread > 0 ? 'default' : 'icon'} asChild>
          <Link to='/notifications' aria-label={label}>
            <Bell />
            {unread > 0 && (
              <Badge size='sm' variant='default'>
                {unreadText(unread)}
              </Badge>
            )}
          </Link>
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}
