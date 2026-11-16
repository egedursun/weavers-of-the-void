import { useRef, useState } from 'react'
import { FileArchive, Upload, X } from 'lucide-react'
import { formatBytes } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Muted, Text } from '@/components/typography'
import { acceptsFile } from './fileAccept'

type FilePickerProps = {
  id?: string
  file: File | null
  onChange: (file: File | null) => void
  accept?: string
  label?: string
  hint?: string
  disabledReason?: string | null
}

export function FilePicker({
  id,
  file,
  onChange,
  accept,
  label = 'Drop a file here or choose one',
  hint,
  disabledReason = null,
}: FilePickerProps) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const [rejected, setRejected] = useState<string | null>(null)
  const blocked = disabledReason !== null
  const take = (next: File | undefined) => {
    if (!next) return
    if (!acceptsFile(next, accept)) {
      setRejected(`${next.name} is not a file this accepts.`)
      return
    }
    setRejected(null)
    onChange(next)
  }
  return (
    <div
      data-domain='file-picker'
      onDragOver={(event) => {
        if (blocked) return
        event.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault()
        setOver(false)
        if (!blocked) take(event.dataTransfer.files[0])
      }}
      className={cn(
        'flex min-w-0 flex-col gap-3 rounded-md px-4 py-4 sealed-well',
        over && 'border-primary bg-primary/5'
      )}
    >
      {file ? (
        <div className='flex min-w-0 items-center gap-3'>
          <FileArchive
            aria-hidden='true'
            className='size-icon-lg shrink-0 text-muted-foreground'
          />
          <div className='flex min-w-0 flex-1 flex-col'>
            <Text weight='medium' truncate>
              {file.name}
            </Text>
            <Muted variant='caption'>{formatBytes(file.size)}</Muted>
          </div>
          <Button
            type='button'
            variant='ghost'
            size='sm'
            disabled={blocked}
            disabledReason={disabledReason ?? undefined}
            onClick={() => {
              setRejected(null)
              onChange(null)
            }}
          >
            <X />
            Remove
          </Button>
        </div>
      ) : (
        <div className='flex min-w-0 flex-col items-center gap-2 text-center'>
          <Upload
            aria-hidden='true'
            className='size-icon-lg text-muted-foreground'
          />
          <Text weight='medium'>{label}</Text>
          {hint && <Muted variant='caption'>{hint}</Muted>}
          <Button
            type='button'
            variant='outline'
            size='sm'
            disabled={blocked}
            disabledReason={disabledReason ?? undefined}
            onClick={() => input.current?.click()}
          >
            Choose a file
          </Button>
        </div>
      )}
      {rejected && (
        <Text variant='caption' tone='destructive'>
          {rejected}
        </Text>
      )}
      <Input
        id={id}
        ref={input}
        type='file'
        accept={accept}
        hidden
        tabIndex={-1}
        aria-label={id ? undefined : label}
        onChange={(event) => {
          take(event.target.files?.[0])
          event.target.value = ''
        }}
      />
    </div>
  )
}
