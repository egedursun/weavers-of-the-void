import { useMemo, useState } from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  type ComboboxOption,
  DEFAULT_MAX_SHOWN,
  filterOptions,
  matchesOption,
} from './comboboxFilter'

export type { ComboboxOption } from './comboboxFilter'

type RecordComboboxProps = {
  id?: string
  options: ComboboxOption[]
  value: string | null
  onChange: (value: string | null, option: ComboboxOption | null) => void
  placeholder: string
  searchPlaceholder?: string
  emptyText?: string
  disabled?: boolean
  disabledReason?: string
  maxShown?: number
  size?: 'sm' | 'default'
  clearable?: boolean
  'aria-label'?: string
}

export function RecordCombobox({
  id,
  options,
  value,
  onChange,
  placeholder,
  searchPlaceholder = 'Type a name',
  emptyText = 'Nothing has this name.',
  disabled = false,
  disabledReason,
  maxShown = DEFAULT_MAX_SHOWN,
  size = 'default',
  clearable = false,
  'aria-label': ariaLabel,
}: RecordComboboxProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const selected = useMemo(
    () => options.find((option) => option.value === value) ?? null,
    [options, value]
  )
  const shown = useMemo(
    () => filterOptions(options, query, maxShown),
    [options, query, maxShown]
  )
  const hidden = Math.max(
    0,
    options.filter((option) =>
      matchesOption(option, query.trim().toLowerCase())
    ).length - shown.length
  )
  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) setQuery('')
      }}
    >
      <PopoverTrigger asChild>
        <Button
          id={id}
          type='button'
          variant='outline'
          size={size}
          role='combobox'
          aria-expanded={open}
          aria-label={ariaLabel}
          disabled={disabled}
          disabledReason={disabledReason}
          data-domain='record-combobox'
          className={cn(
            'w-full min-w-0 justify-between font-normal',
            !selected && 'text-muted-foreground'
          )}
        >
          <span className='min-w-0 truncate'>
            {selected ? selected.label : placeholder}
          </span>
          <ChevronsUpDown aria-hidden='true' className='opacity-50' />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align='start'
        className='w-(--radix-popover-trigger-width) min-w-64 p-0'
      >
        <Command shouldFilter={false}>
          <CommandInput
            value={query}
            onValueChange={setQuery}
            placeholder={searchPlaceholder}
          />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            <CommandGroup>
              {clearable && selected && (
                <CommandItem
                  value='__clear__'
                  onSelect={() => {
                    onChange(null, null)
                    setOpen(false)
                  }}
                >
                  <span className='min-w-0 truncate text-muted-foreground'>
                    Clear the choice
                  </span>
                </CommandItem>
              )}
              {shown.map((option) => (
                <CommandItem
                  key={option.value}
                  value={option.value}
                  onSelect={() => {
                    onChange(option.value, option)
                    setOpen(false)
                  }}
                >
                  <Check
                    aria-hidden='true'
                    className={cn(
                      option.value === value ? 'opacity-100' : 'opacity-0'
                    )}
                  />
                  <span className='min-w-0 flex-1 truncate'>
                    {option.label}
                  </span>
                  {option.hint && (
                    <span className='max-w-1/2 min-w-0 shrink truncate text-caption text-muted-foreground'>
                      {option.hint}
                    </span>
                  )}
                </CommandItem>
              ))}
              {hidden > 0 && (
                <CommandItem value='__more__' disabled>
                  <span className='min-w-0 truncate text-caption text-muted-foreground'>
                    {`${hidden} more; type to narrow`}
                  </span>
                </CommandItem>
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
