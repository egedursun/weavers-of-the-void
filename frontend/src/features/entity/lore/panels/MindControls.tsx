import { useState } from 'react'
import {
  BookMarked,
  Gavel,
  Save,
  ScrollText,
  Shapes,
  Target,
} from 'lucide-react'
import { prophecyConsequenceValues } from '@/api/generated/schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Paged } from '@/components/domain'
import { Muted } from '@/components/typography'
import { EntityPicker } from '@/features/cosmos/EntityPicker'
import { AdjustBlock, ChoicePicker, NamedChip, Who } from '../LoreFields'
import { type LoreCard as LoreCardData } from '../api'
import { KindForge } from '../forge/KindForge'
import { useCustomKinds } from '../forge/kindApi'
import { type LoreNamed, busyOf, lookup, useLoreEdit } from '../model'
import { PickAndRun, useLoreAction } from './controlParts'

type Prophecy = NonNullable<LoreCardData['prophecy']>
type Ideology = NonNullable<LoreCardData['ideology']>
const CONSEQUENCES: Record<string, LoreNamed> = Object.fromEntries(
  prophecyConsequenceValues.map((value) => [value, lookup({}, value)])
)
const AUTHORITIES = ['polity', 'cult', 'settlement', 'people'] as const

export function ProphecyControls({
  id,
  card,
  blocked,
}: {
  id: number
  card: Prophecy
  blocked: string | null
}) {
  const [kind, setKind] = useState<string>(card.consequence_kind ?? '')
  const [target, setTarget] = useState<number | null>(
    card.consequence?.id ?? null
  )
  const edit = useLoreEdit(id)
  const busy = busyOf(blocked, edit.isPending)
  return (
    <AdjustBlock title='What it means when it comes true' icon={Target}>
      <div
        data-surface='ProphecyConsequence'
        className='flex min-w-0 flex-col gap-2'
      >
        {card.consequence_kind && (
          <NamedChip spec={lookup(CONSEQUENCES, card.consequence_kind)}>
            {lookup(CONSEQUENCES, card.consequence_kind).label}
            {card.consequence ? ': ' : ''}
            {card.consequence && <Who item={card.consequence} />}
          </NamedChip>
        )}
        <ChoicePicker
          label='Consequence'
          value={kind}
          table={CONSEQUENCES}
          blocked={busy}
          placeholder='None'
          onPick={setKind}
        />
        <EntityPicker
          types={['mortal', 'settlement', 'polity', 'people', 'house', 'cult']}
          value={target}
          onChange={setTarget}
          placeholder='Whom it touches…'
        />
        <Button
          size='sm'
          className='self-start'
          disabled={busy !== null}
          disabledReason={busy ?? undefined}
          onClick={() =>
            edit.mutate({
              values: {
                consequence_kind: kind || null,
                consequence_entity_id: target,
              },
            })
          }
        >
          <Save />
          Set it so
        </Button>
      </div>
    </AdjustBlock>
  )
}

export function IdeologyControls({
  id,
  card,
  blocked,
}: {
  id: number
  card: Ideology
  blocked: string | null
}) {
  const kinds = useCustomKinds('tenet')
  const suppress = useLoreAction<number>(
    '/api/actions/creed:suppress',
    (authority) => ({ ideology_id: id, authority_id: authority })
  )
  const tenet = useLoreAction<{ kind: number; held: boolean }>(
    '/api/actions/creed:custom_tenet',
    (value) => ({ ideology_id: id, kind_id: value.kind, held: value.held })
  )
  const busy = busyOf(blocked, tenet.isPending)
  return (
    <>
      {card.texts.length > 0 && (
        <AdjustBlock title='Its books' icon={BookMarked}>
          <div className='flex min-w-0 flex-wrap gap-2'>
            <Paged items={card.texts}>
              {(item) => (
                <Badge key={item.id} variant='outline'>
                  <ScrollText aria-hidden='true' />
                  <Who item={item} />
                </Badge>
              )}
            </Paged>
          </div>
        </AdjustBlock>
      )}
      <AdjustBlock title='Tenets of your own making' icon={Shapes}>
        {(kinds.data?.kinds ?? []).length === 0 && (
          <Muted variant='caption'>Name a tenet of your own below first.</Muted>
        )}
        <div className='flex min-w-0 flex-wrap gap-2'>
          {(kinds.data?.kinds ?? []).map((kind) => {
            const held = card.custom_tenets.includes(kind.id)
            return (
              <Button
                key={kind.id}
                size='sm'
                variant={held ? 'default' : 'outline'}
                aria-pressed={held}
                disabled={busy !== null}
                disabledReason={busy ?? undefined}
                onClick={() => tenet.mutate({ kind: kind.id, held: !held })}
              >
                <Shapes />
                {kind.name}
              </Button>
            )
          })}
        </div>
      </AdjustBlock>
      <AdjustBlock title='Suppress it' icon={Gavel}>
        <PickAndRun
          types={AUTHORITIES}
          placeholder='Choose who hunts it down…'
          label='Suppress the creed'
          icon={Gavel}
          blocked={blocked}
          pending={suppress.isPending}
          variant='destructive'
          note='Every follower loses heart and bears a grudge against the suppressor; a realm that held it as its creed lets it go.'
          onRun={(authority) => suppress.mutate(authority)}
        />
      </AdjustBlock>
      <KindForge catalog='tenet' />
    </>
  )
}
