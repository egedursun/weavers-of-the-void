import { Sun } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { useWorldState } from '@/features/pantheon/api'
import { CreatorBeliefs } from './CreatorBeliefs'
import { CreatorCult } from './CreatorCult'
import { CreatorDepth } from './CreatorDepth'
import { CreatorEditForm } from './CreatorEditForm'
import { CreatorEpic } from './CreatorEpic'
import { CreatorGalleries } from './CreatorGalleries'
import { CreatorHero } from './CreatorHero'
import { CreatorNote } from './CreatorNote'
import { CreatorTraces } from './CreatorTraces'
import { GodPanel } from './GodPanel'
import { MoodPanel } from './MoodPanel'
import { ReputationPanel } from './ReputationPanel'
import { RevelationDialog } from './RevelationDialog'
import { type MoodAxis, useCreator, useCreatorReputation } from './api'
import { MOOD_AXES } from './mood'

function savePrompt(prompt: string) {
  return unwrap(api.PATCH('/api/creator', { body: { image_prompt: prompt } }))
}

export function CreatorPageSkeleton() {
  return (
    <div className='flex flex-col gap-4'>
      <Skeleton className='h-control-lg w-2/3' />
      <Skeleton className='h-textarea w-full' />
      <Skeleton className='h-textarea w-full' />
    </div>
  )
}

export function CreatorPage() {
  const detail = useCreator()
  const reputation = useCreatorReputation()
  const state = useWorldState()
  if (detail.isPending) return <CreatorPageSkeleton />
  if (detail.isError)
    return (
      <div className='flex min-w-0 flex-col gap-6'>
        <Alert variant='destructive'>
          <Sun />
          <AlertTitle>The Creator could not be read</AlertTitle>
          <AlertDescription>{detail.error.message}</AlertDescription>
        </Alert>
        <CreatorGalleries
          creatorId={state.data?.creator?.id ?? null}
          name={state.data?.creator?.name ?? 'The Creator'}
          images={null}
          prompt={null}
        />
      </div>
    )
  const data = detail.data
  const creator = data.creator
  const values = Object.fromEntries(
    MOOD_AXES.map((axis) => [axis, data.mood[axis]])
  ) as Record<MoodAxis, number>
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <CreatorHero detail={data} />
      <div className='flex min-w-0 flex-wrap items-start gap-2'>
        <CreatorEditForm key={creator.id} creator={creator} />
        <RevelationDialog />
      </div>
      <GodPanel doom={state.data?.world?.doom_clock ?? 0} />
      <MoodPanel
        label={data.mood.label}
        values={values}
        breakdown={data.mood.breakdown}
      />
      {reputation.data ? (
        <ReputationPanel
          key={reputation.data.passions.join(':')}
          reputation={reputation.data}
        />
      ) : reputation.isError ? (
        <Alert variant='destructive'>
          <AlertTitle>Reputation could not be read</AlertTitle>
          <AlertDescription>{reputation.error.message}</AlertDescription>
        </Alert>
      ) : (
        <Skeleton className='h-textarea w-full' />
      )}
      <CreatorNote key={creator.note ?? ''} note={creator.note} />
      <CreatorEpic creator={creator} />
      <CreatorDepth creator={creator} />
      <CreatorBeliefs views={data.folk_views} name={creator.name} />
      <CreatorCult cult={data.cult} faith={data.faith} />
      <CreatorTraces traces={data.traces} />
      <CreatorGalleries
        creatorId={creator.id}
        name={creator.name}
        images={data.images}
        prompt={creator.image_prompt}
        onSavePrompt={savePrompt}
      />
    </div>
  )
}
