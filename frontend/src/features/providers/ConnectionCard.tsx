import {
  CircleCheck,
  CloudCog,
  EllipsisVertical,
  Globe,
  KeyRound,
  LogIn,
  LogOut,
  PenLine,
  Trash2,
  TriangleAlert,
} from 'lucide-react'
import { formatSince } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { FAMILY_LOOK } from './providerLook'
import { type ProviderConnection, type ProviderKindView } from './types'

export type ConnectionAct =
  'rename' | 'key' | 'address' | 'login' | 'logout' | 'remove'

function status(connection: ProviderConnection, subscription: boolean) {
  if (subscription && connection.logged_in_at === null)
    return { ready: false, text: 'Not logged in' }
  if (connection.unusable !== null)
    return { ready: false, text: connection.unusable }
  if (subscription && connection.logged_in_at)
    return {
      ready: true,
      text: `Logged in ${formatSince(connection.logged_in_at)}`,
    }
  return { ready: true, text: 'Ready' }
}

export function ConnectionCard({
  connection,
  kind,
  editable,
  readOnlyReason,
  canLogIn,
  onAct,
}: {
  connection: ProviderConnection
  kind: ProviderKindView
  editable: boolean
  readOnlyReason: string
  canLogIn: boolean
  onAct: (act: ConnectionAct) => void
}) {
  const look = FAMILY_LOOK[kind.family]
  const subscription = kind.family === 'subscription'
  const shown = status(connection, subscription)
  const locked = !editable || connection.from_server
  const lockReason = connection.from_server
    ? 'It belongs to the server default; change it there.'
    : readOnlyReason
  return (
    <li className='flex min-w-0 flex-col gap-2 rounded-md surface-sheen px-3 py-2.5'>
      <div className='flex min-w-0 flex-wrap items-center gap-3'>
        <Medallion icon={look.icon} tone={look.tone} size='sm' />
        <div className='flex min-w-0 flex-1 basis-48 flex-col'>
          <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
            <Text as='span' weight='semibold' truncate>
              {connection.label}
            </Text>
            {connection.label !== kind.label && (
              <Badge variant='outline' size='sm'>
                {kind.label}
              </Badge>
            )}
            {connection.from_server && (
              <Badge variant='info' size='sm'>
                <CloudCog />
                From the server
              </Badge>
            )}
          </span>
          <Muted as='span' variant='caption' truncate={2}>
            {[
              connection.secret_hint !== ''
                ? `Key ending in ${connection.secret_hint}`
                : null,
              connection.base_url !== '' ? connection.base_url : null,
              `Added ${formatSince(connection.created_at)}`,
            ]
              .filter((part) => part !== null)
              .join(' · ')}
          </Muted>
        </div>
        <Badge variant={shown.ready ? 'success' : 'warning'} size='sm'>
          {shown.ready ? <CircleCheck /> : <TriangleAlert />}
          {shown.text}
        </Badge>
        {subscription && canLogIn && !connection.logged_in_at && (
          <Button
            type='button'
            size='sm'
            disabled={locked}
            disabledReason={lockReason}
            onClick={() => onAct('login')}
          >
            <LogIn />
            Log in
          </Button>
        )}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type='button'
              variant='ghost'
              size='icon-sm'
              aria-label={`Acts on ${connection.label}`}
              disabled={locked}
              disabledReason={lockReason}
            >
              <EllipsisVertical />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align='end' className='w-64'>
            {subscription && canLogIn && connection.logged_in_at && (
              <DropdownMenuItem onSelect={() => onAct('login')}>
                <LogIn />
                Log in again
              </DropdownMenuItem>
            )}
            {subscription && canLogIn && connection.logged_in_at && (
              <DropdownMenuItem onSelect={() => onAct('logout')}>
                <LogOut />
                Log out
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onSelect={() => onAct('rename')}>
              <PenLine />
              Rename
            </DropdownMenuItem>
            {kind.asks_key && !subscription && (
              <DropdownMenuItem onSelect={() => onAct('key')}>
                <KeyRound />
                Replace the key
              </DropdownMenuItem>
            )}
            {kind.asks_address && (
              <DropdownMenuItem onSelect={() => onAct('address')}>
                <Globe />
                Change the address
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant='destructive'
              onSelect={() => onAct('remove')}
            >
              <Trash2 />
              Remove
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {kind.terms !== null && (
        <Muted
          as='span'
          variant='caption'
          className='flex min-w-0 items-center gap-1.5'
        >
          <TriangleAlert
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-warning'
          />
          {kind.terms}
        </Muted>
      )}
    </li>
  )
}
