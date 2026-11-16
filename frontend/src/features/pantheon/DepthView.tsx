import { type components } from '@/api/generated/schema'
import { KeyValueList, ShowMore, useShowMore } from '@/components/domain'
import { MentionText } from '@/components/domain/MentionText'
import { Label, Muted, Text } from '@/components/typography'

type GodDepth = components['schemas']['GodDepth']

const ITEMS_SHOWN = 5

function ListBlock({ title, items }: { title: string; items: string[] }) {
  const page = useShowMore(items, ITEMS_SHOWN)
  if (items.length === 0) return null
  return (
    <div className='flex min-w-0 flex-col gap-1.5'>
      <Label variant='overline'>{`${title} · ${items.length}`}</Label>
      <ul className='flex min-w-0 list-disc flex-col gap-1 pl-5'>
        {page.visible.map((item, index) => (
          <Text as='li' key={`${title}-${index}`}>
            <MentionText text={item} />
          </Text>
        ))}
      </ul>
      <ShowMore state={page} />
    </div>
  )
}

export function DepthView({
  depth,
  hiddenLabel = 'Hidden truth (only you know)',
}: {
  depth: GodDepth
  hiddenLabel?: string
}) {
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Label>{`Deepened in Epoch ${depth.epoch}`}</Label>
      {depth.history && (
        <Text variant='prose'>
          <MentionText text={depth.history} />
        </Text>
      )}
      {depth.names.length > 0 && (
        <KeyValueList
          items={depth.names.map((name, index) => ({
            key: `${name.name}-${index}`,
            label: name.name,
            value: `${name.used_by} · ${name.meaning}`,
          }))}
        />
      )}
      {depth.desire && (
        <Text as='blockquote' italic className='border-l-2 border-primary pl-3'>
          <MentionText text={depth.desire} />
        </Text>
      )}
      <div className='grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2'>
        <ListBlock title='Secrets' items={depth.secrets} />
        <ListBlock title='Fears' items={depth.fears} />
        <ListBlock title='Prohibitions' items={depth.taboos} />
        <ListBlock title='Gifts' items={depth.gifts} />
      </div>
      <ListBlock
        title='Sayings'
        items={depth.sayings.map((saying) => `${saying.form}: ${saying.text}`)}
      />
      <ListBlock title='Rumours' items={depth.rumours} />
      {depth.view_of_pantheon && (
        <KeyValueList
          items={[
            { label: 'View of the pantheon', value: depth.view_of_pantheon },
            ...(depth.worship
              ? [{ label: 'Worship', value: depth.worship }]
              : []),
          ]}
        />
      )}
      {depth.hidden_truth && (
        <div className='flex min-w-0 flex-col gap-1 rounded-md p-3 sealed-well'>
          <Label variant='overline'>{hiddenLabel}</Label>
          <Muted>
            <MentionText text={depth.hidden_truth} />
          </Muted>
        </div>
      )}
    </div>
  )
}
