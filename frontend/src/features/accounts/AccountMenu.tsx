import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import {
  KeySquare,
  LogOut,
  Monitor,
  UserCog,
  UserRoundPen,
  UsersRound,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Muted, Text } from '@/components/typography'
import { AccountAvatar } from './AccountAvatar'
import { type AccountPanel, AccountDialog } from './AccountDialogs'
import { SERVER_ROLE_LOOK, managesAccounts } from './accountLook'
import { useSignOut, useSignedInAccount } from './api'

export function AccountMenu() {
  const account = useSignedInAccount()
  const signOut = useSignOut()
  const navigate = useNavigate()
  const [panel, setPanel] = useState<AccountPanel | null>(null)
  if (account === null) return null
  const role = SERVER_ROLE_LOOK[account.server_role]
  const RoleIcon = role.icon
  const canManage = managesAccounts(account.server_role)
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type='button'
            variant='ghost'
            size='icon'
            aria-label={`${account.display_name}: your account`}
          >
            <AccountAvatar
              name={account.display_name}
              tone={account.avatar_tone}
              size='xs'
            />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align='end' className='w-72'>
          <DropdownMenuLabel className='flex min-w-0 items-center gap-3'>
            <AccountAvatar
              name={account.display_name}
              tone={account.avatar_tone}
              size='md'
            />
            <span className='flex min-w-0 flex-1 flex-col'>
              <Text as='span' weight='semibold' truncate>
                {account.display_name}
              </Text>
              <Muted as='span' variant='caption' truncate className='font-mono'>
                {`@${account.username}`}
              </Muted>
              <span className='flex'>
                <Badge variant='outline' size='sm'>
                  <RoleIcon />
                  {role.label}
                </Badge>
              </span>
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem onSelect={() => setPanel('profile')}>
              <UserRoundPen />
              Your profile
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setPanel('password')}>
              <KeySquare />
              Change your password
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setPanel('sessions')}>
              <Monitor />
              Where you are signed in
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem
              onSelect={() =>
                void navigate({ to: '/workspace', search: { part: 'members' } })
              }
            >
              <UsersRound />
              Team and workspace
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={!canManage}
              title={
                canManage
                  ? undefined
                  : 'Only the server owner and server admins manage accounts.'
              }
              onSelect={() =>
                void navigate({
                  to: '/workspace',
                  search: { part: 'accounts' },
                })
              }
            >
              <UserCog />
              Server accounts
              {!canManage && (
                <Muted as='span' variant='caption' className='ms-auto'>
                  Admins only
                </Muted>
              )}
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            act={signOut}
            variant='destructive'
            disabled={signOut.isPending}
            onSelect={() => signOut.mutate()}
          >
            <LogOut />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <AccountDialog
        panel={panel}
        account={account}
        onClose={() => setPanel(null)}
      />
    </>
  )
}
