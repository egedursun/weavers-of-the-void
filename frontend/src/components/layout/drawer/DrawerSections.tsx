import { type RefObject, useState } from 'react'
import { ListTree } from 'lucide-react'
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
import { scrollToSection } from '@/features/entity/scrollToSection'
import { type DrawerSection, sectionsIn } from './sectionScan'

export function DrawerSections({
  body,
}: {
  body: RefObject<HTMLDivElement | null>
}) {
  const [open, setOpen] = useState(false)
  const [sections, setSections] = useState<DrawerSection[]>([])
  const change = (next: boolean) => {
    if (next) setSections(sectionsIn(body.current))
    setOpen(next)
  }
  return (
    <Popover open={open} onOpenChange={change}>
      <PopoverTrigger asChild>
        <Button variant='ghost' size='icon' aria-label='Jump to a section'>
          <ListTree />
        </Button>
      </PopoverTrigger>
      <PopoverContent align='end' className='w-72 p-0'>
        <Command>
          <CommandInput placeholder='Find a section' />
          <CommandList>
            <CommandEmpty>
              This page has no sections to jump to yet.
            </CommandEmpty>
            <CommandGroup>
              {sections.map((section) => (
                <CommandItem
                  key={section.id}
                  value={`${section.label} ${section.id}`}
                  onSelect={() => {
                    setOpen(false)
                    scrollToSection(section.id, body.current)
                  }}
                >
                  <span className='min-w-0 flex-1 truncate'>
                    {section.label}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
