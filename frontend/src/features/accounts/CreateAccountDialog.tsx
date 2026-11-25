import { type FormEvent, useState } from 'react'
import { LoaderCircle, UserPlus } from 'lucide-react'
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
import { FormRow, Medallion } from '@/components/domain'
import { TemporaryPassword } from './TemporaryPassword'
import {
  DISPLAY_NAME_MAX,
  EMAIL_MAX,
  USERNAME_MAX,
  displayNameProblem,
  emailProblem,
  firstProblem,
  usernameProblem,
} from './accountRules'
import { useCreateAccount } from './api'
import { type IssuedPassword } from './types'

export function CreateAccountDialog({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const create = useCreateAccount()
  const [displayName, setDisplayName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [issued, setIssued] = useState<IssuedPassword | null>(null)
  const problem = firstProblem(
    displayNameProblem(displayName),
    usernameProblem(username),
    emailProblem(email)
  )
  const close = () => {
    setDisplayName('')
    setUsername('')
    setEmail('')
    setIssued(null)
    onClose()
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (problem !== null || create.isPending) return
    create.mutate(
      {
        display_name: displayName.trim(),
        username: username.trim(),
        email: email.trim(),
        server_role: 'member',
      },
      {
        onSuccess: (result) => {
          toast.success(`${result.account.display_name} has an account`)
          setIssued(result)
        },
        onError: (error) => toast.error(error.message),
      }
    )
  }
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && !create.isPending) close()
      }}
    >
      <DialogContent className='sm:max-w-lg'>
        <DialogHeader>
          <div className='flex min-w-0 items-center gap-3'>
            <Medallion icon={UserPlus} />
            <DialogTitle>
              {issued ? 'Hand over the password' : 'Make an account'}
            </DialogTitle>
          </div>
          <DialogDescription>
            {issued
              ? 'Copy the temporary password now; it is never shown again.'
              : 'The account gets its own personal workspace. Add it to team workspaces from their settings.'}
          </DialogDescription>
        </DialogHeader>
        {issued ? (
          <TemporaryPassword
            account={issued.account}
            password={issued.temporary_password}
            onDone={close}
          />
        ) : (
          <form className='flex min-w-0 flex-col gap-4' onSubmit={submit}>
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
            <DialogFooter>
              <Button type='button' variant='outline' onClick={close}>
                Cancel
              </Button>
              <Button
                act={create}
                type='submit'
                disabled={problem !== null || create.isPending}
                disabledReason={problem ?? 'The account is being made.'}
              >
                {create.isPending ? (
                  <LoaderCircle className='animate-spin motion-reduce:animate-none' />
                ) : (
                  <UserPlus />
                )}
                Make the account
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}
