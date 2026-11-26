import { type ReactNode, useEffect, useRef } from 'react'
import { CircleAlert } from 'lucide-react'
import { onAuthSignal } from '@/api/authSignals'
import { forgetViewer } from '@/api/viewerExit'
import { Button } from '@/components/ui/button'
import { EmptyState, LoadingBlock } from '@/components/domain'
import { ConnectModelStep } from '@/features/providers/ConnectModelStep'
import { useConnectStep } from '@/features/providers/connectStep'
import { SetPasswordScreen } from './SetPasswordScreen'
import { SetupScreen } from './SetupScreen'
import { SignInScreen } from './SignInScreen'
import { refreshAuth, useAuthState } from './api'

function Waiting({ children }: { children: ReactNode }) {
  return (
    <main
      id='content'
      className='flex min-h-svh items-center justify-center bg-background px-4'
    >
      {children}
    </main>
  )
}

export function AuthGate({ children }: { children: ReactNode }) {
  const state = useAuthState()
  const connecting = useConnectStep((store) => store.open)
  const seen = useRef<number | null>(null)
  const accountId = state.data?.account?.id ?? null
  useEffect(() => onAuthSignal(() => void refreshAuth()), [])
  useEffect(() => {
    if (!state.isSuccess) return
    const before = seen.current
    seen.current = accountId
    if (before !== null && before !== accountId) forgetViewer()
  }, [state.isSuccess, accountId])
  if (state.isPending)
    return (
      <Waiting>
        <LoadingBlock label='Opening the gates' />
      </Waiting>
    )
  if (state.isError)
    return (
      <Waiting>
        <EmptyState
          icon={CircleAlert}
          title='The server cannot be reached'
          description={state.error.message}
          action={
            <Button
              type='button'
              variant='outline'
              onClick={() => void state.refetch()}
            >
              Try again
            </Button>
          }
        />
      </Waiting>
    )
  const auth = state.data
  if (auth.setup_required) return <SetupScreen />
  if (auth.account === null) return <SignInScreen />
  if (auth.must_change_password)
    return <SetPasswordScreen account={auth.account} />
  if (connecting) return <ConnectModelStep />
  return children
}
