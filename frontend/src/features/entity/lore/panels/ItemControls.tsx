import { useState } from 'react'
import {
  BookOpen,
  Ghost,
  HandCoins,
  History,
  Layers,
  Plus,
  Trash2,
} from 'lucide-react'
import { type ActionBody } from '@/api/actions'
import { itemDeedValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Paged, PagedList } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { AdjustBlock, ChoicePicker, NamedChip, Who } from '../LoreFields'
import { type LoreCard as LoreCardData } from '../api'
import { KindForge } from '../forge/KindForge'
import { DEEDS, PERCENT, busyOf, lookup, sentence } from '../model'
import { PickAndRun, useLoreAction } from './controlParts'

type Item = NonNullable<LoreCardData['item']>
const HOLDERS = [
  'mortal',
  'settlement',
  'people',
  'cult',
  'faction',
  'polity',
] as const
const DEED_TABLE = Object.fromEntries(
  itemDeedValues.map((deed) => [deed, lookup(DEEDS, deed)])
)

export function ItemFacts({ card }: { card: Item }) {
  if (
    card.secondary_materials.length === 0 &&
    !card.bound_spirit &&
    !card.prosthesis_for
  )
    return null
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <PagedList
        items={card.secondary_materials}
        initial={12}
        noun={['entry', 'entries']}
        as='div'
        className='flex min-w-0 flex-wrap items-center gap-2'
        listProps={{ 'data-surface': 'ItemFacts' }}
        itemKey={(material) => material}
      >
        {(material) => (
          <NamedChip
            key={material}
            spec={{ label: sentence(material), icon: Layers, tone: 'muted' }}
          />
        )}
      </PagedList>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {card.bound_spirit && (
          <Badge variant='outline'>
            <Ghost aria-hidden='true' />
            {'Bound spirit: '}
            <Who item={card.bound_spirit} />
          </Badge>
        )}
        {card.prosthesis_for && (
          <NamedChip
            spec={{
              label: `A limb for the ${card.prosthesis_for}`,
              icon: HandCoins,
              tone: 'info',
            }}
          />
        )}
      </div>
    </div>
  )
}

export function ItemControls({
  id,
  card,
  blocked,
}: {
  id: number
  card: Item
  blocked: string | null
}) {
  const [deed, setDeed] = useState('')
  const [note, setNote] = useState('')
  const [knowledge, setKnowledge] = useState<number | null>(null)
  const [fidelity, setFidelity] = useState(String(PERCENT))
  const transfer = useLoreAction('item:transfer', (receiver: number) => ({
    item_id: id,
    receiver_id: receiver,
    reason: '',
  }))
  const addDeed = useLoreAction('item:deed', (_: void) => ({
    item_id: id,
    deed: deed as ActionBody<'item:deed'>['deed'],
    note,
  }))
  const removeDeed = useLoreAction('item:deed_remove', (deedId: number) => ({
    deed_id: deedId,
  }))
  const content = useLoreAction(
    'item:content',
    (value: { knowledge: number; fidelity: number }) => ({
      book_id: id,
      knowledge_id: value.knowledge,
      fidelity: value.fidelity,
    })
  )
  const busy = busyOf(
    blocked,
    addDeed.isPending,
    removeDeed.isPending,
    content.isPending
  )
  const isBook = ['book', 'scroll', 'prayer_book'].includes(card.item_class)
  return (
    <>
      <AdjustBlock title='Give it into new hands' icon={HandCoins}>
        <PickAndRun
          act={transfer}
          types={HOLDERS}
          placeholder='Choose who receives it…'
          label='Give it'
          icon={HandCoins}
          blocked={blocked}
          pending={transfer.isPending}
          onRun={(receiver) => transfer.mutate(receiver)}
        />
      </AdjustBlock>
      <AdjustBlock title='Its story' icon={History}>
        <ul data-surface='ItemDeeds' className='flex min-w-0 flex-col gap-1.5'>
          <Paged items={card.history} as='li'>
            {(entry) => (
              <li key={entry.id} className='flex min-w-0 items-center gap-2'>
                <NamedChip spec={lookup(DEEDS, entry.deed)} />
                <Text as='span' className='min-w-0 flex-1' truncate>
                  {entry.note || `age ${entry.epoch}`}
                </Text>
                <Button
                  act={removeDeed}
                  size='icon'
                  variant='ghost'
                  aria-label='Strike this deed'
                  disabled={busy !== null}
                  disabledReason={busy ?? undefined}
                  onClick={() => removeDeed.mutate(entry.id)}
                >
                  <Trash2 />
                </Button>
              </li>
            )}
          </Paged>
        </ul>
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <ChoicePicker
            label='Deed'
            value={deed}
            table={DEED_TABLE}
            blocked={busy}
            placeholder='Choose'
            onPick={setDeed}
          />
          <div className='flex min-w-0 flex-col gap-1'>
            <Muted variant='caption'>What happened</Muted>
            <Input
              aria-label='What happened'
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </div>
        </div>
        <Button
          act={addDeed}
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null || deed === ''}
          disabledReason={busy ?? (deed === '' ? 'Choose the deed' : undefined)}
          onClick={() => addDeed.mutate()}
        >
          <Plus />
          Write the deed
        </Button>
      </AdjustBlock>
      {isBook && (
        <AdjustBlock title='What is written in it' icon={BookOpen}>
          <ul
            data-surface='BookPages'
            className='flex min-w-0 flex-col gap-1.5'
          >
            <Paged items={card.book_contents} as='li'>
              {(page) => (
                <li
                  key={page.knowledge?.id ?? 0}
                  className='flex min-w-0 items-center gap-2'
                >
                  <Text as='span' className='min-w-0 flex-1' truncate>
                    <Who item={page.knowledge} />
                  </Text>
                  <Badge variant='outline'>{`${page.fidelity}% faithful`}</Badge>
                  <Button
                    act={content}
                    size='icon'
                    variant='ghost'
                    aria-label='Scrape it out'
                    disabled={busy !== null || !page.knowledge}
                    disabledReason={busy ?? undefined}
                    onClick={() =>
                      page.knowledge &&
                      content.mutate({
                        knowledge: page.knowledge.id,
                        fidelity: 0,
                      })
                    }
                  >
                    <Trash2 />
                  </Button>
                </li>
              )}
            </Paged>
          </ul>
          <EntityPicker
            types={['knowledge']}
            value={knowledge}
            onChange={setKnowledge}
            placeholder='Choose knowledge to write…'
          />
          <div className='flex min-w-0 items-end gap-2'>
            <Input
              type='number'
              min={1}
              max={PERCENT}
              className='w-24'
              aria-label='How faithfully'
              value={fidelity}
              onChange={(event) => setFidelity(event.target.value)}
            />
            <Button
              act={content}
              size='sm'
              variant='outline'
              disabled={busy !== null || knowledge === null}
              disabledReason={
                busy ??
                (knowledge === null ? 'Choose the knowledge' : undefined)
              }
              onClick={() =>
                knowledge !== null &&
                content.mutate({
                  knowledge,
                  fidelity: Math.round(Number(fidelity) || 1),
                })
              }
            >
              <Plus />
              Write it in
            </Button>
          </div>
        </AdjustBlock>
      )}
      <KindForge catalog='item_class' />
    </>
  )
}
