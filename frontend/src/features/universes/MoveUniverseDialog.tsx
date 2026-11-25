import { useState } from 'react'
import { ArrowRightLeft, Check, LoaderCircle } from 'lucide-react'
import { toast } from 'sonner'
import { plural } from '@/lib/units'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { DialogFooter } from '@/components/ui/dialog'
import {
  EmptyState,
  LoadingBlock,
  ShowMore,
  useShowMore,
} from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { WorkspaceCrest } from '@/features/workspaces/WorkspaceCrest'
import { useMoveUniverse } from '@/features/workspaces/api'
import { useActiveWorkspace } from '@/features/workspaces/useActiveWorkspace'
import { WORKSPACE_KIND_LOOK } from '@/features/workspaces/workspaceLook'
import { type ActDialogProps, ActHeader } from './ActHeader'

const PLACES_SHOWN = 6

export function MoveUniverseDialog({ universe, onClose }: ActDialogProps) {
  const { workspaces, list, active } = useActiveWorkspace()
  const move = useMoveUniverse()
  const [target, setTarget] = useState<number | null>(null)
  const here = active?.role === 'admin'
  const places = list.filter(
    (workspace) => workspace.id !== active?.id && workspace.role === 'admin'
  )
  const page = useShowMore(places, PLACES_SHOWN)
  const chosen = places.find((workspace) => workspace.id === target) ?? null
  const reason = !here
    ? 'Only an administrator of this workspace moves its universes.'
    : chosen === null
      ? 'Choose where it goes first.'
      : move.isPending
        ? 'The universe is being moved.'
        : null
  return (
    <>
      <ActHeader icon={ArrowRightLeft} title={`Move ${universe.name}`}>
        Move the universe to another workspace you administer. Its members then
        reach it with their roles there; exceptions set here are dropped.
      </ActHeader>
      {workspaces.isPending ? (
        <LoadingBlock label='Reading your workspaces' />
      ) : places.length === 0 ? (
        <EmptyState
          size='compact'
          icon={ArrowRightLeft}
          title='Nowhere to move it'
          description='You administer no other workspace. Found a team workspace from the workspace switcher first.'
        />
      ) : (
        <ul
          aria-label='Where it can go'
          className='flex min-w-0 flex-col gap-2'
        >
          {page.visible.map((workspace) => {
            const picked = workspace.id === target
            return (
              <li key={workspace.id}>
                <Button
                  type='button'
                  variant='outline'
                  size='tile'
                  aria-pressed={picked}
                  disabled={!here || move.isPending}
                  disabledReason={
                    here
                      ? 'The universe is being moved.'
                      : 'Only an administrator of this workspace moves its universes.'
                  }
                  onClick={() => setTarget(workspace.id)}
                  className={cn(picked && 'border-primary bg-accent')}
                >
                  <WorkspaceCrest name={workspace.name} size='sm' />
                  <span className='flex min-w-0 flex-1 flex-col'>
                    <Text as='span' weight='semibold' truncate>
                      {workspace.name}
                    </Text>
                    <Muted as='span' variant='caption'>
                      {`${WORKSPACE_KIND_LOOK[workspace.kind].label} · ${plural(workspace.member_count, 'member')} · ${plural(workspace.universe_count, 'universe')}`}
                    </Muted>
                  </span>
                  {picked && (
                    <Check aria-hidden='true' className='text-primary' />
                  )}
                </Button>
              </li>
            )
          })}
        </ul>
      )}
      <ShowMore state={page} noun={['workspace', 'workspaces']} />
      <DialogFooter>
        <Button type='button' variant='outline' onClick={onClose}>
          Cancel
        </Button>
        <Button
          act={move}
          type='button'
          disabled={reason !== null}
          disabledReason={reason ?? ''}
          onClick={() => {
            if (chosen === null) return
            move.mutate(
              { universeId: universe.id, workspaceId: chosen.id },
              {
                onSuccess: () => {
                  toast.success(`${universe.name} now stands in ${chosen.name}`)
                  onClose()
                },
                onError: (error) => toast.error(error.message),
              }
            )
          }}
        >
          {move.isPending ? (
            <LoaderCircle className='animate-spin motion-reduce:animate-none' />
          ) : (
            <ArrowRightLeft />
          )}
          Move it
        </Button>
      </DialogFooter>
    </>
  )
}
