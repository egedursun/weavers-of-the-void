import { type FormEvent, useDeferredValue, useState } from 'react'
import {
  AtSign,
  Check,
  LoaderCircle,
  Search,
  UserPlus,
  UserRound,
} from 'lucide-react'
import { toast } from 'sonner'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  EmptyState,
  FormRow,
  LoadingBlock,
  Medallion,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { AccountAvatar } from '@/features/accounts/AccountAvatar'
import { TemporaryPassword } from '@/features/accounts/TemporaryPassword'
import {
  DISPLAY_NAME_MAX,
  EMAIL_MAX,
  USERNAME_MAX,
  displayNameProblem,
  emailProblem,
  firstProblem,
  usernameProblem,
} from '@/features/accounts/accountRules'
import { RolePicker } from './RolePicker'
import { useAddMember, useCandidates } from './api'
import { type MemberAdded, type Workspace, type WorkspaceRole } from './types'

const CANDIDATES_SHOWN = 6

type Source = 'existing' | 'new'

const SOURCES: readonly Source[] = ['existing', 'new']

function AccountChooser({
  workspace,
  query,
  picked,
  onQuery,
  onPick,
}: {
  workspace: Workspace
  query: string
  picked: number | null
  onQuery: (value: string) => void
  onPick: (id: number) => void
}) {
  const deferred = useDeferredValue(query)
  const found = useCandidates(workspace.id, deferred)
  const candidates = found.data ?? []
  const page = useShowMore(candidates, CANDIDATES_SHOWN)
  const asked = deferred.trim().length > 0
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Input
        value={query}
        onChange={(event) => onQuery(event.target.value)}
        leadingIcon={Search}
        aria-label='Exact username or e-mail'
        placeholder='Their exact username or e-mail'
      />
      {!asked ? (
        <EmptyState
          size='compact'
          icon={AtSign}
          title='Type their exact username or e-mail'
          description='Accounts are found only by their whole username or e-mail, so nobody can browse the people on this server.'
        />
      ) : found.isPending ? (
        <LoadingBlock label='Looking for the account' />
      ) : found.isError ? (
        <EmptyState
          size='compact'
          icon={AtSign}
          title='The account could not be looked up'
          description={found.error.message}
        />
      ) : page.total === 0 ? (
        <EmptyState
          size='compact'
          icon={Search}
          title='No account to add'
          description='No active account has exactly this username or e-mail outside this workspace. Check the spelling, or make a new account instead.'
        />
      ) : (
        <>
          <ul
            aria-label='Accounts that can join'
            className='flex min-w-0 flex-col gap-1.5'
          >
            {page.visible.map((account) => {
              const chosen = account.id === picked
              return (
                <li key={account.id}>
                  <Button
                    type='button'
                    variant='outline'
                    size='tile'
                    aria-pressed={chosen}
                    onClick={() => onPick(account.id)}
                    className={chosen ? 'border-primary bg-accent' : undefined}
                  >
                    <AccountAvatar
                      name={account.display_name}
                      tone={account.avatar_tone}
                      size='sm'
                    />
                    <span className='flex min-w-0 flex-1 flex-col'>
                      <Text as='span' weight='semibold' truncate>
                        {account.display_name}
                      </Text>
                      <Muted as='span' variant='caption' truncate>
                        {`@${account.username}`}
                      </Muted>
                    </span>
                    {chosen && (
                      <Check aria-hidden='true' className='text-primary' />
                    )}
                  </Button>
                </li>
              )
            })}
          </ul>
          <ShowMore state={page} noun={['account', 'accounts']} />
        </>
      )}
    </div>
  )
}

export function AddMemberDialog({
  workspace,
  open,
  onClose,
}: {
  workspace: Workspace
  open: boolean
  onClose: () => void
}) {
  const add = useAddMember()
  const [source, setSource] = useState<Source>('existing')
  const [query, setQuery] = useState('')
  const [picked, setPicked] = useState<number | null>(null)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [role, setRole] = useState<WorkspaceRole>('viewer')
  const [added, setAdded] = useState<MemberAdded | null>(null)
  const reset = () => {
    setQuery('')
    setPicked(null)
    setUsername('')
    setEmail('')
    setDisplayName('')
    setRole('viewer')
    setAdded(null)
    setSource('existing')
  }
  const close = () => {
    reset()
    onClose()
  }
  const problem =
    source === 'existing'
      ? picked === null
        ? 'Choose the account to add.'
        : null
      : firstProblem(
          displayNameProblem(displayName),
          usernameProblem(username),
          emailProblem(email)
        )
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (problem !== null || add.isPending) return
    add.mutate(
      {
        id: workspace.id,
        draft:
          source === 'existing'
            ? { account_id: picked, role }
            : {
                username: username.trim(),
                email: email.trim(),
                display_name: displayName.trim(),
                role,
              },
      },
      {
        onSuccess: (result) => {
          toast.success(
            `${result.member.account.display_name} joins ${workspace.name}`
          )
          if (result.temporary_password) setAdded(result)
          else close()
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !add.isPending) close()
      }}
    >
      <DialogContent className='sm:max-w-2xl'>
        <DialogHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={UserPlus} />
            <DialogTitle>
              {added
                ? 'Hand over the password'
                : `Add a member to ${workspace.name}`}
            </DialogTitle>
          </div>
          <DialogDescription>
            {added
              ? 'The account is made. Copy its temporary password now; it is never shown again.'
              : 'Their role in the workspace is their role in every universe of it, those on the shelf now and those made later.'}
          </DialogDescription>
        </DialogHeader>
        {added?.temporary_password ? (
          <TemporaryPassword
            account={added.member.account}
            password={added.temporary_password}
            onDone={close}
          />
        ) : (
          <form className='flex min-w-0 flex-col gap-4' onSubmit={submit}>
            <Tabs
              value={source}
              onValueChange={(value) =>
                setSource(SOURCES.find((item) => item === value) ?? 'existing')
              }
            >
              <TabsList aria-label='Who joins'>
                <TabsTrigger value='existing'>
                  <AtSign />
                  An existing account
                </TabsTrigger>
                <TabsTrigger value='new'>
                  <UserRound />A new account
                </TabsTrigger>
              </TabsList>
              <TabsContent value='existing'>
                <AccountChooser
                  workspace={workspace}
                  query={query}
                  picked={picked}
                  onQuery={setQuery}
                  onPick={setPicked}
                />
              </TabsContent>
              <TabsContent value='new'>
                <div className='grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2'>
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
                  <FormRow
                    label='Username'
                    description='Lowercase letters, digits, dots, dashes and underscores.'
                  >
                    {(id) => (
                      <Input
                        id={id}
                        value={username}
                        maxLength={USERNAME_MAX}
                        onChange={(event) =>
                          setUsername(event.target.value.toLowerCase())
                        }
                      />
                    )}
                  </FormRow>
                  <FormRow
                    label='E-mail'
                    description='Kept with the account; no mail is sent.'
                  >
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
                </div>
              </TabsContent>
            </Tabs>
            <RolePicker
              value={role}
              onChange={setRole}
              disabled={add.isPending}
            />
            <DialogFooter>
              <Button type='button' variant='outline' onClick={close}>
                Cancel
              </Button>
              <Button
                act={add}
                type='submit'
                disabled={problem !== null || add.isPending}
                disabledReason={problem ?? 'The member is being added.'}
              >
                {add.isPending ? (
                  <LoaderCircle className='animate-spin motion-reduce:animate-none' />
                ) : (
                  <UserPlus />
                )}
                {source === 'new'
                  ? 'Make the account and add it'
                  : 'Add the member'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
