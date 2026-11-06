import { Crown } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/domain'
import { type DrawerPageProps } from '@/components/layout/drawer/DrawerStack'
import { BodySection } from '@/features/entity/sections/BodySection'
import { MemoriesSection } from '@/features/entity/sections/MemoriesSection'
import { MindSection } from '@/features/entity/sections/MindSection'
import { ThingSections } from '@/features/entity/sections/ThingSections'
import { AnchorageSection } from '@/features/foundations/AnchorageSection'
import {
  useOpportunities,
  useSons,
  useWorldState,
} from '@/features/pantheon/api'
import { mediaUrl } from '@/features/pantheon/media'
import { SonPromptLink } from '@/features/prompts/SonPromptLink'
import { DeadSonPanel } from './DeadSonPanel'
import { HandOfGodPanel } from './HandOfGodPanel'
import { SonBeliefs } from './SonBeliefs'
import { SonBirthChild } from './SonBirthChild'
import { SonBonds } from './SonBonds'
import { SonChat } from './SonChat'
import { SonEditForm } from './SonEditForm'
import { SonEpic } from './SonEpic'
import { SonHero } from './SonHero'
import { SonIdentity } from './SonIdentity'
import { SonImages } from './SonImages'
import { SonOpportunities } from './SonOpportunities'
import { SonOuterBargain } from './SonOuterBargain'
import { SonPowers } from './SonPowers'
import { SonRebellion } from './SonRebellion'
import { SonRecords } from './SonRecords'
import { SonReputation } from './SonReputation'
import { SonSiblings } from './SonSiblings'
import { SonStats } from './SonStats'
import { SonTools } from './SonTools'
import { SonTurns } from './SonTurns'
import { useSonDetail } from './api'
import { sonHints } from './hints'

function PageSkeleton() {
  return (
    <div className='flex flex-col gap-4'>
      <Skeleton className='h-control-lg w-2/3' />
      <Skeleton className='h-textarea w-full' />
      <Skeleton className='h-textarea w-full' />
    </div>
  )
}

export function SonPage({ id }: DrawerPageProps) {
  const sonId = Number(id)
  const detail = useSonDetail(sonId)
  const sons = useSons()
  const state = useWorldState()
  const hints = useOpportunities()
  if (!Number.isInteger(sonId) || sonId <= 0)
    return (
      <EmptyState
        icon={Crown}
        title='No such son'
        description='This link does not point to a son.'
      />
    )
  if (detail.isPending || sons.isPending) return <PageSkeleton />
  if (detail.isError)
    return (
      <Alert variant='destructive'>
        <Crown />
        <AlertTitle>This son could not be read</AlertTitle>
        <AlertDescription>{detail.error.message}</AlertDescription>
      </Alert>
    )
  const view = sons.data?.find((item) => item.son.id === sonId)
  if (!view)
    return (
      <EmptyState
        icon={Crown}
        title='No such son'
        description='They may have been removed from the pantheon.'
      />
    )
  const data = detail.data
  const son = view.son
  const ready = state.data?.pending_son_ids.includes(son.id) ?? false
  const dead = son.status === 'dead'
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <SonHero view={view} detail={data} />
      {dead && <DeadSonPanel son={son} />}
      <HandOfGodPanel
        key={`${son.id}:${son.standing_order ?? ''}`}
        view={view}
        ready={ready}
        killCost={data.kill_cost}
      />
      {!dead && (
        <SonOpportunities
          sonId={son.id}
          statusLines={sonHints(hints.data, son.name)}
        />
      )}
      {!dead && !son.rebel && <SonRebellion sonId={son.id} name={son.name} />}
      {!dead && <SonTools sonId={son.id} name={son.name} />}
      {!dead && <SonOuterBargain son={son} />}
      {!dead && <SonPromptLink sonId={son.id} name={son.name} />}
      <SonReputation son={son} reputation={data.reputation} />
      <SonChat son={son} cover={mediaUrl(view.cover)} />
      <SonEpic son={son} />
      <SonPowers view={view} />
      <SonIdentity son={son} />
      <SonEditForm
        key={`${son.id}:${son.name}:${son.level}:${son.stars}:${son.rarity}`}
        view={view}
      />
      <SonBeliefs views={data.folk_views} sonId={son.id} name={son.name} />
      <SonStats view={view} faith={data.live_faith} />
      <AnchorageSection sonId={son.id} name={son.name} />
      <BodySection nodeId={son.id} />
      <MindSection nodeId={son.id} />
      <MemoriesSection nodeId={son.id} />
      <ThingSections nodeId={son.id} />
      <SonImages son={son} images={data.images} />
      <SonSiblings sonId={son.id} siblings={data.siblings} alive={!dead} />
      {!dead && <SonBirthChild son={son} siblings={data.siblings} />}
      <SonBonds sonId={son.id} bonds={data.bonds} total={data.bond_total} />
      <SonRecords detail={data} />
      <SonTurns sonId={son.id} chronicle={data.chronicle} />
    </div>
  )
}
