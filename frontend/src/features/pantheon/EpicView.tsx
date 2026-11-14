import { type components } from '@/api/generated/schema'
import { plural } from '@/lib/units'
import { ExpandableText, PagedList } from '@/components/domain'
import { Label, SectionTitle, Text } from '@/components/typography'
import { romanNumeral } from './labels'

type Epic = components['schemas']['Epic']

function epochRange(start: number, end: number): string {
  return start === end ? `Epoch ${start}` : `Epochs ${start} to ${end}`
}

export function EpicView({ epic }: { epic: Epic }) {
  return (
    <article className='flex min-w-0 flex-col gap-3'>
      <Label>{`Written in Epoch ${epic.epoch} · ${plural(epic.chapters.length, 'chapter', 'chapters')}`}</Label>
      <SectionTitle level={4}>{epic.title}</SectionTitle>
      {epic.verse && (
        <Text
          as='blockquote'
          variant='prose'
          italic
          className='border-l-2 border-primary pl-3'
        >
          {epic.verse}
        </Text>
      )}
      {epic.body && (
        <ExpandableText variant='prose' lines={6}>
          {epic.body}
        </ExpandableText>
      )}
      <PagedList
        as='ol'
        items={epic.chapters}
        initial={3}
        noun={['chapter', 'chapters']}
        className='flex min-w-0 flex-col gap-3'
        itemKey={(chapter, index) => `${chapter.title}-${index}`}
      >
        {(chapter, index) => (
          <li className='flex min-w-0 flex-col gap-1 border-l-2 border-primary/30 pl-3'>
            <div className='flex min-w-0 flex-wrap items-baseline gap-2'>
              <Text as='span' weight='semibold'>
                {`${romanNumeral(index + 1)}. ${chapter.title}`}
              </Text>
              <Label>
                {epochRange(chapter.epoch_start, chapter.epoch_end)}
              </Label>
            </div>
            <ExpandableText variant='prose' lines={6}>
              {chapter.text}
            </ExpandableText>
          </li>
        )}
      </PagedList>
    </article>
  )
}
