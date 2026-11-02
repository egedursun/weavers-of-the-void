import { type ReactNode, useId } from 'react'
import { Check, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Label as FieldLabel } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Muted, Text } from '@/components/typography'
import { type KpiTone, Medallion } from './KpiTile'

export type Choice<T extends string> = {
  value: T
  label: string
  hint?: string
  icon: LucideIcon
}

export function ChoiceTiles<T extends string>({
  label,
  value,
  options,
  onChange,
  columns = 3,
}: {
  label: string
  value: T
  options: readonly Choice<T>[]
  onChange: (value: T) => void
  columns?: 2 | 3 | 4
}) {
  return (
    <div
      role='radiogroup'
      aria-label={label}
      className={cn(
        'grid min-w-0 grid-cols-1 gap-2',
        columns === 2 && 'sm:grid-cols-2',
        columns === 3 && 'sm:grid-cols-3',
        columns === 4 && 'sm:grid-cols-2 lg:grid-cols-4'
      )}
    >
      {options.map((option) => {
        const active = option.value === value
        return (
          <Button
            key={option.value}
            type='button'
            role='radio'
            aria-checked={active}
            variant='outline'
            size='tile'
            onClick={() => onChange(option.value)}
            className={cn(active && 'border-primary/60 bg-primary/10')}
          >
            <Medallion
              icon={option.icon}
              tone={active ? 'gold' : 'muted'}
              size='sm'
            />
            <span className='flex min-w-0 flex-1 flex-col'>
              <Text as='span' weight='semibold' truncate>
                {option.label}
              </Text>
              {option.hint && (
                <Muted as='span' variant='caption' truncate={2}>
                  {option.hint}
                </Muted>
              )}
            </span>
            {active && (
              <Check
                aria-hidden='true'
                className='size-icon-sm shrink-0 text-primary'
              />
            )}
          </Button>
        )
      })}
    </div>
  )
}

export function SettingGroup({
  label,
  description,
  children,
}: {
  label: string
  description?: string
  children: ReactNode
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <div className='flex min-w-0 flex-col gap-0.5'>
        <Text as='span' weight='semibold'>
          {label}
        </Text>
        {description && <Muted variant='caption'>{description}</Muted>}
      </div>
      {children}
    </div>
  )
}

export function SettingRow({
  icon,
  tone = 'gold',
  label,
  description,
  active = true,
  children,
}: {
  icon: LucideIcon
  tone?: KpiTone
  label: string
  description?: string
  active?: boolean
  children: (controlId: string) => ReactNode
}) {
  const id = useId()
  return (
    <div
      className={cn(
        'flex min-w-0 flex-wrap items-center gap-3 rounded-xl border p-3',
        active ? 'bg-background' : 'bg-muted/40'
      )}
    >
      <Medallion icon={icon} tone={active ? tone : 'muted'} size='sm' />
      <div className='flex min-w-0 flex-1 basis-48 flex-col gap-0.5'>
        <FieldLabel htmlFor={id}>{label}</FieldLabel>
        {description && <Muted variant='caption'>{description}</Muted>}
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {children(id)}
      </div>
    </div>
  )
}

export function SwitchRow({
  icon,
  tone,
  label,
  description,
  checked,
  onChange,
  disabled = false,
  extra,
}: {
  icon: LucideIcon
  tone?: KpiTone
  label: string
  description?: string
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  extra?: ReactNode
}) {
  return (
    <SettingRow
      icon={icon}
      tone={tone}
      label={label}
      description={description}
      active={checked}
    >
      {(id) => (
        <>
          {extra}
          <Switch
            id={id}
            checked={checked}
            disabled={disabled}
            onCheckedChange={onChange}
          />
        </>
      )}
    </SettingRow>
  )
}
