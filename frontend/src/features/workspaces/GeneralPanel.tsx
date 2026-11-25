import { type FormEvent, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import {
  CalendarDays,
  DoorOpen,
  LibraryBig,
  LoaderCircle,
  Save,
  Trash2,
  UsersRound,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatDateTime, formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  ConfirmDialog,
  FormRow,
  MiniStat,
  PanelGrid,
  Section,
} from '@/components/domain'
import { Muted } from '@/components/typography'
import {
  useDeleteWorkspace,
  useLeaveWorkspace,
  useRenameWorkspace,
} from './api'
import { type Workspace } from './types'
import { WORKSPACE_KIND_LOOK, WORKSPACE_ROLE_LOOK } from './workspaceLook'
import { WORKSPACE_NAME_MAX, workspaceNameProblem } from './workspaceRules'

type Ending = 'leave' | 'delete'

export function GeneralPanel({
  workspace,
  lastAdmin,
}: {
  workspace: Workspace
  lastAdmin: boolean
}) {
  const rename = useRenameWorkspace()
  const remove = useDeleteWorkspace()
  const leave = useLeaveWorkspace()
  const navigate = useNavigate()
  const [name, setName] = useState(workspace.name)
  const [ending, setEnding] = useState<Ending | null>(null)
  const admin = workspace.role === 'admin'
  const personal = workspace.kind === 'personal'
  const problem = workspaceNameProblem(name)
  const unchanged = name.trim() === workspace.name
  const kind = WORKSPACE_KIND_LOOK[workspace.kind]
  const role = WORKSPACE_ROLE_LOOK[workspace.role]
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!admin || problem !== null || unchanged) return
    rename.mutate(
      { id: workspace.id, name: name.trim() },
      {
        onSuccess: () => toast.success(`The workspace is now ${name.trim()}`),
        onError: (error) => toast.error(error.message),
      }
    )
  }
  const goHome = () => {
    setEnding(null)
    void navigate({ to: '/' })
  }
  const leaveReason = personal
    ? 'Your personal workspace is always yours.'
    : lastAdmin
      ? 'You are its last administrator; make someone else administrator first.'
      : null
  const deleteReason = personal
    ? 'A personal workspace lasts as long as its account.'
    : !admin
      ? 'Only administrators of the workspace delete it.'
      : null
  return (
    <PanelGrid>
      <Section title='The workspace' icon={kind.icon} surface='card' level={3}>
        <div className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'>
          <MiniStat
            icon={kind.icon}
            label='Kind'
            value={kind.label}
            tone={kind.tone}
          />
          <MiniStat
            icon={role.icon}
            label='Your role'
            value={role.label}
            tone={role.tone}
          />
          <MiniStat
            icon={UsersRound}
            label='Members'
            value={formatInteger(workspace.member_count)}
            tone='info'
          />
          <MiniStat
            icon={LibraryBig}
            label='Universes'
            value={formatInteger(workspace.universe_count)}
            tone='gold'
          />
        </div>
        <span className='flex min-w-0 items-center gap-1.5'>
          <CalendarDays
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-muted-foreground'
          />
          <Muted as='span' variant='caption'>
            {`Founded ${formatDateTime(workspace.created_at)}`}
          </Muted>
        </span>
        <form className='flex min-w-0 flex-col gap-3' onSubmit={submit}>
          <FormRow label='Name of the workspace'>
            {(id) => (
              <Input
                id={id}
                value={name}
                maxLength={WORKSPACE_NAME_MAX}
                disabled={!admin}
                title={
                  admin
                    ? undefined
                    : 'Only administrators rename the workspace.'
                }
                onChange={(event) => setName(event.target.value)}
              />
            )}
          </FormRow>
          <Button
            act={rename}
            type='submit'
            className='self-end'
            disabled={
              !admin || problem !== null || unchanged || rename.isPending
            }
            disabledReason={
              !admin
                ? 'Only administrators rename the workspace.'
                : (problem ??
                  (unchanged
                    ? 'The name has not changed.'
                    : 'Saving the name.'))
            }
          >
            {rename.isPending ? (
              <LoaderCircle className='animate-spin motion-reduce:animate-none' />
            ) : (
              <Save />
            )}
            Save the name
          </Button>
        </form>
      </Section>
      <Section
        title='Leaving and ending'
        icon={DoorOpen}
        surface='card'
        level={3}
      >
        <Muted variant='caption'>
          Leaving takes away your access; deleting the workspace sends every
          universe in it to the trash, where it waits for its days. Whatever
          anyone made stays attributed to them.
        </Muted>
        <div className='flex min-w-0 flex-wrap gap-2'>
          <Button
            act={leave}
            type='button'
            variant='outline'
            disabled={leaveReason !== null || leave.isPending}
            disabledReason={leaveReason ?? 'Leaving the workspace.'}
            onClick={() => setEnding('leave')}
          >
            <DoorOpen />
            Leave the workspace
          </Button>
          <Button
            act={remove}
            type='button'
            variant='destructive'
            disabled={deleteReason !== null || remove.isPending}
            disabledReason={deleteReason ?? 'Deleting the workspace.'}
            onClick={() => setEnding('delete')}
          >
            <Trash2 />
            Delete the workspace
          </Button>
        </div>
      </Section>
      <ConfirmDialog
        act={[remove, leave]}
        open={ending !== null}
        onOpenChange={(next) => {
          if (!next && !remove.isPending && !leave.isPending) setEnding(null)
        }}
        destructive
        title={
          ending === 'delete'
            ? `Delete ${workspace.name}?`
            : `Leave ${workspace.name}?`
        }
        desc={
          ending === 'delete'
            ? `Its ${workspace.universe_count === 1 ? 'universe goes' : 'universes go'} to the trash and every member loses access. Universes in the trash can be brought back until their purge date.`
            : 'You lose access to its universes. An administrator can add you again.'
        }
        confirmText={ending === 'delete' ? 'Delete the workspace' : 'Leave'}
        isLoading={remove.isPending || leave.isPending}
        handleConfirm={() => {
          const after = {
            onSuccess: () => {
              toast.success(
                ending === 'delete'
                  ? `${workspace.name} is deleted`
                  : `You have left ${workspace.name}`
              )
              goHome()
            },
            onError: (error: Error) => toast.error(error.message),
          }
          if (ending === 'delete') remove.mutate(workspace.id, after)
          if (ending === 'leave') leave.mutate(workspace.id, after)
        }}
      />
    </PanelGrid>
  )
}
