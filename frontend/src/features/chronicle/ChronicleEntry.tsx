import { chronicleKindValues } from '@/api/generated/schema'
import { formatInteger } from '@/lib/format'
import { cn } from '@/lib/utils'
import { ChronicleKindIcon } from '@/components/domain/ChronicleKindIcon'
import { MentionText } from '@/components/domain/MentionText'
import { Label, Text } from '@/components/typography'
import { wordOf } from '@/features/entity/affairs/labels'
import { type ChronicleLine } from '@/features/entity/api/types'
import { NodeAvatar } from '@/features/images/NodeAvatar'
import { AuthorMark } from '@/features/team/AuthorMark'
import { ChronicleLineMenu } from './ChronicleLineMenu'
import { kindTone } from './chronicleKinds'
import { useLinkTargets } from './linkTargets'

const CAST_SHOWN = 4

const TONE_CLASS = {
  default: 'gem-muted',
  primary: 'gem-gold',
  success: 'gem-success',
  warning: 'gem-warning',
  destructive: 'gem-danger',
} as const

type ChronicleEntryProps = {
  line: ChronicleLine
  kindLabel?: string
  selfId?: number
  highlighted?: boolean
  showEpoch?: boolean
  editable?: boolean
}

export function ChronicleEntry({
  line,
  kindLabel,
  selfId,
  highlighted = false,
  showEpoch = true,
  editable = true,
}: ChronicleEntryProps) {
  const targets = useLinkTargets(line.entity_ids ?? [])
  const cast = targets.filter((target) => target.id !== selfId)
  const when = [
    showEpoch ? `Epoch ${formatInteger(line.epoch)}` : null,
    line.year !== null ? `Year ${formatInteger(line.year)}` : null,
  ]
    .filter(Boolean)
    .join(' · ')
  return (
    <li
      id={`line-${line.id}`}
      data-epoch={line.epoch}
      data-chronicle-line={line.id}
      className={cn(
        'flex min-w-0 items-start gap-3 rounded-md p-2 transition-colors',
        highlighted && 'bg-primary/10 ring-1 ring-primary'
      )}
    >
      <span
        className={cn(
          'medallion size-control-sm',
          TONE_CLASS[kindTone(line.kind)]
        )}
      >
        <ChronicleKindIcon kind={line.kind} />
      </span>
      <div className='flex min-w-0 flex-1 flex-col gap-1'>
        <div className='flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5'>
          <Label variant='overline'>
            {kindLabel ?? wordOf(chronicleKindValues, line.kind)}
          </Label>
          {when && <Label>{when}</Label>}
          <AuthorMark name={line.author_name} />
        </div>
        <Text>
          <MentionText text={line.text} targets={targets} selfId={selfId} />
        </Text>
      </div>
      {cast.length > 0 && (
        <div
          className='hidden shrink-0 items-center gap-0.5 sm:flex'
          aria-label={`Mentioned: ${cast.map((target) => target.name).join(', ')}`}
        >
          {cast.slice(0, CAST_SHOWN).map((target) => (
            <span key={target.id} title={target.name} className='rounded-full'>
              <NodeAvatar id={target.id} name={target.name} />
            </span>
          ))}
          {cast.length > CAST_SHOWN && (
            <Label className='ps-3'>{`+${cast.length - CAST_SHOWN}`}</Label>
          )}
        </div>
      )}
      {editable && <ChronicleLineMenu line={line} />}
    </li>
  )
}
