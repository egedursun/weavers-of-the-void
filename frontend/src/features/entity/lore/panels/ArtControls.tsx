import { useState } from 'react'
import { Award, Brush, Landmark } from 'lucide-react'
import { artMediumValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Muted } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { AdjustBlock, ChoicePicker } from '../LoreFields'
import { type LoreCard as LoreCardData } from '../api'
import { MEDIUMS, busyOf, lookup } from '../model'
import { useLoreAction } from './controlParts'

type Artwork = NonNullable<LoreCardData['artwork']>
const PATRONS = [
  'polity',
  'settlement',
  'people',
  'cult',
  'faction',
  'mortal',
] as const
const MEDIUM_TABLE = Object.fromEntries(
  artMediumValues.map((medium) => [medium, lookup(MEDIUMS, medium)])
)

export function CanonBadge({ card }: { card: Artwork }) {
  if (!card.canon) return null
  return (
    <Badge variant='default' data-surface='ArtworkCanon'>
      <Award aria-hidden='true' />A classic of its people
    </Badge>
  )
}

export function ArtControls({
  id,
  card,
  blocked,
}: {
  id: number
  card: Artwork
  blocked: string | null
}) {
  const [patron, setPatron] = useState<number | null>(null)
  const [author, setAuthor] = useState<number | null>(null)
  const [medium, setMedium] = useState<string>(card.medium)
  const canonise = useLoreAction<boolean>(
    '/api/actions/art:canonise',
    (canon) => ({ artwork_id: id, canon })
  )
  const commission = useLoreAction<void>('/api/actions/art:commission', () => ({
    patron_id: patron,
    author_id: author,
    medium,
    subject_id: card.subject?.id ?? null,
    name: '',
    message: {},
    paid: true,
  }))
  const busy = busyOf(blocked, canonise.isPending, commission.isPending)
  return (
    <>
      <AdjustBlock title='Among the classics' icon={Award}>
        <Muted variant='caption'>
          A classic never fades for want of performers, presses its message
          harder and is copied more.
        </Muted>
        <Button
          size='sm'
          variant={card.canon ? 'outline' : 'default'}
          className='self-start'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() => canonise.mutate(!card.canon)}
        >
          <Award />
          {card.canon
            ? 'Strike it from the classics'
            : 'Set it among the classics'}
        </Button>
      </AdjustBlock>
      <AdjustBlock title='Commission a work' icon={Brush}>
        <Muted variant='caption'>
          A realm or town pays from its treasury; the work portrays the same
          subject as this one.
        </Muted>
        <EntityPicker
          types={[...PATRONS]}
          value={patron}
          onChange={setPatron}
          placeholder='Choose the patron…'
        />
        <EntityPicker
          types={['mortal']}
          value={author}
          onChange={setAuthor}
          placeholder='Choose the artist (optional)…'
        />
        <ChoicePicker
          label='Medium'
          value={medium}
          table={MEDIUM_TABLE}
          blocked={busy}
          onPick={setMedium}
        />
        <Button
          size='sm'
          variant='outline'
          className='self-start'
          disabled={busy !== null || patron === null}
          disabledReason={
            busy ?? (patron === null ? 'Choose the patron' : undefined)
          }
          onClick={() => commission.mutate()}
        >
          <Landmark />
          Commission it
        </Button>
      </AdjustBlock>
    </>
  )
}
