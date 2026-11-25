import {
  CircleAlert,
  EyeOff,
  FileText,
  ImageIcon,
  Loader2,
  X,
} from 'lucide-react'
import { formatBytes } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Picture } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { ATTACHMENT_STATUS_LOOK } from './attachmentLook'
import { type AttachmentTray, type TrayFile } from './useAttachmentTray'

const PERCENT = 100

function StatusBadge({ item }: { item: TrayFile }) {
  if (item.status === 'uploading')
    return (
      <Badge size='sm' variant='outline'>
        <Loader2 className='animate-spin' />
        {`${String(Math.round(item.progress * PERCENT))}%`}
      </Badge>
    )
  if (item.status === 'failed' || item.status === 'rejected')
    return (
      <Badge size='sm' variant='destructive'>
        <CircleAlert />
        {item.status === 'rejected' ? 'Refused' : 'Failed'}
      </Badge>
    )
  const status = item.attachment?.status ?? 'stored'
  const look = ATTACHMENT_STATUS_LOOK[status]
  const Icon = look.icon
  return (
    <Badge size='sm' variant={look.variant}>
      <Icon />
      {look.label}
    </Badge>
  )
}

function TrayChip({
  item,
  vision,
  onRemove,
}: {
  item: TrayFile
  vision: boolean
  onRemove: () => void
}) {
  const image = item.file.type.startsWith('image/')
  const Icon = image ? ImageIcon : FileText
  const bad = item.status === 'failed' || item.status === 'rejected'
  return (
    <div
      role='listitem'
      data-tray-status={item.status}
      className={cn(
        'flex min-w-0 flex-col gap-1.5 rounded-md surface-sheen px-2 py-1.5',
        bad && 'border-destructive/50'
      )}
    >
      <div className='flex min-w-0 items-center gap-2'>
        {item.preview ? (
          <Picture
            src={item.preview}
            alt=''
            className='size-portrait-sm shrink-0 rounded-sm object-cover'
          />
        ) : (
          <Icon
            aria-hidden='true'
            className='size-icon-md shrink-0 text-muted-foreground'
          />
        )}
        <div className='flex min-w-0 flex-1 flex-col'>
          <Text as='span' variant='caption' weight='medium' truncate>
            {item.file.name}
          </Text>
          <Muted as='span' variant='caption' truncate>
            {bad ? item.error : formatBytes(item.file.size)}
          </Muted>
        </div>
        <StatusBadge item={item} />
        <Button
          type='button'
          variant='ghost'
          size='icon-sm'
          aria-label={`Remove ${item.file.name}`}
          onClick={onRemove}
        >
          <X />
        </Button>
      </div>
      {item.status === 'uploading' && (
        <Progress
          size='sm'
          value={item.progress * PERCENT}
          aria-label={`Upload of ${item.file.name}`}
        />
      )}
      {image && !vision && item.status === 'done' && (
        <Muted as='span' variant='caption' className='flex items-center gap-1'>
          <EyeOff aria-hidden='true' className='size-icon-xs shrink-0' />
          The model cannot see images; it is told that you attached one.
        </Muted>
      )}
      {item.attachment?.note && (
        <Muted as='span' variant='caption'>
          {item.attachment.note}
        </Muted>
      )}
    </div>
  )
}

export function AttachmentTrayList({
  tray,
  vision,
}: {
  tray: AttachmentTray
  vision: boolean
}) {
  if (tray.files.length === 0) return null
  return (
    <div
      role='list'
      aria-label='Files to send'
      className='grid min-w-0 grid-cols-1 gap-1.5 @md/will:grid-cols-2'
    >
      {tray.files.map((item) => (
        <TrayChip
          key={item.key}
          item={item}
          vision={vision}
          onRemove={() => tray.remove(item.key)}
        />
      ))}
    </div>
  )
}
