import { type FormEvent, useId, useState } from 'react'
import { Search } from 'lucide-react'
import { toast } from 'sonner'
import { Input } from '@/components/ui/input'

type Findable = { id: number; name: string }

type MapSearchProps = {
  items: readonly Findable[]
  onFind: (id: number) => void
  placeholder?: string
  missing?: string
  label?: string
}

export function MapSearch({
  items,
  onFind,
  placeholder = 'Find on map…',
  missing = 'No such place on the map.',
  label = 'Find on map',
}: MapSearchProps) {
  const listId = useId()
  const [value, setValue] = useState('')

  const find = (text: string): boolean => {
    const wanted = text.trim().toLocaleLowerCase('en-US')
    if (!wanted) return false
    const match = items.find(
      (item) => item.name.toLocaleLowerCase('en-US') === wanted
    )
    if (!match) return false
    onFind(match.id)
    setValue('')
    return true
  }

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!value.trim()) return
    if (!find(value)) toast.error(missing)
  }

  return (
    <form
      role='search'
      onSubmit={submit}
      className='flex min-w-0 flex-1 basis-48'
    >
      <Input
        size='sm'
        type='search'
        list={listId}
        value={value}
        leadingIcon={Search}
        aria-label={label}
        placeholder={placeholder}
        className='w-full'
        onChange={(event) => {
          setValue(event.target.value)
          const native = event.nativeEvent as InputEvent
          if (native.inputType === 'insertReplacementText' || !native.inputType)
            find(event.target.value)
        }}
      />
      <datalist id={listId}>
        {items.map((item) => (
          <option key={item.id} value={item.name} />
        ))}
      </datalist>
    </form>
  )
}
