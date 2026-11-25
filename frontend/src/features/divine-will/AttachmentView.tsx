import { useState } from 'react'
import { Link } from '@tanstack/react-router'
import { Download, EyeOff, FileText, ImageIcon } from 'lucide-react'
import { formatDateTime } from '@/lib/format'
import { formatBytes } from '@/lib/units'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  EmptyState,
  KeyValueList,
  LoadingBlock,
  Picture,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { WillMarkdown } from './WillMarkdown'
import { attachmentFileUrl, useAttachment } from './api'
import { ATTACHMENT_STATUS_LOOK } from './attachmentLook'
import { type WillAttachment } from './types'

function AttachmentBody({ attachment }: { attachment: WillAttachment }) {
  const detail = useAttachment(attachment.id)
  const image = attachment.kind === 'image'
  if (detail.isPending) return <LoadingBlock label='Opening the file' />
  if (detail.isError)
    return (
      <Text tone='destructive' role='alert'>
        {detail.error.message}
      </Text>
    )
  const status = ATTACHMENT_STATUS_LOOK[detail.data.status]
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <KeyValueList
        items={[
          { key: 'status', label: 'State', value: status.label },
          { key: 'mime', label: 'File type', value: detail.data.mime },
          { key: 'size', label: 'Size', value: formatBytes(detail.data.size) },
          {
            key: 'seen',
            label: 'Seen by the model',
            value: detail.data.seen_by_model ? 'Yes' : 'No',
          },
          {
            key: 'cycle',
            label: 'Sent with',
            value:
              detail.data.cycle_id === null
                ? 'Not sent yet'
                : 'An exchange of this session',
          },
          {
            key: 'created',
            label: 'Uploaded',
            value: formatDateTime(detail.data.created_at),
          },
          ...(detail.data.note
            ? [{ key: 'note', label: 'Note', value: detail.data.note }]
            : []),
        ]}
      />
      {image ? (
        <Picture
          src={attachmentFileUrl(attachment.id)}
          alt={attachment.filename}
          className='max-h-96 w-full rounded-md object-contain'
        />
      ) : detail.data.markdown.trim() ? (
        <div className='max-h-96 min-w-0 overflow-y-auto rounded-md surface-well px-3 py-2'>
          <WillMarkdown text={detail.data.markdown} />
        </div>
      ) : (
        <EmptyState
          size='compact'
          icon={FileText}
          title='No text was read from it'
          description='The file is kept as it is; its text could not be drawn out.'
        />
      )}
      <Button variant='outline' size='sm' className='w-fit' asChild>
        <a
          href={attachmentFileUrl(attachment.id)}
          download={attachment.filename}
        >
          <Download />
          Save the original
        </a>
      </Button>
    </div>
  )
}

export function AttachmentChip({ attachment }: { attachment: WillAttachment }) {
  const [open, setOpen] = useState(false)
  const image = attachment.kind === 'image'
  const Icon = image ? ImageIcon : FileText
  const status = ATTACHMENT_STATUS_LOOK[attachment.status]
  const unseen = image && !attachment.seen_by_model
  return (
    <>
      <Button
        variant='outline'
        size='sm'
        aria-label={`${attachment.filename}, ${status.label}${unseen ? ', not seen by the model' : ''}`}
        onClick={() => setOpen(true)}
      >
        <Icon />
        {attachment.filename}
        {unseen && <EyeOff className='text-warning' />}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{attachment.filename}</DialogTitle>
            <DialogDescription asChild>
              <div className='flex flex-wrap items-center gap-1.5'>
                <Badge size='sm' variant={status.variant}>
                  {status.label}
                </Badge>
                {unseen && (
                  <Muted as='span' variant='caption'>
                    The model could not see this image; it was told that you
                    attached one.
                  </Muted>
                )}
              </div>
            </DialogDescription>
          </DialogHeader>
          {open && <AttachmentBody attachment={attachment} />}
        </DialogContent>
      </Dialog>
    </>
  )
}

export function ArtifactLink({
  artifactId,
  version,
}: {
  artifactId: number
  version: number
}) {
  return (
    <Button variant='outline' size='sm' className='w-fit' asChild>
      <Link to='/library' search={{ artifact: artifactId }}>
        <FileText />
        {version > 1
          ? `Read version ${String(version)} in the Library`
          : 'Read it in the Library'}
      </Link>
    </Button>
  )
}
