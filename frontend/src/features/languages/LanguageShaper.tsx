import { useState } from 'react'
import { AudioLines, Dices, PenLine, Save } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { FormRow, PagedList, Section } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { humanize } from '@/features/entity/actions/schema'
import {
  WRITING_SYSTEMS,
  useEditLanguage,
  useRedrawSignature,
  useSampleNames,
} from './api'
import {
  type Draft,
  type ScriptChoice,
  UNWRITTEN,
  changesOf,
  hasChanges,
  initialDraft,
} from './languageEdit'
import { type LanguageNode } from './languageFamilies'

const ALPHABET_MAX = 64
const LETTERS_MAX = 24

export function LanguageShaper({
  node,
  readOnlyReason,
}: {
  node: LanguageNode
  readOnlyReason: string | null
}) {
  const [draft, setDraft] = useState(() => initialDraft(node))
  const [salt, setSalt] = useState(0)
  const edit = useEditLanguage()
  const redraw = useRedrawSignature()
  const preview = useSampleNames(node.language.id)
  const update = (patch: Partial<Draft>) =>
    setDraft((current) => ({ ...current, ...patch }))
  const change = changesOf(node, draft)
  const signatureInvalid =
    !draft.clearSignature &&
    draft.consonants.trim() === '' &&
    (draft.cluster.trim() !== '' || draft.ending.trim() !== '')
  const reason =
    readOnlyReason ??
    (signatureInvalid ? 'A signature needs its consonants.' : null) ??
    (!hasChanges(change) ? 'Nothing has changed.' : null) ??
    (edit.isPending ? 'Working on it.' : null)
  const roll = () => {
    const next = salt + 1
    setSalt(next)
    preview.mutate(String(next))
  }
  return (
    <Section
      id='languages-shape'
      title='Shape this tongue'
      description='Its script, letters, taught names and signature sound. Names born from now on follow them.'
      surface='card'
      level={3}
    >
      <form
        className='flex min-w-0 flex-col gap-3'
        onSubmit={(event) => {
          event.preventDefault()
          if (reason === null)
            edit.mutate(change, {
              onSuccess: () =>
                update({
                  names: '',
                  forgetNames: false,
                  clearSignature: false,
                }),
            })
        }}
      >
        <FormRow label='Script'>
          {(id) => (
            <Select
              value={draft.script}
              onValueChange={(value) =>
                update({ script: value as ScriptChoice })
              }
            >
              <SelectTrigger id={id} className='w-full'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={UNWRITTEN}>Unwritten</SelectItem>
                {WRITING_SYSTEMS.map((system) => (
                  <SelectItem key={system} value={system}>
                    {humanize(system)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
        <FormRow
          label='Alphabet'
          description='The letters its names may use; empty falls back to the world alphabet.'
        >
          {(id) => (
            <Input
              id={id}
              maxLength={ALPHABET_MAX}
              value={draft.alphabet}
              onChange={(event) => update({ alphabet: event.target.value })}
            />
          )}
        </FormRow>
        <FormRow
          label='Taught names'
          description='One per line; they teach the tongue its sound.'
        >
          {(id) => (
            <Textarea
              id={id}
              value={draft.names}
              disabled={draft.forgetNames}
              placeholder='One name per line'
              onChange={(event) => update({ names: event.target.value })}
            />
          )}
        </FormRow>
        <FormRow label='Forget the taught names'>
          {(id) => (
            <Switch
              id={id}
              checked={draft.forgetNames}
              onCheckedChange={(checked) => update({ forgetNames: checked })}
            />
          )}
        </FormRow>
        <FormRow
          label='Signature consonants'
          description='Consonants its names lean on.'
        >
          {(id) => (
            <Input
              id={id}
              maxLength={LETTERS_MAX}
              value={draft.consonants}
              disabled={draft.clearSignature}
              onChange={(event) => update({ consonants: event.target.value })}
            />
          )}
        </FormRow>
        <FormRow label='Signature cluster' description='Optional'>
          {(id) => (
            <Input
              id={id}
              maxLength={LETTERS_MAX}
              value={draft.cluster}
              disabled={draft.clearSignature}
              onChange={(event) => update({ cluster: event.target.value })}
            />
          )}
        </FormRow>
        <FormRow label='Signature ending' description='Optional'>
          {(id) => (
            <Input
              id={id}
              maxLength={LETTERS_MAX}
              value={draft.ending}
              disabled={draft.clearSignature}
              onChange={(event) => update({ ending: event.target.value })}
            />
          )}
        </FormRow>
        <FormRow label='Drop the signature'>
          {(id) => (
            <Switch
              id={id}
              checked={draft.clearSignature}
              disabled={node.signature === null}
              onCheckedChange={(checked) => update({ clearSignature: checked })}
            />
          )}
        </FormRow>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            type='submit'
            disabled={reason !== null}
            disabledReason={reason ?? undefined}
          >
            <Save />
            Save the tongue
          </Button>
          <Button
            type='button'
            variant='outline'
            disabled={readOnlyReason !== null || redraw.isPending}
            disabledReason={readOnlyReason ?? 'Working on it.'}
            onClick={() => redraw.mutate(node.language.id)}
          >
            <PenLine />
            Redraw the signature
          </Button>
        </div>
      </form>
      <div className='flex min-w-0 flex-col gap-2'>
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Label variant='overline'>Hear it speak</Label>
          <Button
            type='button'
            variant='outline'
            size='sm'
            disabled={preview.isPending}
            disabledReason='Listening.'
            onClick={roll}
          >
            {preview.data ? <Dices /> : <AudioLines />}
            {preview.data ? 'Other names' : 'Sound out names'}
          </Button>
        </div>
        {preview.data ? (
          preview.data.names.length === 0 ? (
            <Muted variant='caption'>
              This tongue has too few sounds to name anything yet.
            </Muted>
          ) : (
            <PagedList
              items={preview.data.names}
              initial={12}
              noun={['entry', 'entries']}
              as='div'
              className='flex min-w-0 flex-wrap gap-2'
              itemKey={(name, index) => `${name}-${index}`}
            >
              {(name, index) => (
                <Badge key={`${name}-${index}`} variant='secondary'>
                  {name}
                </Badge>
              )}
            </PagedList>
          )
        ) : (
          <Muted variant='caption'>
            Names are only sounded out here; nothing is written to the world.
          </Muted>
        )}
      </div>
    </Section>
  )
}
