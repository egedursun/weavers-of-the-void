import { useMemo, useState } from 'react'
import {
  EllipsisVertical,
  KeyRound,
  Search,
  UserMinus,
  UserPlus,
  UserRoundCheck,
  UserRoundX,
  UsersRound,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatSince } from '@/lib/format'
import { plural } from '@/lib/units'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ConfirmDialog,
  EmptyState,
  LoadingBlock,
  Medallion,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AccountAvatar } from '@/features/accounts/AccountAvatar'
import { TemporaryPassword } from '@/features/accounts/TemporaryPassword'
import { STATUS_LOOK } from '@/features/accounts/accountLook'
import { useSignedInAccount } from '@/features/accounts/api'
import { AddMemberDialog } from './AddMemberDialog'
import {
  useChangeMemberRole,
  useMembers,
  useRemoveMember,
  useResetMemberPassword,
  useSetMemberActive,
} from './api'
import { type Member, type Workspace, type WorkspaceRole } from './types'
import { WORKSPACE_ROLES, WORKSPACE_ROLE_LOOK } from './workspaceLook'

const MEMBERS_SHOWN = 12

type Pending =
  | { kind: 'remove' | 'deactivate'; member: Member }
  | { kind: 'reset'; member: Member }

type Issued = { member: Member; password: string }

function RoleCell({
  workspace,
  member,
  lastAdmin,
  manage,
}: {
  workspace: Workspace
  member: Member
  lastAdmin: boolean
  manage: boolean
}) {
  const change = useChangeMemberRole()
  const look = WORKSPACE_ROLE_LOOK[member.role]
  const Icon = look.icon
  if (!manage)
    return (
      <Badge variant='outline' size='sm'>
        <Icon />
        {look.label}
      </Badge>
    )
  const reason = lastAdmin
    ? 'The last administrator keeps the role; make someone else administrator first.'
    : change.isPending
      ? 'The role is being changed.'
      : null
  return (
    <Select
      act={change}
      value={member.role}
      disabled={reason !== null}
      onValueChange={(value) => {
        const role = WORKSPACE_ROLES.find((item) => item === value)
        if (!role || role === member.role) return
        change.mutate(
          { id: workspace.id, accountId: member.account.id, role },
          {
            onSuccess: () =>
              toast.success(
                `${member.account.display_name} is now ${WORKSPACE_ROLE_LOOK[role].label}`
              ),
            onError: (error) => toast.error(error.message),
          }
        )
      }}
    >
      <SelectTrigger
        size='sm'
        aria-label={`Role of ${member.account.display_name}`}
        title={reason ?? undefined}
        className='w-40'
      >
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {WORKSPACE_ROLES.map((role: WorkspaceRole) => {
          const RoleIcon = WORKSPACE_ROLE_LOOK[role].icon
          return (
            <SelectItem key={role} value={role}>
              <RoleIcon aria-hidden='true' />
              {WORKSPACE_ROLE_LOOK[role].label}
            </SelectItem>
          )
        })}
      </SelectContent>
    </Select>
  )
}

function MemberRow({
  workspace,
  member,
  you,
  lastAdmin,
  manage,
  onPending,
}: {
  workspace: Workspace
  member: Member
  you: boolean
  lastAdmin: boolean
  manage: boolean
  onPending: (pending: Pending) => void
}) {
  const { account } = member
  const status = STATUS_LOOK[account.status]
  const StatusIcon = status.icon
  const active = account.status === 'active'
  const selfReason = you
    ? 'Use "Leave the workspace" or your own account menu.'
    : null
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-3 rounded-md surface-sheen px-3 py-2.5'>
      <AccountAvatar
        name={account.display_name}
        tone={account.avatar_tone}
        size='md'
        dimmed={!active}
      />
      <div className='flex min-w-0 flex-1 basis-48 flex-col'>
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
          {`Joined ${formatSince(member.added_at)} · reaches ${plural(member.universe_count, 'universe')} · ${
            account.last_sign_in_at
              ? `last signed in ${formatSince(account.last_sign_in_at)}`
              : 'never signed in'
          }`}
        </Muted>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Badge variant={active ? 'success' : 'outline'} size='sm'>
          <StatusIcon />
          {status.label}
        </Badge>
        <RoleCell
          workspace={workspace}
          member={member}
          lastAdmin={lastAdmin}
          manage={manage}
        />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type='button'
              variant='ghost'
              size='icon-sm'
              aria-label={`Acts on ${account.display_name}`}
              disabled={!manage || selfReason !== null}
              disabledReason={
                selfReason ??
                'Only administrators of the workspace manage members.'
              }
            >
              <EllipsisVertical />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align='end' className='w-64'>
            <DropdownMenuItem
              onSelect={() => onPending({ kind: 'reset', member })}
            >
              <KeyRound />
              Reset the password
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => onPending({ kind: 'deactivate', member })}
            >
              {active ? <UserRoundX /> : <UserRoundCheck />}
              {active ? 'Deactivate the account' : 'Reactivate the account'}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant='destructive'
              disabled={lastAdmin}
              onSelect={() => onPending({ kind: 'remove', member })}
            >
              <UserMinus />
              Remove from the workspace
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </li>
  )
}

export function MembersPanel({ workspace }: { workspace: Workspace }) {
  const members = useMembers(workspace.id)
  const me = useSignedInAccount()
  const remove = useRemoveMember()
  const reset = useResetMemberPassword()
  const setActive = useSetMemberActive()
  const [adding, setAdding] = useState(false)
  const [query, setQuery] = useState('')
  const [pending, setPending] = useState<Pending | null>(null)
  const [issued, setIssued] = useState<Issued | null>(null)
  const manage = workspace.role === 'admin'
  const list = useMemo(() => members.data ?? [], [members.data])
  const admins = list.filter((member) => member.role === 'admin').length
  const needle = query.trim().toLowerCase()
  const shown = useMemo(
    () =>
      list.filter(
        (member) =>
          needle === '' ||
          [
            member.account.display_name,
            member.account.username,
            member.account.email,
          ]
            .join(' ')
            .toLowerCase()
            .includes(needle)
      ),
    [list, needle]
  )
  const page = useShowMore(shown, MEMBERS_SHOWN)
  const busy = remove.isPending || reset.isPending || setActive.isPending
  const target = pending?.member
  const confirm = () => {
    if (!pending) return
    const accountTarget = {
      id: workspace.id,
      accountId: pending.member.account.id,
    }
    const name = pending.member.account.display_name
    const done = (message: string) => ({
      onSuccess: () => {
        toast.success(message)
        setPending(null)
      },
      onError: (error: Error) => toast.error(error.message),
    })
    if (pending.kind === 'remove')
      remove.mutate(accountTarget, done(`${name} has left ${workspace.name}`))
    if (pending.kind === 'deactivate') {
      const active = pending.member.account.status === 'active'
      setActive.mutate(
        { ...accountTarget, active: !active },
        done(
          active ? `${name} can no longer sign in` : `${name} can sign in again`
        )
      )
    }
    if (pending.kind === 'reset')
      reset.mutate(accountTarget, {
        onSuccess: (result) => {
          setIssued({
            member: pending.member,
            password: result.temporary_password,
          })
          setPending(null)
        },
        onError: (error: Error) => toast.error(error.message),
      })
  }
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          leadingIcon={Search}
          aria-label='Search the members'
          placeholder='Search by name, username or e-mail'
          className='min-w-0 flex-1 basis-60'
        />
        <Button
          type='button'
          disabled={!manage}
          disabledReason='Only administrators of the workspace add members.'
          onClick={() => setAdding(true)}
        >
          <UserPlus />
          Add a member
        </Button>
      </div>
      {members.isPending ? (
        <LoadingBlock label='Reading the members' />
      ) : members.isError ? (
        <EmptyState
          size='compact'
          icon={UsersRound}
          title='The members could not be read'
          description={members.error.message}
          action={
            <Button
              type='button'
              variant='outline'
              onClick={() => void members.refetch()}
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
          description='Change the search to see every member.'
        />
      ) : (
        <>
          <ul aria-label='Members' className='flex min-w-0 flex-col gap-2'>
            {page.visible.map((member) => (
              <MemberRow
                key={member.account.id}
                workspace={workspace}
                member={member}
                you={me?.id === member.account.id}
                lastAdmin={member.role === 'admin' && admins <= 1}
                manage={manage}
                onPending={setPending}
              />
            ))}
          </ul>
          <ShowMore state={page} noun={['member', 'members']} />
        </>
      )}
      <AddMemberDialog
        workspace={workspace}
        open={adding}
        onClose={() => setAdding(false)}
      />
      <ConfirmDialog
        act={[remove, setActive, reset]}
        open={pending !== null}
        onOpenChange={(next) => {
          if (!next && !busy) setPending(null)
        }}
        destructive={pending?.kind !== 'reset'}
        title={
          !pending || !target
            ? 'Confirm'
            : pending.kind === 'remove'
              ? `Remove ${target.account.display_name}?`
              : pending.kind === 'reset'
                ? `Reset the password of ${target.account.display_name}?`
                : target.account.status === 'active'
                  ? `Deactivate ${target.account.display_name}?`
                  : `Reactivate ${target.account.display_name}?`
        }
        desc={
          !pending || !target
            ? ''
            : pending.kind === 'remove'
              ? `They lose access to every universe of ${workspace.name}. Everything they made stays, with their name on it.`
              : pending.kind === 'reset'
                ? 'They are signed out everywhere and get a temporary password, shown to you once, to replace at their next sign-in.'
                : target.account.status === 'active'
                  ? 'They are signed out at once and cannot sign in until reactivated. Their memberships and everything they made stay.'
                  : 'They can sign in again with their password and get back their memberships.'
        }
        confirmText={
          pending?.kind === 'remove'
            ? 'Remove'
            : pending?.kind === 'reset'
              ? 'Reset the password'
              : target?.account.status === 'active'
                ? 'Deactivate'
                : 'Reactivate'
        }
        isLoading={busy}
        handleConfirm={confirm}
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
              account={issued.member.account}
              password={issued.password}
              onDone={() => setIssued(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
