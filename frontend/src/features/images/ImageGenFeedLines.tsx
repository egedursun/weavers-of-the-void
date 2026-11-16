import {
  CircleAlert,
  CircleCheck,
  Hourglass,
  Images,
  LoaderCircle,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'
import { EntityLink, Paged, Picture } from '@/components/domain'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Label, Muted, Text } from '@/components/typography'
import { useNames } from '@/features/entity/api/queries'
import { type LogLine } from './api'
import { type ImageLine, useImageGenStore } from './imageGenState'
import { mediaUrl } from './media'

const TONE_ICON: Record<ImageLine['tone'], LucideIcon> = {
  info: Hourglass,
  progress: LoaderCircle,
  done: CircleCheck,
  failed: CircleAlert,
  bulk: Images,
}

const TONE_CLASS: Record<ImageLine['tone'], string> = {
  info: 'text-muted-foreground',
  progress: 'animate-spin text-primary',
  done: 'text-success',
  failed: 'text-destructive',
  bulk: 'text-muted-foreground',
}

const DRAWER_OF: Partial<Record<string, DrawerKind>> = {
  entity: 'entity',
  son: 'son',
  foreign_god: 'foreign-god',
  creator: 'creator',
}

const LOG_SHOWN = 8
const PERCENT = 100
const TIME = new Intl.DateTimeFormat('en-US', {
  hour: '2-digit',
  minute: '2-digit',
})

function timeOf(at: string): string {
  const value = Date.parse(at)
  return Number.isNaN(value) ? '' : TIME.format(value)
}

type ImageGenFeedLinesProps = {
  log?: LogLine[]
  limit?: number
}

export function ImageGenFeedLines({ log = [], limit }: ImageGenFeedLinesProps) {
  const lines = useImageGenStore((store) => store.lines)
  const names = useNames()
  const shown = limit ? lines.slice(0, limit) : lines
  const target = (nodeId: number | null) => {
    if (nodeId === null) return null
    const entry = names.data?.find((item) => item.id === nodeId)
    const kind = entry ? DRAWER_OF[entry.kind] : undefined
    const label = entry?.name ?? `Record ${nodeId}`
    if (!kind)
      return (
        <Text as='span' weight='medium'>
          {label}
        </Text>
      )
    return (
      <EntityLink
        kind={kind}
        id={kind === 'creator' ? undefined : String(nodeId)}
      >
        {label}
      </EntityLink>
    )
  }
  if (shown.length === 0 && log.length === 0)
    return (
      <Muted variant='caption'>No image work since this page opened.</Muted>
    )
  return (
    <div data-domain='image-feed' className='flex min-w-0 flex-col gap-3'>
      {shown.length > 0 && (
        <ul className='flex min-w-0 flex-col gap-2'>
          <Paged items={shown} as='li'>
            {(line) => {
              const Icon = TONE_ICON[line.tone]
              return (
                <li key={line.key} className='flex min-w-0 items-center gap-2'>
                  <Icon
                    aria-hidden='true'
                    className={cn(
                      'size-icon-sm shrink-0',
                      TONE_CLASS[line.tone]
                    )}
                  />
                  {line.file && (
                    <Picture
                      compact
                      src={mediaUrl(line.file, 64)}
                      alt=''
                      className='size-portrait-sm shrink-0 rounded-sm object-cover'
                    />
                  )}
                  <div className='flex min-w-0 flex-1 flex-wrap items-baseline gap-x-2'>
                    {target(line.nodeId)}
                    <Muted as='span' variant='caption' truncate>
                      {line.text}
                    </Muted>
                  </div>
                  {line.percent !== undefined && line.tone === 'progress' && (
                    <Progress
                      size='sm'
                      value={Math.min(line.percent, PERCENT)}
                      aria-label='Image progress'
                      className='w-16 shrink-0'
                    />
                  )}
                  <Label>{timeOf(line.at)}</Label>
                </li>
              )
            }}
          </Paged>
        </ul>
      )}
      {log.length > 0 && (
        <div className='flex min-w-0 flex-col gap-1'>
          <Label variant='overline'>Worker log</Label>
          <ul className='flex min-w-0 flex-col gap-1'>
            <Paged items={log.slice(-LOG_SHOWN)} as='li'>
              {(entry, index) => (
                <li key={`${entry.at}-${index}`} className='flex min-w-0 gap-2'>
                  <Label>{timeOf(entry.at)}</Label>
                  <Text
                    as='span'
                    variant='caption'
                    tone={
                      entry.level === 'error'
                        ? 'destructive'
                        : entry.level === 'warning'
                          ? 'warning'
                          : 'muted'
                    }
                    className='min-w-0'
                  >
                    {entry.text}
                  </Text>
                </li>
              )}
            </Paged>
          </ul>
        </div>
      )}
    </div>
  )
}
