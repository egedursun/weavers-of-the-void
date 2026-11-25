import { useMemo, useState } from 'react'
import {
  Crown,
  EllipsisVertical,
  KeyRound,
  Lock,
  Search,
  ShieldCheck,
  Trash2,
  UserPlus,
  UserRoundCheck,
  UserRoundX,
  UsersRound,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime, formatInteger, formatSince } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import {
  ConfirmDialog,
  EmptyState,
  KpiTile,
  LoadingBlock,
  Medallion,
  Section,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AccountAvatar } from './AccountAvatar'
import { CreateAccountDialog } from './CreateAccountDialog'
import { TemporaryPassword } from './TemporaryPassword'
import { SERVER_ROLE_LOOK, STATUS_LOOK, managesAccounts } from './accountLook'
import {
  useAccounts,
  useDeleteAccount,
  useEditAccount,
  useResetAccountPassword,
  useSignedInAccount,
  useTransferOwnership,
} from './api'
import { type Account } from './types'

const ACCOUNTS_SHOWN = 15

function lockedUntil(account: Account): boolean {
  return (
    account.locked_until !== null &&
    Date.parse(account.locked_until) > Date.now()
  )
}

type Act = 'reset' | 'active' | 'delete' | 'admin' | 'owner'

type Pending = { act: Act; account: Account }

function AccountRow({
  account,
  me,
  onAct,
}: {
  account: Account
  me: Account
  onAct: (pending: Pending) => void
}) {
  const role = SERVER_ROLE_LOOK[account.server_role]
  const RoleIcon = role.icon
  const status = STATUS_LOOK[account.status]
  const StatusIcon = status.icon
  const you = account.id === me.id
  const owner = account.server_role === 'owner'
  const active = account.status === 'active'
  const iAmOwner = me.server_role === 'owner'
  const fixed = you
    ? 'Manage your own account from your account menu.'
    : owner
      ? 'The owner cannot be changed here; the owner hands ownership on.'
      : null
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-3 rounded-md surface-sheen px-3 py-2.5'>
      <AccountAvatar
        name={account.display_name}
        tone={account.avatar_tone}
        size='md'
        dimmed={!active}
      />
      <div className='flex min-w-0 flex-1 basis-56 flex-col'>
        <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Text as='span' weight='semibold' truncate>
            {account.display_name}
          </Text>
          {you && (
            <Badge variant='secondary' size='sm'>
              You
            </Badge>
          )}
          {account.must_change_password && (
            <Badge variant='warning' size='sm'>
              <KeyRound />
              Must set their own password
            </Badge>
          )}
        </span>
        <Muted as='span' variant='caption' truncate>
          <span className='font-mono'>{`@${account.username}`}</span>
          {` · ${account.email}`}
        </Muted>
        <Muted as='span' variant='caption' truncate>
          {`Joined ${formatDateTime(account.created_at)} · ${
            account.last_sign_in_at
              ? `last signed in ${formatSince(account.last_sign_in_at)}`
              : 'never signed in'
          }`}
        </Muted>
      </div>
      <span className='flex min-w-0 flex-wrap items-center gap-2'>
        {lockedUntil(account) && (
          <Badge
            variant='destructive'
            size='sm'
            title='Too many wrong passwords; the lock lifts by itself.'
          >
            <Lock />
            {`Locked until ${formatDateTime(account.locked_until ?? '')}`}
          </Badge>
        )}
        <Badge variant='outline' size='sm' title={role.meaning}>
          <RoleIcon />
          {role.label}
        </Badge>
        <Badge variant={active ? 'success' : 'outline'} size='sm'>
          <StatusIcon />
          {status.label}
        </Badge>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type='button'
              variant='ghost'
              size='icon-sm'
              aria-label={`Acts on ${account.display_name}`}
              disabled={fixed !== null}
              disabledReason={fixed ?? ''}
            >
              <EllipsisVertical />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align='end' className='w-64'>
            <DropdownMenuItem onSelect={() => onAct({ act: 'reset', account })}>
              <KeyRound />
              Reset the password
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => onAct({ act: 'active', account })}
            >
              {active ? <UserRoundX /> : <UserRoundCheck />}
              {active ? 'Deactivate' : 'Reactivate'}
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={!iAmOwner}
              onSelect={() => onAct({ act: 'admin', account })}
            >
              <ShieldCheck />
              {account.server_role === 'admin'
                ? 'Take back server admin'
                : 'Make server admin'}
              {!iAmOwner && (
                <Muted as='span' variant='caption' className='ms-auto'>
                  Owner only
                </Muted>
              )}
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={!iAmOwner || account.server_role !== 'admin' || !active}
              onSelect={() => onAct({ act: 'owner', account })}
            >
              <Crown />
              Hand ownership to them
              {(!iAmOwner || account.server_role !== 'admin') && (
                <Muted as='span' variant='caption' className='ms-auto'>
                  {iAmOwner ? 'Admins only' : 'Owner only'}
                </Muted>
              )}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant='destructive'
              onSelect={() => onAct({ act: 'delete', account })}
            >
              <Trash2 />
              Delete the account
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </span>
    </li>
  )
}

function confirmCopy(pending: Pending): {
  title: string
  desc: string
  confirm: string
  destructive: boolean
} {
  const name = pending.account.display_name
  const active = pending.account.status === 'active'
  switch (pending.act) {
    case 'reset':
      return {
        title: `Reset the password of ${name}?`,
        desc: 'They are signed out everywhere and get a temporary password, shown to you once, to replace at their next sign-in.',
        confirm: 'Reset the password',
        destructive: false,
      }
    case 'active':
      return active
        ? {
            title: `Deactivate ${name}?`,
            desc: 'They are signed out at once and cannot sign in until reactivated. Their memberships and everything they made stay.',
            confirm: 'Deactivate',
            destructive: true,
          }
        : {
            title: `Reactivate ${name}?`,
            desc: 'They can sign in again with their password and get back their memberships.',
            confirm: 'Reactivate',
            destructive: false,
          }
    case 'admin':
      return pending.account.server_role === 'admin'
        ? {
            title: `Take back server admin from ${name}?`,
            desc: 'They stay a member of their workspaces but no longer manage accounts.',
            confirm: 'Take it back',
            destructive: true,
          }
        : {
            title: `Make ${name} a server admin?`,
            desc: 'They can create, reset, deactivate and delete accounts on this server.',
            confirm: 'Make server admin',
            destructive: false,
          }
    case 'owner':
      return {
        title: `Hand ownership of the server to ${name}?`,
        desc: 'They become the owner and you become a server admin. Only the new owner can hand it back.',
        confirm: 'Hand ownership over',
        destructive: true,
      }
    case 'delete':
      return {
        title: `Delete the account of ${name}?`,
        desc: `${name} can no longer sign in and leaves every workspace. Everything they made stays, shown under their name as a former member. This cannot be undone.`,
        confirm: `Delete ${name}`,
        destructive: true,
      }
  }
}

export function ServerAccountsPanel() {
  const me = useSignedInAccount()
  const allowed = me !== null && managesAccounts(me.server_role)
  const accounts = useAccounts(allowed)
  const edit = useEditAccount()
  const reset = useResetAccountPassword()
  const remove = useDeleteAccount()
  const transfer = useTransferOwnership()
  const [creating, setCreating] = useState(false)
  const [query, setQuery] = useState('')
  const [pending, setPending] = useState<Pending | null>(null)
  const [issued, setIssued] = useState<{
    account: Account
    password: string
  } | null>(null)
  const list = useMemo(() => accounts.data ?? [], [accounts.data])
  const needle = query.trim().toLowerCase()
  const shown = useMemo(
    () =>
      list.filter(
        (account) =>
          needle === '' ||
          [account.display_name, account.username, account.email]
            .join(' ')
            .toLowerCase()
            .includes(needle)
      ),
    [list, needle]
  )
  const page = useShowMore(shown, ACCOUNTS_SHOWN)
  const busy =
    edit.isPending || reset.isPending || remove.isPending || transfer.isPending
  const copy = pending ? confirmCopy(pending) : null
  const run = () => {
    if (!pending) return
    const { account, act } = pending
    const done = (message: string) => ({
      onSuccess: () => {
        toast.success(message)
        setPending(null)
      },
      onError: (error: Error) => toast.error(error.message),
    })
    if (act === 'reset')
      reset.mutate(account.id, {
        onSuccess: (result) => {
          setIssued({ account, password: result.temporary_password })
          setPending(null)
        },
        onError: (error: Error) => toast.error(error.message),
      })
    if (act === 'active')
      edit.mutate(
        {
          id: account.id,
          status: account.status === 'active' ? 'deactivated' : 'active',
        },
        done(
          account.status === 'active'
            ? `${account.display_name} can no longer sign in`
            : `${account.display_name} can sign in again`
        )
      )
    if (act === 'admin')
      edit.mutate(
        {
          id: account.id,
          server_role: account.server_role === 'admin' ? 'member' : 'admin',
        },
        done(
          `${account.display_name} is now ${account.server_role === 'admin' ? 'a member' : 'a server admin'}`
        )
      )
    if (act === 'owner')
      transfer.mutate(
        account.id,
        done(`${account.display_name} owns the server now`)
      )
    if (act === 'delete')
      remove.mutate(
        account.id,
        done(`The account of ${account.display_name} is deleted`)
      )
  }
  const counts = {
    active: list.filter((account) => account.status === 'active').length,
    admins: list.filter((account) => account.server_role !== 'member').length,
    waiting: list.filter((account) => account.must_change_password).length,
  }
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      {!allowed ? (
        <EmptyState
          icon={ShieldCheck}
          title='Only server admins manage accounts'
          description='Ask the owner of the server or a server admin. Members of a workspace are managed under Members and roles in the workspace menu.'
        />
      ) : (
        <>
          <div
            role='group'
            aria-label='Accounts at a glance'
            className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'
          >
            <KpiTile
              label='Accounts'
              value={accounts.isSuccess ? formatInteger(list.length) : '…'}
              icon={UsersRound}
            />
            <KpiTile
              label='Active'
              value={accounts.isSuccess ? formatInteger(counts.active) : '…'}
              icon={UserRoundCheck}
              tone='success'
            />
            <KpiTile
              label='Owner and admins'
              value={accounts.isSuccess ? formatInteger(counts.admins) : '…'}
              icon={ShieldCheck}
              tone='info'
            />
            <KpiTile
              label='Must set their own password'
              value={accounts.isSuccess ? formatInteger(counts.waiting) : '…'}
              icon={KeyRound}
              tone='warning'
            />
          </div>
          <Section title='Every account' icon={UsersRound} surface='card'>
            <div className='flex min-w-0 flex-wrap items-center gap-2'>
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                leadingIcon={Search}
                aria-label='Search the accounts'
                placeholder='Search by name, username or e-mail'
                className='min-w-0 flex-1 basis-60'
              />
              <Button type='button' onClick={() => setCreating(true)}>
                <UserPlus />
                Make an account
              </Button>
            </div>
            {accounts.isPending ? (
              <LoadingBlock label='Reading the accounts' />
            ) : accounts.isError ? (
              <EmptyState
                size='compact'
                icon={UsersRound}
                title='The accounts could not be read'
                description={accounts.error.message}
                action={
                  <Button
                    type='button'
                    variant='outline'
                    onClick={() => void accounts.refetch()}
                  >
                    Try again
                  </Button>
                }
              />
            ) : page.total === 0 ? (
              <EmptyState
                size='compact'
                icon={Search}
                title='Nobody matches'
                description='Change the search to see every account.'
              />
            ) : (
              <>
                <ul
                  aria-label='Accounts'
                  className='flex min-w-0 flex-col gap-2'
                >
                  {page.visible.map((account) => (
                    <AccountRow
                      key={account.id}
                      account={account}
                      me={me}
                      onAct={setPending}
                    />
                  ))}
                </ul>
                <ShowMore state={page} noun={['account', 'accounts']} />
              </>
            )}
          </Section>
        </>
      )}
      <CreateAccountDialog open={creating} onClose={() => setCreating(false)} />
      <ConfirmDialog
        act={[reset, edit, transfer, remove]}
        open={pending !== null}
        onOpenChange={(next) => {
          if (!next && !busy) setPending(null)
        }}
        destructive={copy?.destructive ?? false}
        title={copy?.title ?? 'Confirm'}
        desc={copy?.desc ?? ''}
        confirmText={copy?.confirm ?? 'Confirm'}
        isLoading={busy}
        handleConfirm={run}
      />
      <Dialog
        open={issued !== null}
        onOpenChange={(next) => {
          if (!next) setIssued(null)
        }}
      >
        <DialogContent className='sm:max-w-lg'>
          <DialogHeader>
            <div className='flex min-w-0 items-center gap-3'>
              <Medallion icon={KeyRound} />
              <DialogTitle>A new temporary password</DialogTitle>
            </div>
            <DialogDescription>
              The old password no longer works. Copy this one now; it is never
              shown again.
            </DialogDescription>
          </DialogHeader>
          {issued && (
            <TemporaryPassword
              account={issued.account}
              password={issued.password}
              onDone={() => setIssued(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
