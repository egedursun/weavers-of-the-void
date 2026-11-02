import { useState } from 'react'
import {
  Brain,
  Droplet,
  Hourglass,
  Gamepad2,
  ImagePlus,
  Languages,
  Lock,
  PenLine,
  Plus,
  Power,
  PowerOff,
} from 'lucide-react'
import { toast } from 'sonner'
import { formatInteger } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState, MiniStat, Section } from '@/components/domain'
import { SettingRow } from '@/components/domain/SettingsKit'
import { Muted, Text } from '@/components/typography'
import { BulkDeepenPanel } from '@/features/bulk/BulkDeepenPanel'
import { GenesisRecord } from '@/features/onboarding/GenesisRecord'
import { type WorldState, useWorldState } from '@/features/overview/api'
import { useRuleValue } from '@/features/world-rules/api'
import { WorldSettingsForm } from './WorldSettingsForm'
import {
  useCheatEssence,
  useWorldSettings,
  useWriteMissingPrompts,
} from './api'

const MODEL_NAME = 'Claude Haiku'
const CHEAT_DEFAULT = 1000
const CHEAT_CAP_RULE = 'server.cheat_essence_max'
const QUICK_AMOUNTS = [100, 1000, 10000] as const

const LORE_LANGUAGE_LABEL: Record<string, string> = {
  english: 'English',
  turkish: 'Turkish',
}

function ModelAndLanguage({ state }: { state: WorldState }) {
  const language = state.world?.lore_language ?? 'english'
  return (
    <Section
      title='Model and lore language'
      description='Every role, from sons to Fate and the chronicler, thinks with one model.'
      surface='card'
      icon={Brain}
      tone='info'
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 md:grid-cols-3'>
        <MiniStat
          icon={Brain}
          label='Language model'
          value={MODEL_NAME}
          tone='info'
        />
        <MiniStat
          icon={state.llm_enabled ? Power : PowerOff}
          label='Model calls'
          value={state.llm_enabled ? 'Enabled' : 'Turned off'}
          tone={state.llm_enabled ? 'success' : 'warning'}
        />
        <MiniStat
          icon={Lock}
          label='Lore language'
          value={LORE_LANGUAGE_LABEL[language] ?? language}
          tone='gold'
          hint='Chosen once at genesis; it cannot be changed'
        />
      </div>
    </Section>
  )
}

function ImagePrompts({ state }: { state: WorldState }) {
  const write = useWriteMissingPrompts()
  const missing = state.promptless_count
  const reason = !state.llm_enabled
    ? 'Writing prompts needs the language model, which is turned off'
    : state.read_only
      ? 'A guest world is read-only'
      : missing === 0
        ? 'No record is missing a prompt'
        : 'Writing prompts'
  return (
    <Section
      title='Image prompts'
      description='Every record that can have an image gets a written prompt. Missing ones are completed at the start of each epoch.'
      surface='card'
      icon={ImagePlus}
      tone='verdigris'
      stretch
    >
      <MiniStat
        icon={PenLine}
        label='Records without a prompt'
        value={missing}
        tone={missing > 0 ? 'warning' : 'success'}
      />
      <ul className='flex min-w-0 flex-col gap-2'>
        <li className='flex min-w-0 items-center gap-2'>
          <Hourglass
            aria-hidden='true'
            className='size-icon-sm shrink-0 text-primary'
          />
          <Muted variant='caption'>
            Missing prompts are written by themselves when the next epoch
            begins.
          </Muted>
        </li>
        <li className='flex min-w-0 items-center gap-2'>
          {state.llm_enabled ? (
            <Power
              aria-hidden='true'
              className='size-icon-sm shrink-0 text-success'
            />
          ) : (
            <PowerOff
              aria-hidden='true'
              className='size-icon-sm shrink-0 text-warning'
            />
          )}
          <Muted variant='caption'>
            {state.llm_enabled
              ? 'The language model is on, so they can be written now.'
              : 'The language model is off; prompts wait until it is back.'}
          </Muted>
        </li>
      </ul>
      <div className='flex-1' />
      <Button
        variant='outline'
        className='w-full'
        disabled={
          !state.llm_enabled ||
          state.read_only ||
          missing === 0 ||
          write.isPending
        }
        disabledReason={reason}
        onClick={() =>
          write.mutate(undefined, {
            onSuccess: () => toast.success('Writing the missing prompts'),
            onError: (error) => toast.error(error.message),
          })
        }
      >
        <ImagePlus />
        Write all missing prompts now
      </Button>
    </Section>
  )
}

function CheatEssence({ state }: { state: WorldState }) {
  const cheat = useCheatEssence()
  const cap = useRuleValue(CHEAT_CAP_RULE)
  const [amount, setAmount] = useState(String(CHEAT_DEFAULT))
  const value = Number(amount)
  const invalid =
    !Number.isInteger(value) || value < 1 || (cap !== null && value > cap)
  const add = (count: number) =>
    cheat.mutate(count, {
      onSuccess: (result) =>
        toast.success(
          result.message || `+${formatInteger(count)} essence added`
        ),
      onError: (error) => toast.error(error.message),
    })
  const blocked = state.read_only
    ? 'A guest world is read-only'
    : cheat.isPending
      ? 'Adding essence'
      : null
  return (
    <Section
      title='Cheat: divine essence'
      description='Adds essence to the Creator at once. It is not written to the chronicle.'
      surface='card'
      icon={Droplet}
      tone='warning'
      stretch
    >
      <div className='grid min-w-0 grid-cols-1 gap-2 lg:grid-cols-3'>
        <MiniStat
          icon={Droplet}
          label='Essence now'
          value={state.creator?.essence ?? 0}
          tone='gold'
        />
        <div className='lg:col-span-2'>
          <SettingRow
            icon={Plus}
            tone='warning'
            label='Amount'
            description={
              cap === null
                ? 'A whole number of at least 1.'
                : `At most ${formatInteger(cap)} at once (World rules, The god's actions).`
            }
          >
            {(id) => (
              <>
                <Input
                  id={id}
                  type='number'
                  min={1}
                  max={cap ?? undefined}
                  inputMode='numeric'
                  value={amount}
                  aria-invalid={invalid}
                  onChange={(event) => setAmount(event.target.value)}
                  className='w-36'
                />
                <Button
                  disabled={invalid || blocked !== null}
                  disabledReason={
                    blocked ?? 'Enter a whole number within the limit'
                  }
                  onClick={() => add(value)}
                >
                  <Plus />
                  Add
                </Button>
              </>
            )}
          </SettingRow>
        </div>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        <Muted variant='caption'>Quick:</Muted>
        {QUICK_AMOUNTS.filter((count) => cap === null || count <= cap).map(
          (count) => (
            <Button
              key={count}
              size='sm'
              variant='outline'
              disabled={blocked !== null}
              disabledReason={blocked ?? undefined}
              onClick={() => add(count)}
            >
              <Droplet />
              {`+${formatInteger(count)}`}
            </Button>
          )
        )}
      </div>
    </Section>
  )
}

export function GameSettings() {
  const state = useWorldState()
  const hasWorld = Boolean(state.data?.world)
  const settings = useWorldSettings(hasWorld)
  if (state.isPending) return <Skeleton className='h-48 w-full' />
  if (state.isError)
    return <Text tone='destructive'>{state.error.message}</Text>
  if (!hasWorld)
    return (
      <EmptyState
        icon={Gamepad2}
        title='No world to configure'
        description='Game settings belong to a world. They appear here after genesis.'
      />
    )
  const data = state.data
  return (
    <div className='flex min-w-0 flex-col gap-6'>
      <div className='grid min-w-0 grid-cols-2 gap-2 lg:grid-cols-4'>
        <MiniStat
          icon={Droplet}
          label='Essence'
          value={data.creator?.essence ?? 0}
          tone='gold'
        />
        <MiniStat
          icon={data.llm_enabled ? Power : PowerOff}
          label='Model'
          value={data.llm_enabled ? 'On' : 'Off'}
          tone={data.llm_enabled ? 'success' : 'warning'}
        />
        <MiniStat
          icon={Languages}
          label='Lore language'
          value={
            LORE_LANGUAGE_LABEL[data.world?.lore_language ?? 'english'] ??
            data.world?.lore_language ??
            ''
          }
          tone='info'
        />
        <MiniStat
          icon={PenLine}
          label='Prompts missing'
          value={data.promptless_count}
          tone={data.promptless_count > 0 ? 'warning' : 'success'}
        />
      </div>
      <ModelAndLanguage state={data} />
      {settings.isPending && <Skeleton className='h-48 w-full' />}
      {settings.isError && (
        <Text tone='destructive'>{settings.error.message}</Text>
      )}
      {settings.data && (
        <WorldSettingsForm
          key={JSON.stringify(settings.data)}
          settings={settings.data}
          readOnly={data.read_only}
        />
      )}
      <BulkDeepenPanel />
      <div className='grid min-w-0 grid-cols-1 gap-6 xl:grid-cols-2'>
        <ImagePrompts state={data} />
        <CheatEssence state={data} />
      </div>
      <GenesisRecord />
    </div>
  )
}
