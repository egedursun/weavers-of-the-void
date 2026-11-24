import { type ReactNode, useState } from 'react'
import { type LucideIcon, Skull, Trash2 } from 'lucide-react'
import { type ActionBody } from '@/api/actions'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ConfirmDialog,
  EmptyState,
  HeroFrame,
  Section,
} from '@/components/domain'
import { Label, Muted, PageTitle } from '@/components/typography'
import { CelestialTimeline } from '@/features/celestial/WorldWikiPage'
import { PortraitGenerateOverlay } from '@/features/images/PortraitGenerateOverlay'
import { RecordGallery } from '@/features/pantheon/RecordGallery'
import { type ScaleWiki, useCosmographyAction } from '../api'

export function WikiLoading() {
  return (
    <div className='flex flex-col gap-4'>
      <div className='flex min-w-0 gap-4'>
        <Skeleton className='size-portrait-xl rounded-xl' />
        <div className='flex flex-1 flex-col gap-2'>
          <Skeleton className='h-control-md w-1/3' />
          <Skeleton className='h-control-lg w-2/3' />
        </div>
      </div>
      <Skeleton className='h-scene w-full' />
    </div>
  )
}

export function WikiError({
  icon: Icon,
  title,
  message,
}: {
  icon: LucideIcon
  title: string
  message: string
}) {
  return (
    <Alert variant='destructive'>
      <Icon />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  )
}

export function Missing({ icon, title }: { icon: LucideIcon; title: string }) {
  return (
    <EmptyState
      icon={icon}
      title={title}
      description='This link does not point to a part of the heavens that exists now.'
    />
  )
}

export function WikiHero({
  nodeId,
  name,
  overline,
  description,
  cover,
  emblem,
  badges,
  meter,
}: {
  nodeId: number
  name: string
  overline: string
  description: string | null | undefined
  cover: string | null
  emblem: ReactNode
  badges: ReactNode
  meter?: ReactNode
}) {
  return (
    <HeroFrame>
      <header className='flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start'>
        <PortraitGenerateOverlay
          nodeId={nodeId}
          name={name}
          cover={cover}
          placeholder={emblem}
        />
        <div className='flex min-w-0 flex-1 flex-col gap-2'>
          <Label variant='overline'>{overline}</Label>
          <PageTitle truncate={2}>{name}</PageTitle>
          {description ? (
            <Muted>{description}</Muted>
          ) : (
            <Muted variant='caption'>
              No account of it is written yet; write one under Shape, or let the
              chroniclers find it.
            </Muted>
          )}
          <div className='flex min-w-0 flex-wrap gap-1.5'>{badges}</div>
          {meter}
        </div>
      </header>
    </HeroFrame>
  )
}

export function WikiRecords({
  nodeId,
  name,
  wiki,
  prompt,
  savePrompt,
}: {
  nodeId: number
  name: string
  wiki: ScaleWiki | undefined
  prompt: string | null | undefined
  savePrompt: (prompt: string) => Promise<unknown>
}) {
  return (
    <>
      <CelestialTimeline
        lines={wiki?.timeline ?? []}
        total={wiki?.timeline_total ?? 0}
        scope='node'
        scopeId={nodeId}
        emptyText={`The chronicle has not named ${name} yet.`}
      />
      <RecordGallery
        sectionId='section-scale-images'
        title={`Images of ${name}`}
        nodeId={nodeId}
        name={name}
        images={wiki?.images ?? []}
        prompt={prompt ?? null}
        promptLabel='Image prompt'
        onSavePrompt={savePrompt}
      />
    </>
  )
}

export function DangerZone<
  Name extends 'cluster:delete' | 'dimension:delete' | 'galaxy:delete',
>({
  noun,
  name,
  consequence,
  action,
  target,
}: {
  noun: string
  name: string
  consequence: string
  action: Name
  target: ActionBody<Name>
}) {
  const [open, setOpen] = useState(false)
  const remove = useCosmographyAction(
    action,
    (_: void) => target,
    `${name} is unmade`
  )
  return (
    <Section
      id='section-scale-unmake'
      title={`Unmake the ${noun}`}
      description={consequence}
      icon={Skull}
      tone='danger'
      surface='card'
    >
      <div className='flex min-w-0 flex-wrap items-center justify-between gap-3'>
        <Muted variant='caption'>
          The ledger keeps the act, so it can be undone.
        </Muted>
        <Button
          variant='destructive'
          size='sm'
          disabled={remove.isPending}
          disabledReason={remove.isPending ? 'Unmaking' : undefined}
          onClick={() => setOpen(true)}
        >
          <Trash2 />
          {`Unmake ${name}`}
        </Button>
      </div>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={`Unmake ${name}?`}
        desc={consequence}
        confirmText='Unmake'
        destructive
        isLoading={remove.isPending}
        handleConfirm={() => {
          remove.mutate()
          setOpen(false)
        }}
      />
    </Section>
  )
}
