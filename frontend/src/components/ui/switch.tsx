import * as React from 'react'
import * as SwitchPrimitive from '@radix-ui/react-switch'
import { type ActProp, refusalOf } from '@/api/mutation'
import { type Permission, refusalIn, useTeamGate } from '@/api/teamGate'
import { cn } from '@/lib/utils'
import { Refusal } from './refusal'

function Switch({
  className,
  act,
  permission,
  disabled,
  checked,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root> & {
  act?: ActProp
  permission?: Permission
}) {
  const team = useTeamGate()
  const refusal = refusalOf(act) ?? refusalIn(team, permission ?? null)
  return (
    <Refusal reason={refusal}>
      <SwitchPrimitive.Root
        disabled={disabled || refusal !== null}
        checked={permission && refusal !== null ? false : checked}
        data-slot='switch'
        className={cn(
          'peer inline-flex h-5 w-9 shrink-0 items-center rounded-full border border-transparent p-0.5 shadow-xs transition-colors outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=unchecked]:bg-input',
          className
        )}
        {...props}
      >
        <SwitchPrimitive.Thumb
          data-slot='switch-thumb'
          className='pointer-events-none block size-4 rounded-full bg-background shadow-xs ring-0 transition-transform data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0 rtl:data-[state=checked]:-translate-x-4'
        />
      </SwitchPrimitive.Root>
    </Refusal>
  )
}

export { Switch }
