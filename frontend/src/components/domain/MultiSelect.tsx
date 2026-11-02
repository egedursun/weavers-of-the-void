import { type ReactNode, useId, useMemo, useState } from 'react'
import { ChevronDown, ListChecks, Search, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button, type ButtonProps } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Muted, Text } from '@/components/typography'
import {
  type MultiSelectOption,
  selectionText,
  visibleOptions,
} from './multiSelectModel'

export type { MultiSelectOption } from './multiSelectModel'

type MultiSelectProps = {
  label: string
  options: MultiSelectOption[]
  value: string[]
  onChange: (next: string[]) => void
  min?: number
  id?: string
  icon?: ReactNode
  searchPlaceholder?: string
  emptyText?: string
  size?: ButtonProps['size']
  className?: string
}

export function MultiSelect({
  label,
  options,
  value,
  onChange,
  min = 0,
  id,
  icon,
  searchPlaceholder = 'Type to filter',
  emptyText = 'Nothing matches.',
  size = 'default',
  className,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const listId = useId()
  const chosen = useMemo(() => new Set(value), [value])
  const shown = visibleOptions(options, chosen, query)
  const toggle = (option: string, on: boolean) =>
    onChange(on ? [...value, option] : value.filter((item) => item !== option))
  const summary = selectionText(value.length, min)
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant='outline'
          size={size}
          aria-haspopup='dialog'
          aria-expanded={open}
          className={cn('justify-start', className)}
        >
          {icon ?? <ListChecks />}
          <span className='min-w-0 flex-1 truncate text-start'>{`${label} · ${summary}`}</span>
          <ChevronDown className='opacity-60' />
        </Button>
      </PopoverTrigger>
      <PopoverContent align='start' className='flex w-72 flex-col gap-2 p-2'>
        <Input
          type='search'
          leadingIcon={Search}
          aria-label={`Filter ${label.toLowerCase()}`}
          aria-controls={listId}
          placeholder={searchPlaceholder}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <ScrollArea className='flex max-h-72 min-h-0 flex-col'>
          {shown.length === 0 ? (
            <Muted variant='caption'>{emptyText}</Muted>
          ) : (
            <ul
              id={listId}
              aria-label={label}
              className='flex min-w-0 flex-col gap-1 pe-2'
            >
              {shown.map((option) => {
                const checkboxId = `${listId}-${option.value}`
                return (
                  <li
                    key={option.value}
                    className='flex min-w-0 items-center gap-2 rounded-md px-1 py-1 hover:bg-accent'
                  >
                    <Checkbox
                      id={checkboxId}
                      checked={chosen.has(option.value)}
                      onCheckedChange={(state) =>
                        toggle(option.value, state === true)
                      }
                    />
                    <label
                      htmlFor={checkboxId}
                      className='flex min-w-0 flex-1 cursor-pointer items-center gap-2'
                    >
                      {option.icon}
                      <Text as='span' truncate>
                        {option.label}
                      </Text>
                      {option.detail && (
                        <Muted as='span' variant='caption' truncate>
                          {option.detail}
                        </Muted>
                      )}
                    </label>
                  </li>
                )
              })}
            </ul>
          )}
        </ScrollArea>
        <div className='flex min-w-0 items-center justify-between gap-2 border-t pt-2'>
          <Muted as='span' variant='caption' aria-live='polite'>
            {summary}
          </Muted>
          <Button
            variant='ghost'
            size='sm'
            disabled={value.length === 0}
            disabledReason='Nothing is selected.'
            onClick={() => onChange([])}
          >
            <X />
            Clear
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
