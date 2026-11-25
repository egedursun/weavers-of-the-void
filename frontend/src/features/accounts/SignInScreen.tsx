import { type FormEvent, useState } from 'react'
import { CircleAlert, DoorOpen, LoaderCircle, UserRound } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormRow, IntroNote } from '@/components/domain'
import { AuthFrame } from './AuthFrame'
import { PasswordField } from './PasswordField'
import { EMAIL_MAX } from './accountRules'
import { useSignIn } from './api'

export function SignInScreen() {
  const signIn = useSignIn()
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const problem =
    login.trim().length === 0
      ? 'Give your username or e-mail.'
      : password.length === 0
        ? 'Give your password.'
        : null
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (problem !== null || signIn.isPending) return
    signIn.mutate(
      { login: login.trim(), password },
      { onError: () => setPassword('') }
    )
  }
  return (
    <AuthFrame
      title='Sign in'
      icon={DoorOpen}
      heading='Return to the void'
      lead='Sign in to reach your workspaces and the universes your team shapes together.'
      footer={
        <IntroNote>
          Forgot your password? Ask an administrator of your workspace to reset
          it; you will get a temporary one to replace at your next sign-in.
        </IntroNote>
      }
    >
      <form
        aria-label='Sign in'
        className='flex min-w-0 flex-col gap-4'
        onSubmit={submit}
      >
        <FormRow label='Username or e-mail'>
          {(id) => (
            <Input
              id={id}
              value={login}
              maxLength={EMAIL_MAX}
              autoComplete='username'
              leadingIcon={UserRound}
              onChange={(event) => setLogin(event.target.value)}
            />
          )}
        </FormRow>
        <FormRow label='Password'>
          {(id) => (
            <PasswordField
              id={id}
              value={password}
              onChange={setPassword}
              autoComplete='current-password'
              disabled={signIn.isPending}
              invalid={signIn.isError}
            />
          )}
        </FormRow>
        {signIn.isError && (
          <Alert variant='destructive'>
            <CircleAlert />
            <AlertTitle>You could not be signed in</AlertTitle>
            <AlertDescription>{signIn.error.message}</AlertDescription>
          </Alert>
        )}
        <Button
          act={signIn}
          type='submit'
          size='lg'
          disabled={problem !== null || signIn.isPending}
          disabledReason={problem ?? 'Signing in.'}
        >
          {signIn.isPending ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <DoorOpen />
          )}
          {signIn.isPending ? 'Signing in' : 'Sign in'}
        </Button>
      </form>
    </AuthFrame>
  )
}
