import { BadgeCheck, TriangleAlert } from 'lucide-react'
import { EmptyState, Section, LoadingBlock } from '@/components/domain'
import { useGodGate } from '@/features/pantheon/gate'
import { type LoreCard as LoreCardData, useLore } from './api'
import { LORE_KIND, type LoreKind } from './model'
import { ArtworkPanel } from './panels/ArtworkPanel'
import { IdeologyPanel } from './panels/IdeologyPanel'
import { ItemPanel } from './panels/ItemPanel'
import { LanguagePanel } from './panels/LanguagePanel'
import { LegendPanel } from './panels/LegendPanel'
import { ProphecyPanel } from './panels/ProphecyPanel'
import { RitePanel } from './panels/RitePanel'
import { TraditionPanel } from './panels/TraditionPanel'

function Body({
  card,
  blocked,
}: {
  card: LoreCardData
  blocked: string | null
}) {
  const id = card.entity_id
  if (card.language)
    return <LanguagePanel id={id} card={card.language} blocked={blocked} />
  if (card.legend)
    return <LegendPanel id={id} card={card.legend} blocked={blocked} />
  if (card.tradition)
    return <TraditionPanel id={id} card={card.tradition} blocked={blocked} />
  if (card.ideology)
    return <IdeologyPanel id={id} card={card.ideology} blocked={blocked} />
  if (card.rite) return <RitePanel id={id} card={card.rite} blocked={blocked} />
  if (card.prophecy)
    return <ProphecyPanel id={id} card={card.prophecy} blocked={blocked} />
  if (card.item) return <ItemPanel id={id} card={card.item} blocked={blocked} />
  if (card.artwork)
    return <ArtworkPanel id={id} card={card.artwork} blocked={blocked} />
  return (
    <EmptyState
      icon={BadgeCheck}
      title='No story yet'
      description='The world has not yet given it a story; it will after the next epoch.'
    />
  )
}

export function LoreSection({
  entityId,
  kind,
  readOnlyReason,
}: {
  entityId: number
  kind: LoreKind
  readOnlyReason?: string | null
}) {
  const view = useLore(entityId)
  const { reason } = useGodGate()
  const blocked = readOnlyReason ?? reason()
  const spec = LORE_KIND[kind]
  return (
    <Section
      id='section-lore'
      title={`The ${spec.label.toLowerCase()}'s story`}
      description='How it lives in the world. Open the shaping panel below to set any value.'
      icon={spec.icon}
      tone={spec.tone}
    >
      <div className='@container/lore flex min-w-0 flex-col gap-4'>
        {view.isPending && <LoadingBlock label='Reading the record' />}
        {view.isError && (
          <EmptyState
            icon={TriangleAlert}
            title='The record could not be read'
            description={view.error.message}
          />
        )}
        {view.data && <Body card={view.data} blocked={blocked} />}
      </div>
    </Section>
  )
}
