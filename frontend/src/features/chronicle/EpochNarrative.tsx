import { useState } from 'react'
import { BookOpen, ChevronDown, ChevronUp, Globe2 } from 'lucide-react'
import { formatDateTime } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { MentionText } from '@/components/domain/MentionText'
import { Label, Text } from '@/components/typography'
import { ChronicleAudit } from './ChronicleAudit'
import { EpochEditForm } from './EpochEditForm'
import { KeeperByline } from './KeeperByline'
import { type EpochListItem, type PerspectiveLine } from './api'

type EpochNarrativeProps = {
  epoch: EpochListItem
  perspectives: PerspectiveLine[]
}

const CHRONICLER = 'chronicler'
const PREVIEW_CHARS = 700
const WORLD_PREVIEW_CHARS = 360

function previewOf(text: string, limit: number): string | null {
  if (text.length <= limit) return null
  const cut = text.lastIndexOf('. ', limit)
  return `${text.slice(0, cut > limit / 2 ? cut + 1 : limit).trim()} …`
}

function Prose({ text, limit }: { text: string; limit: number }) {
  const [expanded, setExpanded] = useState(false)
  const preview = previewOf(text, limit)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Text variant='prose'>
        <MentionText text={expanded || !preview ? text : preview} />
      </Text>
      {preview && (
        <Button
          variant='ghost'
          size='sm'
          className='self-start'
          aria-expanded={expanded}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <ChevronUp /> : <ChevronDown />}
          {expanded ? 'Show less' : 'Read the whole chronicle'}
        </Button>
      )}
    </div>
  )
}

export function EpochNarrative({ epoch, perspectives }: EpochNarrativeProps) {
  const worlds = (epoch.worlds ?? []).filter(
    (world) => world.narrative || world.summary
  )
  if (!epoch.narrative && worlds.length === 0 && perspectives.length === 0)
    return null
  return (
    <Tabs defaultValue={CHRONICLER}>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Label variant='overline'>Whose eyes</Label>
        <TabsList size='sm' aria-label='Whose eyes'>
          <TabsTrigger value={CHRONICLER}>The chronicler</TabsTrigger>
          {perspectives.map((item) => (
            <TabsTrigger key={item.id} value={`people-${item.id}`}>
              {item.people_name ?? 'A people'}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>
      <TabsContent value={CHRONICLER} className='flex min-w-0 flex-col gap-4'>
        {(epoch.chronicler_name || epoch.closed_at) && (
          <KeeperByline
            lead='Set down by'
            id={epoch.chronicler_entity_id}
            name={epoch.chronicler_name}
            detail={[
              epoch.chronicler_identity,
              epoch.closed_at && `closed ${formatDateTime(epoch.closed_at)}`,
            ]
              .filter(Boolean)
              .join(' · ')}
            fallback='the plain record of the age'
          />
        )}
        {epoch.narrative && (
          <div className='flex min-w-0 items-start gap-3'>
            <BookOpen
              aria-hidden='true'
              className='size-icon-sm shrink-0 text-primary'
            />
            <div className='min-w-0 flex-1'>
              <Prose text={epoch.narrative} limit={PREVIEW_CHARS} />
            </div>
          </div>
        )}
        {worlds.length > 0 && (
          <div className='grid min-w-0 grid-cols-1 gap-2 xl:grid-cols-2'>
            {worlds.map((world) => (
              <div
                key={world.world_id}
                className='flex min-w-0 flex-col gap-1.5 rounded-md border surface-framed border-gild/70 bg-card p-3'
              >
                <div className='flex min-w-0 items-center gap-2'>
                  <Globe2
                    aria-hidden='true'
                    className='size-icon-sm shrink-0 text-info'
                  />
                  <Label variant='overline'>{world.world_name}</Label>
                </div>
                <Prose
                  text={world.narrative ?? world.summary ?? ''}
                  limit={WORLD_PREVIEW_CHARS}
                />
              </div>
            ))}
          </div>
        )}
        {epoch.narrative && (
          <ChronicleAudit epoch={epoch.epoch} audit={epoch.audit} />
        )}
        <EpochEditForm
          key={`${epoch.name ?? ''}:${epoch.narrative ?? ''}`}
          epoch={epoch.epoch}
          name={epoch.name}
          narrative={epoch.narrative}
        />
      </TabsContent>
      {perspectives.map((item) => (
        <TabsContent
          key={item.id}
          value={`people-${item.id}`}
          className='flex min-w-0 flex-col gap-2'
        >
          <KeeperByline
            lead='As told by'
            id={item.historian_entity_id}
            name={item.historian}
            detail={`historian of ${item.people_name ?? 'a people'}; biased, as every people is`}
            fallback='a historian whose name is lost'
          />
          <Text variant='prose' italic>
            <MentionText text={item.text} />
          </Text>
        </TabsContent>
      ))}
    </Tabs>
  )
}
