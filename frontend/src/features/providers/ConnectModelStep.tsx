import { ArrowRight, BrainCircuit, CircleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { EmptyState, IntroNote, LoadingBlock } from '@/components/domain'
import { AuthFrame } from '@/features/accounts/AuthFrame'
import { useWorkspaces } from '@/features/workspaces/api'
import { ProvidersPanel } from './ProvidersPanel'
import { useProviders } from './api'
import { useConnectStep } from './connectStep'

export function ConnectModelStep() {
  const finish = useConnectStep((state) => state.finish)
  const workspaces = useWorkspaces()
  const personal =
    workspaces.data?.find((workspace) => workspace.kind === 'personal') ?? null
  const scope = personal ? { workspaceId: personal.id } : null
  const providers = useProviders(scope)
  const ready = (providers.data?.roles ?? []).some(
    (role) => role.entries.length > 0 || role.server_entries.length > 0
  )
  return (
    <AuthFrame
      title='Connect a model'
      icon={BrainCircuit}
      heading='Give the world a mind'
      lead='The gods, the chronicle and the Divine Will think with a model you connect. Log in to a subscription of your own here, or add a key; you can change all of it later.'
      wide
      footer={
        <div className='flex min-w-0 flex-wrap justify-end gap-2'>
          <Button type='button' variant='outline' onClick={finish}>
            Skip for now
          </Button>
          <Button
            type='button'
            disabled={!ready}
            disabledReason='Put a model in at least one role first, or skip for now.'
            onClick={finish}
          >
            Continue
            <ArrowRight />
          </Button>
        </div>
      }
    >
      <IntroNote>
        Team workspaces use the server default, which you set later under Team
        and workspace, Models.
      </IntroNote>
      {workspaces.isPending ? (
        <LoadingBlock label='Finding your workspace' />
      ) : scope === null ? (
        <EmptyState
          size='compact'
          icon={CircleAlert}
          title='Your workspace could not be found'
          description={
            workspaces.isError
              ? workspaces.error.message
              : 'Skip for now and connect a model from the workspace settings.'
          }
        />
      ) : (
        <ProvidersPanel scope={scope} />
      )}
    </AuthFrame>
  )
}
