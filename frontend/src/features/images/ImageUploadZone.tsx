import { useEffect, useRef, useState } from 'react'
import { LoaderCircle, Upload } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Muted, Text } from '@/components/typography'
import { IMAGE_MIMES } from './api'
import { useImageUpload } from './useImageUpload'

type ImageUploadZoneProps = {
  nodeId: number
  label: string
  acceptPaste?: boolean
  disabledReason?: string | null
}

function filesOf(list: FileList | null | undefined): File[] {
  return list ? Array.from(list) : []
}

export function ImageUploadZone({
  nodeId,
  label,
  acceptPaste = true,
  disabledReason = null,
}: ImageUploadZoneProps) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const { upload, pending } = useImageUpload(nodeId)
  const blocked = disabledReason !== null
  useEffect(() => {
    if (!acceptPaste || blocked) return
    const onPaste = (event: ClipboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target?.closest('input, textarea, [contenteditable="true"]')) return
      const files = filesOf(event.clipboardData?.files)
      if (files.length === 0) return
      event.preventDefault()
      void upload(files)
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, [acceptPaste, blocked, upload])
  return (
    <div
      data-domain='image-upload-zone'
      onDragOver={(event) => {
        if (blocked) return
        event.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault()
        setOver(false)
        if (!blocked) void upload(filesOf(event.dataTransfer.files))
      }}
      className={cn(
        'flex min-w-0 flex-col items-center justify-center gap-2 rounded-md px-4 py-6 text-center sealed-well',
        over && 'border-primary bg-primary/5'
      )}
    >
      {pending > 0 ? (
        <LoaderCircle
          aria-hidden='true'
          className='size-icon-lg animate-spin text-muted-foreground'
        />
      ) : (
        <Upload
          aria-hidden='true'
          className='size-icon-lg text-muted-foreground'
        />
      )}
      <Text weight='medium'>
        {pending > 0 ? `Uploading ${pending}…` : label}
      </Text>
      <Muted variant='caption'>
        Drop images here, paste them, or choose files. PNG, JPEG or WEBP.
      </Muted>
      <Button
        variant='outline'
        size='sm'
        disabled={blocked || pending > 0}
        disabledReason={disabledReason ?? 'Uploading.'}
        onClick={() => input.current?.click()}
      >
        Choose files
      </Button>
      <Input
        ref={input}
        type='file'
        accept={IMAGE_MIMES.join(',')}
        multiple
        hidden
        tabIndex={-1}
        aria-label={label}
        onChange={(event) => {
          void upload(filesOf(event.target.files))
          event.target.value = ''
        }}
      />
    </div>
  )
}
