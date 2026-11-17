import { Ghost } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Section } from '@/components/domain'
import { type DrawerPageProps } from '@/components/layout/drawer/DrawerStack'
import { Muted, Text } from '@/components/typography'
import { GodDivinitySection } from '@/features/divine/GodDivinitySection'
import { BodySection } from '@/features/entity/sections/BodySection'
import { MemoriesSection } from '@/features/entity/sections/MemoriesSection'
import { MindSection } from '@/features/entity/sections/MindSection'
import { ThingSections } from '@/features/entity/sections/ThingSections'
import { BeliefSection } from '@/features/pantheon/BeliefSection'
import { RecordGallery } from '@/features/pantheon/RecordGallery'
import { AttitudeBar } from './AttitudeBar'
import { ForeignGodChronicle } from './ForeignGodChronicle'
import { ForeignGodDepth } from './ForeignGodDepth'
import { ForeignGodEditForm } from './ForeignGodEditForm'
import { ForeignGodHero } from './ForeignGodHero'
import { ForeignGodPowerPanel } from './ForeignGodPowerPanel'
import { ForeignGodProfile } from './ForeignGodProfile'
import { ForeignGodRelations } from './ForeignGodRelations'
import { editForeignGod, useForeignGod } from './api'

export function ForeignGodPage({ id }: DrawerPageProps) {
  const godId = Number(id)
  const detail = useForeignGod(godId)
  if (!Number.isInteger(godId) || godId <= 0)
    return (
      <EmptyState
        icon={Ghost}
        title='No such foreign god'
        description='This link does not point to a foreign god.'
      />
    )
  if (detail.isPending)
    return (
      <div className='flex flex-col gap-4'>
        <Skeleton className='h-control-lg w-2/3' />
        <Skeleton className='h-textarea w-full' />
      </div>
    )
  if (detail.isError)
    return (
      <Alert variant='destructive'>
        <Ghost />
        <AlertTitle>This foreign god could not be read</AlertTitle>
        <AlertDescription>{detail.error.message}</AlertDescription>
      </Alert>
    )
  const data = detail.data
  const god = data.god
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <ForeignGodHero detail={data} />
      <Section title='Description' level={3}>
        {god.description ? (
          <Text variant='prose'>{god.description}</Text>
        ) : (
          <Muted>No description yet; you can write one below.</Muted>
        )}
      </Section>
      <Section title='Attitude to the pantheon' level={3}>
        <AttitudeBar stance={god.stance} />
      </Section>
      <ForeignGodPowerPanel detail={data} />
      <ForeignGodProfile detail={data} />
      <BodySection nodeId={god.id} />
      <MindSection nodeId={god.id} />
      <MemoriesSection nodeId={god.id} />
      <GodDivinitySection godId={god.id} />
      <BeliefSection
        views={data.folk_views}
        sonId={null}
        godId={god.id}
        godName={god.name}
      />
      <ThingSections nodeId={god.id} />
      <ForeignGodDepth god={god} />
      <ForeignGodRelations detail={data} />
      <RecordGallery
        key={god.image_prompt ?? ''}
        title='Images'
        nodeId={god.id}
        name={god.name}
        images={data.images}
        prompt={god.image_prompt}
        promptLabel='Image prompt'
        onSavePrompt={(prompt) =>
          editForeignGod(god.id, { image_prompt: prompt })
        }
      />
      <ForeignGodChronicle
        godId={god.id}
        lines={data.chronicle}
        total={data.chronicle_total}
      />
      <ForeignGodEditForm
        key={`${god.id}:${god.name}:${god.status}:${god.stance}:${god.power}`}
        detail={data}
      />
    </div>
  )
}
