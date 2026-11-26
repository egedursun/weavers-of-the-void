import { Link } from '@tanstack/react-router'
import { BrainCircuit, CircleAlert } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Text } from '@/components/typography'
import { useWorldState } from '@/features/overview/api'
import { MODELS_OFF_REASON, missingRoles, rolesNamed } from './modelReadiness'
import { type ModelRole } from './types'

function ChooseModels() {
  return (
    <Button size='sm' variant='outline' asChild>
      <Link to='/workspace' search={{ part: 'providers' }}>
        <BrainCircuit />
        Choose the models
      </Link>
    </Button>
  )
}

export function ModelNeeded({ role, what }: { role: ModelRole; what: string }) {
  const state = useWorldState().data
  if (!state) return null
  const off = !state.llm_enabled
  if (!off && !missingRoles(state).includes(role)) return null
  return (
    <Alert>
      <CircleAlert className='text-warning' />
      <AlertTitle>
        {off ? MODELS_OFF_REASON : `No model is set for ${rolesNamed([role])}`}
      </AlertTitle>
      <AlertDescription className='flex min-w-0 flex-col items-start gap-2'>
        {off
          ? `${what} waits until the server turns the language model on.`
          : `${what} waits until this workspace or the server default puts a model in the ${rolesNamed([role])} chain.`}
        {!off && <ChooseModels />}
      </AlertDescription>
    </Alert>
  )
}

export function MissingModelsBanner() {
  const missing = missingRoles(useWorldState().data)
  if (missing.length === 0) return null
  return (
    <div
      data-layout='models-banner'
      role='status'
      className='flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-warning/40 bg-warning/15 px-3 py-2 md:px-4'
    >
      <CircleAlert
        aria-hidden='true'
        className='size-icon-md shrink-0 text-warning'
      />
      <Text
        as='span'
        weight='medium'
        truncate={2}
        className='min-w-0 flex-1 basis-48'
      >
        {`No model is set for ${rolesNamed(missing)}. What needs ${missing.length === 1 ? 'it' : 'them'} waits until you choose one.`}
      </Text>
      <ChooseModels />
    </div>
  )
}
