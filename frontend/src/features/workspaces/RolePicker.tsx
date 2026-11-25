import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { type WorkspaceRole } from './types'
import { WORKSPACE_ROLES, WORKSPACE_ROLE_LOOK } from './workspaceLook'

export function RolePicker({
  value,
  onChange,
  disabled,
  label = 'Role in the workspace',
}: {
  value: WorkspaceRole
  onChange: (role: WorkspaceRole) => void
  disabled: boolean
  label?: string
}) {
  return (
    <div
      role='radiogroup'
      aria-label={label}
      className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'
    >
      {WORKSPACE_ROLES.map((role) => {
        const look = WORKSPACE_ROLE_LOOK[role]
        const chosen = role === value
        return (
          <Button
            key={role}
            type='button'
            variant='outline'
            size='card'
            role='radio'
            aria-checked={chosen}
            disabled={disabled}
            disabledReason='The member is being saved.'
            onClick={() => onChange(role)}
            className={cn('relative', chosen && 'border-primary bg-accent')}
          >
            <span className='flex min-w-0 items-center gap-2'>
              <Medallion icon={look.icon} tone={look.tone} size='sm' />
              <Text as='span' weight='semibold'>
                {look.label}
              </Text>
            </span>
            <Muted as='span' variant='caption'>
              {look.meaning}
            </Muted>
            {chosen && (
              <Check
                aria-hidden='true'
                className='absolute end-2 top-2 size-icon-md text-primary'
              />
            )}
          </Button>
        )
      })}
    </div>
  )
}
