import { useId, useState } from 'react'
import { FolderSync, Save, X } from 'lucide-react'
import { toast } from 'sonner'
import { agree, plural } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label as FieldLabel } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Medallion } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import {
  type SecondaryTarget,
  useSecondaryTarget,
  useSetSecondaryTarget,
} from './api'

function TargetEditor({
  target,
  readOnly,
}: {
  target: SecondaryTarget
  readOnly: boolean
}) {
  const [directory, setDirectory] = useState(target.directory ?? '')
  const inputId = useId()
  const save = useSetSecondaryTarget()
  const run = (value: string | null) =>
    save.mutate(value, {
      onSuccess: (result) =>
        toast.success(
          result.directory
            ? `Backups are also copied to ${result.directory}`
            : 'Backups are no longer copied elsewhere'
        ),
      onError: (error) => toast.error(error.message),
    })
  const trimmed = directory.trim()
  const unchanged = trimmed === (target.directory ?? '')
  const reason = readOnly
    ? 'A guest world is read-only'
    : save.isPending
      ? 'Saving'
      : trimmed === ''
        ? 'Write a folder path first'
        : unchanged
          ? 'Nothing has changed'
          : null
  return (
    <form
      className='flex min-w-0 flex-col gap-3 rounded-xl border bg-background p-4'
      onSubmit={(event) => {
        event.preventDefault()
        if (reason === null) run(trimmed)
      }}
    >
      <div className='flex min-w-0 items-start gap-3'>
        <Medallion
          icon={FolderSync}
          tone={target.directory ? 'success' : 'muted'}
          size='sm'
        />
        <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
          <FieldLabel htmlFor={inputId}>A second copy elsewhere</FieldLabel>
          <Muted variant='caption'>
            {`Each backup is also copied to this folder, for example a synced or external drive. The last ${plural(target.keep, 'copy', 'copies')} ${agree(target.keep, 'is', 'are')} kept there.`}
          </Muted>
        </div>
        <Badge size='sm' variant={target.directory ? 'success' : 'outline'}>
          {target.directory ? 'On' : 'Off'}
        </Badge>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <div className='min-w-0 flex-1 basis-64'>
          <Input
            id={inputId}
            leadingIcon={FolderSync}
            placeholder='~/Backups/aerona'
            value={directory}
            autoComplete='off'
            onChange={(event) => setDirectory(event.target.value)}
          />
        </div>
        <Button
          type='submit'
          variant='outline'
          disabled={reason !== null}
          disabledReason={reason ?? undefined}
        >
          <Save />
          Save the folder
        </Button>
        {target.directory && (
          <Button
            variant='ghost'
            disabled={readOnly || save.isPending}
            disabledReason={readOnly ? 'A guest world is read-only' : 'Saving'}
            onClick={() => {
              setDirectory('')
              run(null)
            }}
          >
            <X />
            Stop copying
          </Button>
        )}
      </div>
      <Muted variant='caption' truncate>
        {target.directory
          ? `Now copying to ${target.directory}`
          : 'No second copy is made yet.'}
      </Muted>
    </form>
  )
}

export function SecondaryTargetForm({ readOnly }: { readOnly: boolean }) {
  const target = useSecondaryTarget()
  if (target.isPending) return <Skeleton className='h-control-md w-full' />
  if (target.isError)
    return <Text tone='destructive'>{target.error.message}</Text>
  return (
    <TargetEditor
      key={target.data.directory ?? ''}
      target={target.data}
      readOnly={readOnly}
    />
  )
}
