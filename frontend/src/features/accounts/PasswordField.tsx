import { useState } from 'react'
import { Eye, EyeOff, KeyRound } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { PASSWORD_MAX } from './passwordRules'

export function PasswordField({
  id,
  value,
  onChange,
  autoComplete,
  invalid = false,
  disabled = false,
  describedBy,
}: {
  id: string
  value: string
  onChange: (value: string) => void
  autoComplete: 'current-password' | 'new-password'
  invalid?: boolean
  disabled?: boolean
  describedBy?: string
}) {
  const [shown, setShown] = useState(false)
  return (
    <span className='flex w-full min-w-0 items-center gap-1'>
      <Input
        id={id}
        type={shown ? 'text' : 'password'}
        value={value}
        maxLength={PASSWORD_MAX}
        autoComplete={autoComplete}
        aria-invalid={invalid || undefined}
        aria-describedby={describedBy}
        disabled={disabled}
        leadingIcon={KeyRound}
        onChange={(event) => onChange(event.target.value)}
        className='min-w-0 flex-1'
      />
      <Button
        type='button'
        variant='ghost'
        size='icon'
        aria-label={shown ? 'Hide the password' : 'Show the password'}
        aria-pressed={shown}
        disabled={disabled}
        disabledReason='The form is being sent.'
        onClick={() => setShown((value) => !value)}
      >
        {shown ? <EyeOff /> : <Eye />}
      </Button>
    </span>
  )
}
