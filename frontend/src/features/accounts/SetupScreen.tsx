import { type FormEvent, useState } from 'react'
import { Crown, LoaderCircle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormRow } from '@/components/domain'
import { AuthFrame } from './AuthFrame'
import { NewPasswordFields } from './NewPasswordFields'
import {
  DISPLAY_NAME_MAX,
  EMAIL_MAX,
  USERNAME_MAX,
  displayNameProblem,
  emailProblem,
  firstProblem,
  usernameProblem,
} from './accountRules'
import { usePasswordMin, useSetup } from './api'
import { emailName, passwordChecks } from './passwordRules'

export function SetupScreen() {
  const setup = useSetup()
  const min = usePasswordMin()
  const [displayName, setDisplayName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const checks = passwordChecks(
    password,
    repeat,
    [username, emailName(email)],
    min
  )
  const problem = firstProblem(
    displayNameProblem(displayName),
    usernameProblem(username),
    emailProblem(email),
    checks.every((check) => check.met)
      ? null
      : 'The password does not meet every rule yet.'
  )
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (problem !== null || setup.isPending) return
    setup.mutate({
      display_name: displayName.trim(),
      username: username.trim(),
      email: email.trim(),
      password,
    })
  }
  return (
    <AuthFrame
      title='The owner'
      icon={Crown}
      heading='Claim this server'
      lead='Nobody has signed in here yet. The account you make now owns the server: it keeps every universe already on its shelves and adds the rest of the team.'
    >
      <form
        aria-label='Create the owner account'
        className='flex min-w-0 flex-col gap-4'
        onSubmit={submit}
      >
        <FormRow label='Display name' description='How the team sees you.'>
          {(id) => (
            <Input
              id={id}
              value={displayName}
              maxLength={DISPLAY_NAME_MAX}
              autoComplete='name'
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
              autoComplete='username'
              onChange={(event) =>
                setUsername(event.target.value.toLowerCase())
              }
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
              autoComplete='email'
              onChange={(event) => setEmail(event.target.value)}
            />
          )}
        </FormRow>
        <NewPasswordFields
          password={password}
          repeat={repeat}
          checks={checks}
          disabled={setup.isPending}
          onPassword={setPassword}
          onRepeat={setRepeat}
          min={min}
        />
        {setup.isError && (
          <Alert variant='destructive'>
            <AlertTitle>The account could not be made</AlertTitle>
            <AlertDescription>{setup.error.message}</AlertDescription>
          </Alert>
        )}
        <Button
          act={setup}
          type='submit'
          size='lg'
          disabled={problem !== null || setup.isPending}
          disabledReason={problem ?? 'The account is being made.'}
        >
          {setup.isPending ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <Crown />
          )}
          {setup.isPending ? 'Claiming it' : 'Claim the server'}
        </Button>
      </form>
    </AuthFrame>
  )
}
