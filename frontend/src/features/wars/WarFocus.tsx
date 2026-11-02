import { Link } from '@tanstack/react-router'
import { ArrowLeft, Swords } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, Section } from '@/components/domain'
import { WarCard } from './WarCard'
import { useWar } from './api'

export function WarFocus({ warId }: { warId: number }) {
  const war = useWar(warId)
  return (
    <Section
      id='war-focus'
      title={war.data ? (war.data.event?.name ?? `War ${warId}`) : 'The war'}
      description='One war with its sides, battles, armies and sieges.'
      actions={
        <Button variant='outline' size='sm' asChild>
          <Link
            to='/wars'
            search={(previous) => ({ ...previous, war: undefined })}
          >
            <ArrowLeft />
            All wars
          </Link>
        </Button>
      }
    >
      {war.isPending && <Skeleton className='h-textarea w-full' />}
      {war.isError && (
        <EmptyState
          icon={Swords}
          title='No such war'
          description={war.error.message}
        />
      )}
      {war.data && <WarCard war={war.data} focused />}
    </Section>
  )
}
