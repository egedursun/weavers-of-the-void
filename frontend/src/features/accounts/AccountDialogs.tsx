import { type FormEvent, useState } from 'react'
import {
  CalendarDays,
  KeySquare,
  LoaderCircle,
  LogOut,
  Monitor,
  MonitorX,
  Save,
  UserRoundPen,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime, formatSince } from '@/lib/format'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  EmptyState,
  FormRow,
  LoadingBlock,
  Medallion,
  MiniStat,
  PagedList,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { NewPasswordFields } from './NewPasswordFields'
import { PasswordField } from './PasswordField'
import { TonePicker } from './TonePicker'
import {
  DISPLAY_NAME_MAX,
  EMAIL_MAX,
  displayNameProblem,
  emailProblem,
  firstProblem,
} from './accountRules'
import {
  useChangePassword,
  useEditProfile,
  useEndOtherSessions,
  useEndSession,
  usePasswordMin,
  useSessions,
} from './api'
import { emailName, passwordChecks } from './passwordRules'
import { type Account, type AvatarTone, type SessionView } from './types'

export type AccountPanel = 'profile' | 'password' | 'sessions'

const SESSIONS_SHOWN = 6

function PanelHeader({
  icon,
  title,
  lead,
}: {
  icon: typeof Save
  title: string
  lead: string
}) {
  return (
    <DialogHeader>
      <div className='flex min-w-0 items-center gap-3'>
        <Medallion icon={icon} />
        <DialogTitle>{title}</DialogTitle>
      </div>
      <DialogDescription>{lead}</DialogDescription>
    </DialogHeader>
  )
}

function ProfilePanel({
  account,
  onClose,
}: {
  account: Account
  onClose: () => void
}) {
  const edit = useEditProfile()
  const [displayName, setDisplayName] = useState(account.display_name)
  const [email, setEmail] = useState(account.email)
  const [tone, setTone] = useState<AvatarTone>(account.avatar_tone)
  const unchanged =
    displayName.trim() === account.display_name &&
    email.trim() === account.email &&
    tone === account.avatar_tone
  const problem = firstProblem(
    displayNameProblem(displayName),
    emailProblem(email)
  )
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (problem !== null || unchanged) return
    edit.mutate(
      {
        display_name: displayName.trim(),
        email: email.trim(),
        avatar_tone: tone,
      },
      {
        onSuccess: () => {
          toast.success('Your profile is saved')
          onClose()
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  return (
    <form className='flex min-w-0 flex-col gap-4' onSubmit={submit}>
      <PanelHeader
        icon={UserRoundPen}
        title='Your profile'
        lead='Your name and face as the team sees them on every act you take.'
      />
      <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
        <MiniStat
          icon={CalendarDays}
          label='Account made'
          value={formatDateTime(account.created_at)}
          tone='gold'
        />
        <MiniStat
          icon={KeySquare}
          label='Password last set'
          value={
            account.password_changed_at
              ? formatSince(account.password_changed_at)
              : 'Not yet'
          }
          tone='info'
        />
      </div>
      <FormRow label='Username' description='Fixed; it is how you sign in.'>
        {(id) => (
          <Input
            id={id}
            value={account.username}
            readOnly
            className='font-mono'
          />
        )}
      </FormRow>
      <FormRow label='Display name'>
        {(id) => (
          <Input
            id={id}
            value={displayName}
            maxLength={DISPLAY_NAME_MAX}
            onChange={(event) => setDisplayName(event.target.value)}
          />
        )}
      </FormRow>
      <FormRow label='E-mail'>
        {(id) => (
          <Input
            id={id}
            type='email'
            value={email}
            maxLength={EMAIL_MAX}
            onChange={(event) => setEmail(event.target.value)}
          />
        )}
      </FormRow>
      <div className='flex min-w-0 flex-col gap-2'>
        <Text as='span' variant='caption' weight='medium'>
          Avatar tone
        </Text>
        <TonePicker
          name={displayName}
          value={tone}
          onChange={setTone}
          disabled={edit.isPending}
        />
      </div>
      <DialogFooter>
        <Button type='button' variant='outline' onClick={onClose}>
          Cancel
        </Button>
        <Button
          act={edit}
          type='submit'
          disabled={problem !== null || unchanged || edit.isPending}
          disabledReason={
            problem ??
            (unchanged
              ? 'Nothing has changed yet.'
              : 'The profile is being saved.')
          }
        >
          {edit.isPending ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <Save />
          )}
          Save the profile
        </Button>
      </DialogFooter>
    </form>
  )
}

function PasswordPanel({
  account,
  onClose,
}: {
  account: Account
  onClose: () => void
}) {
  const change = useChangePassword()
  const min = usePasswordMin()
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const checks = passwordChecks(
    password,
    repeat,
    [account.username, emailName(account.email)],
    min
  )
  const problem =
    current.length === 0
      ? 'Give your current password.'
      : !checks.every((check) => check.met)
        ? 'The new password does not meet every rule yet.'
        : password === current
          ? 'Choose a password different from the current one.'
          : null
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (problem !== null || change.isPending) return
    change.mutate(
      { current, new: password },
      {
        onSuccess: () => {
          toast.success(
            'Your password is changed; your other sessions are signed out'
          )
          onClose()
        },
      }
    )
  }
  return (
    <form className='flex min-w-0 flex-col gap-4' onSubmit={submit}>
      <PanelHeader
        icon={KeySquare}
        title='Change your password'
        lead='Every other device you are signed in on is signed out when the password changes.'
      />
      <FormRow label='Current password'>
        {(id) => (
          <PasswordField
            id={id}
            value={current}
            onChange={setCurrent}
            autoComplete='current-password'
            disabled={change.isPending}
            invalid={change.isError}
          />
        )}
      </FormRow>
      <NewPasswordFields
        label='New password'
        password={password}
        repeat={repeat}
        checks={checks}
        disabled={change.isPending}
        onPassword={setPassword}
        onRepeat={setRepeat}
        min={min}
      />
      {change.isError && (
        <Alert variant='destructive'>
          <AlertTitle>The password was not changed</AlertTitle>
          <AlertDescription>{change.error.message}</AlertDescription>
        </Alert>
      )}
      <DialogFooter>
        <Button type='button' variant='outline' onClick={onClose}>
          Cancel
        </Button>
        <Button
          act={change}
          type='submit'
          disabled={problem !== null || change.isPending}
          disabledReason={problem ?? 'The password is being changed.'}
        >
          {change.isPending ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <KeySquare />
          )}
          Change the password
        </Button>
      </DialogFooter>
    </form>
  )
}

function deviceOf(agent: string): string {
  if (!agent) return 'An unknown device'
  const browser =
    ['Firefox', 'Edg', 'Chrome', 'Safari'].find((name) =>
      agent.includes(name)
    ) ?? 'A browser'
  const system =
    ['Windows', 'Mac OS', 'Android', 'iPhone', 'iPad', 'Linux'].find((name) =>
      agent.includes(name)
    ) ?? 'an unknown system'
  return `${browser === 'Edg' ? 'Edge' : browser} on ${system === 'Mac OS' ? 'macOS' : system}`
}

function SessionRow({ session }: { session: SessionView }) {
  const end = useEndSession()
  return (
    <li className='flex min-w-0 items-center gap-3 rounded-md surface-sheen px-3 py-2'>
      <Medallion
        icon={Monitor}
        tone={session.current ? 'success' : 'muted'}
        size='sm'
      />
      <div className='flex min-w-0 flex-1 flex-col'>
        <span className='flex min-w-0 flex-wrap items-center gap-1.5'>
          <Text as='span' weight='semibold' truncate>
            {deviceOf(session.user_agent)}
          </Text>
          {session.current && (
            <Badge variant='success' size='sm'>
              This device
            </Badge>
          )}
        </span>
        <Muted as='span' variant='caption' truncate>
          {`${session.address || 'Unknown address'} · used ${formatSince(session.last_used_at)}`}
        </Muted>
        <Muted as='span' variant='caption' truncate>
          {`Signed in ${formatDateTime(session.created_at)} · ends ${formatDateTime(session.expires_at)}`}
        </Muted>
      </div>
      <Button
        act={end}
        type='button'
        size='sm'
        variant='outline'
        disabled={session.current || end.isPending}
        disabledReason={
          session.current
            ? 'Use "Sign out" to end the session you are using.'
            : 'The session is being ended.'
        }
        onClick={() =>
          end.mutate(session.id, {
            onSuccess: () => toast.success('That device is signed out'),
            onError: (error) => toast.error(error.message),
          })
        }
      >
        <MonitorX />
        Sign out
      </Button>
    </li>
  )
}

function SessionsPanel({ onClose }: { onClose: () => void }) {
  const sessions = useSessions(true)
  const others = useEndOtherSessions()
  const list = sessions.data ?? []
  const otherCount = list.filter((session) => !session.current).length
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <PanelHeader
        icon={Monitor}
        title='Where you are signed in'
        lead='Every device holding a session of yours. Sign out any you do not recognise.'
      />
      {sessions.isPending ? (
        <LoadingBlock label='Reading your sessions' />
      ) : sessions.isError ? (
        <EmptyState
          size='compact'
          icon={MonitorX}
          title='Your sessions could not be read'
          description={sessions.error.message}
          action={
            <Button
              type='button'
              variant='outline'
              onClick={() => void sessions.refetch()}
            >
              Try again
            </Button>
          }
        />
      ) : (
        <PagedList
          items={list}
          initial={SESSIONS_SHOWN}
          noun={['session', 'sessions']}
          className='flex min-w-0 flex-col gap-2'
          listProps={{ 'aria-label': 'Your sessions' }}
          itemKey={(session) => session.id}
        >
          {(session) => <SessionRow session={session} />}
        </PagedList>
      )}
      <DialogFooter>
        <Button
          act={others}
          type='button'
          variant='outline'
          className='text-destructive'
          disabled={otherCount === 0 || others.isPending}
          disabledReason={
            otherCount === 0
              ? 'No other device is signed in.'
              : 'The other sessions are being ended.'
          }
          onClick={() =>
            others.mutate(undefined, {
              onSuccess: () =>
                toast.success('Every other device is signed out'),
              onError: (error) => toast.error(error.message),
            })
          }
        >
          <LogOut />
          Sign out everywhere else
        </Button>
        <Button type='button' onClick={onClose}>
          Done
        </Button>
      </DialogFooter>
    </div>
  )
}

export function AccountDialog({
  panel,
  account,
  onClose,
}: {
  panel: AccountPanel | null
  account: Account
  onClose: () => void
}) {
  return (
    <Dialog
      open={panel !== null}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <DialogContent className='sm:max-w-xl'>
        {panel === 'profile' && (
          <ProfilePanel account={account} onClose={onClose} />
        )}
        {panel === 'password' && (
          <PasswordPanel account={account} onClose={onClose} />
        )}
        {panel === 'sessions' && <SessionsPanel onClose={onClose} />}
      </DialogContent>
    </Dialog>
  )
}
