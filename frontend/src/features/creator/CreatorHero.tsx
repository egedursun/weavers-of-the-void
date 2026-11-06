import { BookOpen, Brush, HandHeart, Sparkles, Sun, Users } from 'lucide-react'
import { formatDecimal, formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { MiniStat } from '@/components/domain'
import { Label, Muted, PageTitle, Text } from '@/components/typography'
import { PortraitGenerateOverlay } from '@/features/images/PortraitGenerateOverlay'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import { useGodGate } from '@/features/pantheon/gate'
import { MOOD_BADGE, MOOD_LABEL } from '@/features/pantheon/labels'
import { type CreatorDetail } from './api'
import { useRedrawLikeness } from './likeness'

export function RedrawLikenessButton() {
  const { reason } = useGodGate()
  const { action, running } = useRedrawLikeness()
  return (
    <div className='flex min-w-0 flex-col items-start gap-2'>
      <ActionButton
        label='Redraw the likeness'
        icon={Brush}
        blocked={
          reason({ llm: true }) ??
          (running ? 'The likeness is already being drawn.' : null)
        }
        pending={action.isPending}
        onRun={() => action.mutate()}
      />
      <ActionJob
        jobId={action.jobId}
        title='Likeness'
        onDismiss={action.clearJob}
      />
    </div>
  )
}

export function CreatorHero({ detail }: { detail: CreatorDetail }) {
  const creator = detail.creator
  const faith =
    detail.cult.length > 0 && detail.faith < 1
      ? '<1'
      : formatDecimal(detail.faith, 1)
  return (
    <header className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
      <PortraitGenerateOverlay
        nodeId={creator.id}
        name={creator.name}
        cover={detail.cover ?? null}
        rarity='legendary'
      />
      <div className='flex min-w-0 flex-1 flex-col gap-2'>
        <Label variant='overline'>
          <Sun aria-hidden='true' className='inline size-icon-xs' /> Creator ·
          immortal, indestructible
        </Label>
        <PageTitle truncate={2}>{creator.name}</PageTitle>
        <Muted>{creator.title ?? 'No likeness is drawn yet.'}</Muted>
        <div className='flex min-w-0 flex-wrap gap-1.5'>
          <Badge size='sm' variant={MOOD_BADGE[detail.mood.label]}>
            {MOOD_LABEL[detail.mood.label]}
          </Badge>
          {creator.epic && (
            <Badge size='sm' variant='default'>
              <BookOpen />
              Epic written
            </Badge>
          )}
        </div>
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-3'>
          <MiniStat
            icon={Sparkles}
            tone='verdigris'
            label='Essence'
            value={formatInteger(creator.essence)}
          />
          <MiniStat icon={HandHeart} tone='gold' label='Faith' value={faith} />
          <MiniStat
            icon={Users}
            tone='info'
            label={
              detail.cult.length === 1
                ? 'Community worships'
                : 'Communities worship'
            }
            value={detail.cult.length}
          />
        </div>
        {creator.appearance && (
          <Text variant='prose'>{creator.appearance}</Text>
        )}
        {creator.temperament && <Muted italic>{creator.temperament}</Muted>}
        <div>
          <RedrawLikenessButton />
        </div>
      </div>
    </header>
  )
}
