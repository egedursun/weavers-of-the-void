import { type FormEvent, useState } from 'react'
import { CircleAlert, KeySquare, LoaderCircle, LogOut } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { FormRow } from '@/components/domain'
import { AuthFrame } from './AuthFrame'
import { NewPasswordFields } from './NewPasswordFields'
import { PasswordField } from './PasswordField'
import { useChangePassword, usePasswordMin, useSignOut } from './api'
import { emailName, passwordChecks } from './passwordRules'
import { type Account } from './types'

export function SetPasswordScreen({ account }: { account: Account }) {
  const change = useChangePassword()
  const min = usePasswordMin()
  const signOut = useSignOut()
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
      ? 'Give the temporary password you were handed.'
      : !checks.every((check) => check.met)
        ? 'The new password does not meet every rule yet.'
        : password === current
          ? 'Choose a password different from the temporary one.'
          : null
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (problem !== null || change.isPending) return
    change.mutate(
      { current, new: password },
      {
        onSuccess: () =>
          toast.success(
            `Welcome, ${account.display_name}. Your password is set.`
          ),
      }
    )
  }
  return (
    <AuthFrame
      title='Set your password'
      icon={KeySquare}
      heading={`Welcome, ${account.display_name}`}
      lead='You signed in with a temporary password. Choose your own now; nobody else will know it, and the temporary one stops working.'
      footer={
        <Button
          act={signOut}
          type='button'
          variant='ghost'
          className='self-center'
          disabled={signOut.isPending}
          disabledReason='Signing out.'
          onClick={() => signOut.mutate()}
        >
          <LogOut />
          Not you? Sign out
        </Button>
      }
    >
      <form
        aria-label='Set your password'
        className='flex min-w-0 flex-col gap-4'
        onSubmit={submit}
      >
        <FormRow label='Temporary password'>
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
          label='Your new password'
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
            <CircleAlert />
            <AlertTitle>The password was not changed</AlertTitle>
            <AlertDescription>{change.error.message}</AlertDescription>
          </Alert>
        )}
        <Button
          act={change}
          type='submit'
          size='lg'
          disabled={problem !== null || change.isPending}
          disabledReason={problem ?? 'The password is being set.'}
        >
          {change.isPending ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <KeySquare />
          )}
          {change.isPending ? 'Setting the password' : 'Set my password'}
        </Button>
      </form>
    </AuthFrame>
  )
}
