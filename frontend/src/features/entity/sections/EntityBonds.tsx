import { useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, Link2, Plus, Scissors } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { formatInteger } from '@/lib/format'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ConfirmDialog,
  EmptyState,
  EntityLink,
  ExpandableText,
  FormRow,
  PagedList,
  Section,
  Paged,
} from '@/components/domain'
import { PageControls } from '@/components/domain/PageControls'
import { RecordCombobox } from '@/components/domain/RecordCombobox'
import { Label, Muted, Text } from '@/components/typography'
import { drawerKindOf } from '@/features/chronicle/linkTargets'
import { type EntityContext } from '../actions/context'
import { humanize } from '../actions/schema'
import { useLoreMutation } from '../api/mutations'
import { useCatalogue, useEntityBonds, useNames } from '../api/queries'
import { type BondView } from '../api/types'
import { BOND_DESCRIPTION_MAX, BOND_PAGE_SIZE } from '../constants'
import { groupBonds } from './bondGroups'

type EntityBondsProps = {
  ctx: EntityContext
  readOnlyReason: string | null
}

function BondOther({ bond }: { bond: BondView }) {
  const other = bond.other
  if (!other) return <Text as='span'>Something forgotten</Text>
  const kind = drawerKindOf(other.kind)
  if (!kind) return <Text as='span'>{other.name}</Text>
  return (
    <EntityLink
      kind={kind}
      id={kind === 'creator' ? undefined : String(other.id)}
      showIcon={other.kind !== 'entity'}
    >
      {other.name}
    </EntityLink>
  )
}

function BondChip({
  bond,
  blocked,
  onBreak,
}: {
  bond: BondView
  blocked: string | null
  onBreak: () => void
}) {
  const past = bond.state === 'past'
  return (
    <li className='flex min-w-0 items-start gap-2 rounded-md border bg-card px-2.5 py-1.5'>
      <div className='flex min-w-0 flex-1 flex-col gap-0.5'>
        <Text as='div' tone={past ? 'muted' : 'default'}>
          {past && (
            <Text as='span' tone='muted'>
              formerly{' '}
            </Text>
          )}
          <BondOther bond={bond} />
        </Text>
        {bond.description && (
          <ExpandableText variant='caption' tone='muted' lines={2}>
            {bond.description}
          </ExpandableText>
        )}
      </div>
      {bond.kind !== 'inside' && !bond.derived && (
        <Button
          variant='ghost'
          size='icon-sm'
          aria-label='Break this bond'
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={onBreak}
        >
          <Scissors />
        </Button>
      )}
    </li>
  )
}

function DebtCard({ bond, selfName }: { bond: BondView; selfName: string }) {
  const debtor = bond.outgoing ? selfName : (bond.other?.name ?? 'Someone')
  const creditor = bond.outgoing ? (bond.other?.name ?? 'someone') : selfName
  const overdue = bond.debt_status === 'overdue'
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border px-3 py-2'>
      <Text as='span' className='min-w-0 flex-1'>
        {`${debtor} owes ${creditor} ${bond.debt_amount !== null ? formatInteger(bond.debt_amount) : ''} ${bond.debt_what ?? ''}`.trim()}
      </Text>
      {bond.debt_due_epoch !== null && (
        <Badge size='sm' variant={overdue ? 'destructive' : 'outline'}>
          {overdue
            ? `Overdue · epoch ${bond.debt_due_epoch}`
            : `Due epoch ${bond.debt_due_epoch}`}
        </Badge>
      )}
      {bond.debt_status && !overdue && bond.debt_status !== 'open' && (
        <Badge size='sm' variant='secondary'>
          {humanize(bond.debt_status)}
        </Badge>
      )}
    </li>
  )
}

function CreateBondForm({ ctx, readOnlyReason }: EntityBondsProps) {
  const catalogue = useCatalogue()
  const names = useNames()
  const [direction, setDirection] = useState<'out' | 'in'>('out')
  const [kind, setKind] = useState<string | null>(null)
  const [target, setTarget] = useState<number | null>(null)
  const [description, setDescription] = useState('')
  const kinds = useMemo(
    () =>
      [...(catalogue.data?.bond_kinds ?? [])]
        .filter((item) => item.key !== 'inside')
        .sort((left, right) => left.label.localeCompare(right.label)),
    [catalogue.data]
  )
  const options = useMemo(
    () =>
      (names.data ?? [])
        .filter(
          (entry) =>
            entry.id !== ctx.entity.id &&
            (entry.kind === 'entity' || entry.kind === 'son') &&
            entry.status !== 'rejected'
        )
        .map((entry) => ({
          value: String(entry.id),
          label: entry.name,
          hint: entry.kind === 'son' ? 'Son' : humanize(entry.type),
        })),
    [names.data, ctx.entity.id]
  )
  const create = useLoreMutation({
    run: () =>
      unwrap(
        api.POST('/api/links', {
          body: {
            source_id: direction === 'out' ? ctx.entity.id : (target ?? 0),
            target_id: direction === 'out' ? (target ?? 0) : ctx.entity.id,
            kind: kind as never,
            description: description.trim() || null,
          },
        })
      ),
    success: 'Bond created',
    onDone: () => {
      setTarget(null)
      setDescription('')
    },
  })
  const reason =
    readOnlyReason ??
    (kind === null ? 'Choose the bond.' : null) ??
    (target === null ? 'Choose the other side.' : null) ??
    (create.isPending ? 'Working on it.' : null)
  return (
    <div className='flex min-w-0 flex-col gap-3'>
      <FormRow label='Direction'>
        {(id) => (
          <Select
            value={direction}
            onValueChange={(value) => setDirection(value as 'out' | 'in')}
          >
            <SelectTrigger id={id} className='w-full'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value='out'>{`${ctx.entity.name} → the other`}</SelectItem>
              <SelectItem value='in'>{`The other → ${ctx.entity.name}`}</SelectItem>
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='Bond'>
        {(id) => (
          <Select value={kind ?? undefined} onValueChange={setKind}>
            <SelectTrigger id={id} className='w-full'>
              <SelectValue placeholder='Choose a bond' />
            </SelectTrigger>
            <SelectContent>
              {kinds.map((item) => (
                <SelectItem key={item.key} value={item.key}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </FormRow>
      <FormRow label='The other side'>
        {(id) => (
          <RecordCombobox
            id={id}
            options={options}
            value={target === null ? null : String(target)}
            onChange={(value) =>
              setTarget(value === null ? null : Number(value))
            }
            placeholder='Choose a record or a son'
            aria-label='The other side'
          />
        )}
      </FormRow>
      <FormRow
        label='Description'
        description='Optional; for example 12 silver, due epoch 15'
      >
        {(id) => (
          <Input
            id={id}
            maxLength={BOND_DESCRIPTION_MAX}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        )}
      </FormRow>
      <Button
        className='self-start'
        disabled={reason !== null}
        disabledReason={reason ?? undefined}
        onClick={() => create.mutate()}
      >
        <Link2 />
        Create bond
      </Button>
    </div>
  )
}

export function EntityBonds({ ctx, readOnlyReason }: EntityBondsProps) {
  const [offset, setOffset] = useState(0)
  const [breaking, setBreaking] = useState<BondView | null>(null)
  const catalogue = useCatalogue()
  const page = useEntityBonds(ctx.entity.id, offset, BOND_PAGE_SIZE)
  const remove = useLoreMutation({
    run: (bondId: number) =>
      unwrap(
        api.DELETE('/api/links/{bond_id}', {
          params: { path: { bond_id: bondId } },
        })
      ),
    success: 'Bond broken',
  })
  const labelOf = (kind: string) =>
    catalogue.data?.bond_kinds.find((item) => item.key === kind)?.label ??
    humanize(kind)
  const items = page.data?.items ?? []
  const total = page.data?.total ?? ctx.detail.bond_total
  const past = items.filter((bond) => bond.state === 'past').length
  const debts = items.filter(
    (bond) => bond.kind === 'owes' && bond.debt_amount !== null
  )
  const groups = groupBonds(items.filter((bond) => !debts.includes(bond)))
  const blocked = readOnlyReason ?? (remove.isPending ? 'Working on it.' : null)
  return (
    <Section
      id='section-bonds'
      title={`Bonds ${formatInteger(total)}`}
      description={
        past > 0
          ? `${formatInteger(past)} on this page are past bonds.`
          : undefined
      }
    >
      {page.isPending && <Skeleton className='h-textarea w-full' />}
      {page.isError && <Text tone='destructive'>{page.error.message}</Text>}
      {page.isSuccess && items.length === 0 && (
        <EmptyState
          size='compact'
          icon={Link2}
          title='No bonds'
          description='Nothing is bound to this record yet.'
        />
      )}
      {debts.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>Debts and receivables</Label>
          <PagedList
            items={debts}
            initial={4}
            noun={['debt', 'debts']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(bond) => bond.id}
          >
            {(bond) => <DebtCard bond={bond} selfName={ctx.entity.name} />}
          </PagedList>
        </div>
      )}
      <Paged items={groups}>
        {(group) => (
          <div key={group.key} className='flex min-w-0 flex-col gap-2'>
            <div className='flex min-w-0 items-center gap-2'>
              {group.outgoing ? (
                <ArrowRight
                  aria-hidden='true'
                  className='size-icon-sm text-muted-foreground'
                />
              ) : (
                <ArrowLeft
                  aria-hidden='true'
                  className='size-icon-sm text-muted-foreground'
                />
              )}
              <Text
                as='span'
                weight='medium'
                className='min-w-0 flex-1'
                truncate
              >
                {group.outgoing
                  ? labelOf(group.kind)
                  : `${labelOf(group.kind)} (toward it)`}
              </Text>
              <Muted variant='caption'>
                {formatInteger(group.bonds.length)}
              </Muted>
            </div>
            <PagedList
              items={group.bonds}
              initial={6}
              noun={['bond', 'bonds']}
              className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
              itemKey={(bond) => bond.id}
            >
              {(bond) => (
                <BondChip
                  bond={bond}
                  blocked={blocked}
                  onBreak={() => setBreaking(bond)}
                />
              )}
            </PagedList>
          </div>
        )}
      </Paged>
      <PageControls
        offset={offset}
        limit={BOND_PAGE_SIZE}
        total={total}
        onChange={setOffset}
        label='Bond pages'
        busy={page.isFetching}
      />
      <Collapsible className='flex min-w-0 flex-col gap-3'>
        <CollapsibleTrigger asChild>
          <Button variant='outline' className='self-start'>
            <Plus />
            Create a bond
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CreateBondForm ctx={ctx} readOnlyReason={readOnlyReason} />
        </CollapsibleContent>
      </Collapsible>
      <ConfirmDialog
        open={breaking !== null}
        onOpenChange={(open) => !open && setBreaking(null)}
        title='Break this bond?'
        desc={
          breaking
            ? `${labelOf(breaking.kind)} between ${ctx.entity.name} and ${breaking.other?.name ?? 'the other side'} will end.`
            : ''
        }
        destructive
        confirmText='Break'
        isLoading={remove.isPending}
        handleConfirm={() => {
          if (breaking) remove.mutate(breaking.id)
          setBreaking(null)
        }}
      />
    </Section>
  )
}
