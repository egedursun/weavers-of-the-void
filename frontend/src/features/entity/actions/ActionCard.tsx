import { useMemo, useState } from 'react'
import { ChevronDown, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ConfirmDialog, JobProgress } from '@/components/domain'
import { Muted, Text } from '@/components/typography'
import { useJob, useLoreMutation } from '../api/mutations'
import { type ActionCatalogueItem } from '../api/types'
import { ActionField } from './ActionField'
import { type EntityContext } from './context'
import { PENDING_REASON, fixedCost, useLoreGate } from './gate'
import { DEFAULT_PICKERS, type PickerData, type PickerSpec } from './pickers'
import { type RecordActionSpec } from './registry'
import {
  type FieldModel,
  type FieldValue,
  bodyOf,
  fieldsOf,
  humanize,
  initialValue,
  missingRequired,
} from './schema'
import { sendAction } from './send'

type ActionCardProps = {
  spec: RecordActionSpec
  item: ActionCatalogueItem
  ctx: EntityContext
  data: PickerData
}

function pickerFor(
  spec: RecordActionSpec,
  field: FieldModel
): PickerSpec | undefined {
  if (field.kind !== 'integer' || !field.key.endsWith('_id')) return undefined
  return (
    spec.pickers?.[field.key] ??
    DEFAULT_PICKERS[field.key] ?? { source: 'entity' }
  )
}

export function CostChip({ text }: { text: string }) {
  const amount = fixedCost(text)
  if (amount === 0) return null
  return (
    <Badge size='sm' variant='secondary' title={text}>
      <Sparkles />
      {amount ?? text}
    </Badge>
  )
}

function useInitialValues(
  fields: FieldModel[],
  spec: RecordActionSpec,
  ctx: EntityContext
): Record<string, FieldValue> {
  return useMemo(() => {
    const values: Record<string, FieldValue> = {}
    for (const field of fields) values[field.key] = initialValue(field)
    if (ctx.wars.length === 1 && 'war_id' in values && spec.self !== 'war_id')
      values.war_id = ctx.wars[0].warId
    return { ...values, ...(spec.defaults?.(ctx) ?? {}) }
  }, [fields, spec, ctx])
}

export function ActionCard({ spec, item, ctx, data }: ActionCardProps) {
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const fields = useMemo(() => fieldsOf(item.input_schema), [item.input_schema])
  const initial = useInitialValues(fields, spec, ctx)
  const [values, setValues] = useState<Record<string, FieldValue>>(initial)
  const gate = useLoreGate()
  const skip = useMemo(
    () =>
      new Set<string>([
        ...(spec.self === null ? [] : [spec.self]),
        ...(spec.hidden ?? []),
        ...(spec.omit?.(ctx) ?? []),
      ]),
    [spec, ctx]
  )
  const shown = fields.filter(
    (field) => !skip.has(field.key) && field.kind !== 'unsupported'
  )
  const mutation = useLoreMutation({
    run: (body: Record<string, FieldValue>) =>
      sendAction(spec.route, ctx.entity.id, spec.self, body),
    onDone: () => setValues(initial),
  })
  const job = useJob(mutation.jobId)
  const missing = missingRequired(fields, values, skip)
  const blocked =
    gate.reason({
      cost: fixedCost(item.cost),
      world: spec.world,
      llm: spec.llm,
    }) ??
    spec.blocked?.(ctx) ??
    (missing
      ? `Fill in ${spec.labels?.[missing.key] ?? humanize(missing.key)}.`
      : null) ??
    (mutation.isPending ? PENDING_REASON : null)
  const submit = () => {
    const hiddenValues = Object.fromEntries(
      (spec.hidden ?? []).map((key) => [key, values[key]])
    )
    const body = {
      ...bodyOf(fields, values, skip),
      ...hiddenValues,
    }
    mutation.mutate(body)
  }
  const Icon = spec.icon
  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      data-action-id={item.id}
      className='flex min-w-0 flex-col gap-3 rounded-md border surface-framed border-gild/70 bg-card p-3'
    >
      <CollapsibleTrigger asChild>
        <Button
          variant='ghost'
          className='w-full justify-start'
          aria-label={`${item.title}${item.cost !== 'Free' ? `, costs ${item.cost}` : ''}`}
        >
          <Icon />
          <span className='min-w-0 flex-1 truncate text-start'>
            {item.title}
          </span>
          <CostChip text={item.cost} />
          <ChevronDown
            className={
              open ? 'rotate-180 transition-transform' : 'transition-transform'
            }
          />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-4'>
        {fixedCost(item.cost) === null && (
          <Muted variant='caption'>{`Cost: ${item.cost}`}</Muted>
        )}
        {shown.length > 0 && (
          <div className='flex min-w-0 flex-col gap-3'>
            {shown.map((field) => (
              <ActionField
                key={field.key}
                field={field}
                label={spec.labels?.[field.key]}
                value={values[field.key] ?? null}
                onChange={(value) =>
                  setValues((current) => ({ ...current, [field.key]: value }))
                }
                picker={pickerFor(spec, field)}
                multiline={spec.multiline?.includes(field.key)}
                ctx={ctx}
                data={data}
                disabled={mutation.isPending}
              />
            ))}
          </div>
        )}
        {shown.length === 0 && (
          <Text tone='muted'>{`Acts on ${ctx.entity.name} directly.`}</Text>
        )}
        <div className='flex min-w-0 flex-wrap items-center gap-2'>
          <Button
            variant={spec.destructive ? 'destructive' : 'default'}
            disabled={blocked !== null}
            disabledReason={blocked ?? undefined}
            aria-busy={mutation.isPending || undefined}
            onClick={() => (spec.confirm ? setConfirming(true) : submit())}
          >
            <Icon />
            {item.title}
          </Button>
        </div>
        {job.data && <JobProgress job={job.data} title={item.title} />}
      </CollapsibleContent>
      {spec.confirm && (
        <ConfirmDialog
          open={confirming}
          onOpenChange={setConfirming}
          title={`${item.title}?`}
          desc={spec.confirm(ctx)}
          destructive={spec.destructive}
          confirmText={item.title}
          isLoading={mutation.isPending}
          handleConfirm={() => {
            setConfirming(false)
            submit()
          }}
        />
      )}
    </Collapsible>
  )
}
