import { useId } from 'react'
import { FormRow } from '@/components/domain'
import { PasswordField } from './PasswordField'
import { PasswordStrength } from './PasswordStrength'
import { type PasswordCheck } from './passwordRules'

export function NewPasswordFields({
  password,
  repeat,
  checks,
  disabled,
  onPassword,
  onRepeat,
  min,
  label = 'Password',
}: {
  password: string
  repeat: string
  checks: PasswordCheck[]
  disabled: boolean
  onPassword: (value: string) => void
  onRepeat: (value: string) => void
  min: number
  label?: string
}) {
  const rulesId = useId()
  return (
    <>
      <FormRow label={label}>
        {(id) => (
          <PasswordField
            id={id}
            value={password}
            onChange={onPassword}
            autoComplete='new-password'
            disabled={disabled}
            describedBy={rulesId}
          />
        )}
      </FormRow>
      <FormRow label='Repeat the password'>
        {(id) => (
          <PasswordField
            id={id}
            value={repeat}
            onChange={onRepeat}
            autoComplete='new-password'
            disabled={disabled}
            invalid={repeat.length > 0 && repeat !== password}
            describedBy={rulesId}
          />
        )}
      </FormRow>
      <PasswordStrength
        id={rulesId}
        password={password}
        checks={checks}
        min={min}
      />
    </>
  )
}
