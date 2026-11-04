import { type ReactNode, useState } from 'react'
import { Link2, Unlink } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { type components } from '@/api/generated/schema'
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
import {
  EmptyState,
  EntityLink,
  ExpandableText,
  FormRow,
  Section,
  ShowMore,
  useShowMore,
  Paged,
} from '@/components/domain'
import { type DrawerKind } from '@/components/layout/drawer/drawerEntries'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { NamePicker } from '@/features/pantheon/NamePicker'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { useLabels } from '@/features/pantheon/labels'
import { type BondView } from './api'

type BondKind = components['schemas']['BondKind']
type NodeKind = components['schemas']['NodeKind']

const DRAWER_OF: Partial<Record<NodeKind, DrawerKind>> = {
  entity: 'entity',
  son: 'son',
  foreign_god: 'foreign-god',
  creator: 'creator',
}

export function NodeLink({
  node,
}: {
  node: { id: number; kind: NodeKind; name: string }
}) {
  const kind = DRAWER_OF[node.kind]
  if (!kind)
    return (
      <Text as='span' weight='medium'>
        {node.name}
      </Text>
    )
  if (kind === 'creator')
    return <EntityLink kind='creator'>{node.name}</EntityLink>
  return (
    <EntityLink kind={kind} id={String(node.id)}>
      {node.name}
    </EntityLink>
  )
}

const BONDS_SHOWN = 6

function BondGroup({
  list,
  renderBond,
}: {
  list: BondView[]
  renderBond: (bond: BondView) => ReactNode
}) {
  const page = useShowMore(list, BONDS_SHOWN)
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <ul className='flex min-w-0 flex-col gap-2'>
        {page.visible.map((bond) => renderBond(bond))}
      </ul>
      <ShowMore state={page} noun={['bond', 'bonds']} />
    </div>
  )
}

export function BondList({
  bonds,
  total,
  editable,
}: {
  bonds: BondView[]
  total: number
  editable: boolean
}) {
  const { bondKind } = useLabels()
  const { reason } = useGodGate()
  const remove = useGodAction({
    run: (bondId: number) =>
      unwrap(
        api.DELETE('/api/links/{bond_id}', {
          params: { path: { bond_id: bondId } },
        })
      ),
    success: 'The bond was broken',
  })
  const groups = new Map<string, BondView[]>()
  for (const bond of bonds) {
    const list = groups.get(bond.kind) ?? []
    list.push(bond)
    groups.set(bond.kind, list)
  }
  if (bonds.length === 0)
    return (
      <EmptyState
        icon={Link2}
        size='compact'
        title='No trace in the world yet'
        description='Bonds appear as he creates, blesses, curses and loves.'
      />
    )
  return (
    <div className='flex min-w-0 flex-col gap-4'>
      <Paged items={[...groups.entries()]}>
        {([kind, list]) => (
          <div key={kind} className='flex min-w-0 flex-col gap-2'>
            <Label variant='overline'>{`${bondKind(kind)} · ${list.length}`}</Label>
            <BondGroup
              list={list}
              renderBond={(bond) => (
                <li
                  key={bond.id}
                  className='flex min-w-0 flex-wrap items-center gap-2 rounded-md border bg-card px-2.5 py-1.5'
                >
                  <Label>{bond.outgoing ? '→' : '←'}</Label>
                  {bond.other ? (
                    <NodeLink node={bond.other} />
                  ) : (
                    <Muted>Unknown</Muted>
                  )}
                  {bond.state !== 'active' && (
                    <Badge size='sm' variant='secondary'>
                      Past
                    </Badge>
                  )}
                  <Label>{`Epoch ${bond.epoch}`}</Label>
                  {bond.description && (
                    <div className='basis-full'>
                      <ExpandableText variant='caption' tone='muted' lines={2}>
                        {bond.description}
                      </ExpandableText>
                    </div>
                  )}
                  {editable && bond.state === 'active' && (
                    <ActionButton
                      label='Break'
                      icon={Unlink}
                      size='sm'
                      variant='ghost'
                      blocked={reason()}
                      pending={remove.isPending}
                      confirm={{
                        title: 'Break this bond?',
                        description:
                          'The bond ends now and is recorded as past.',
                      }}
                      onRun={() => remove.mutate(bond.id)}
                    />
                  )}
                </li>
              )}
            />
          </div>
        )}
      </Paged>
      {total > bonds.length && (
        <Muted variant='caption'>{`Showing ${bonds.length} of ${total} bonds.`}</Muted>
      )}
    </div>
  )
}

export function CreateBondForm({ sourceId }: { sourceId: number }) {
  const { catalogue } = useLabels()
  const [kind, setKind] = useState<BondKind | ''>('')
  const [target, setTarget] = useState<string | null>(null)
  const [description, setDescription] = useState('')
  const { reason } = useGodGate()
  const create = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/links', {
          body: {
            source_id: sourceId,
            target_id: Number(target),
            kind: kind as BondKind,
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
  return (
    <Collapsible className='flex min-w-0 flex-col gap-3'>
      <CollapsibleTrigger asChild>
        <Button variant='ghost' size='sm' className='self-start'>
          <Link2 />
          Create a bond
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className='flex min-w-0 flex-col gap-3'>
        <FormRow label='Kind'>
          {(id) => (
            <Select
              value={kind}
              onValueChange={(value) => setKind(value as BondKind)}
            >
              <SelectTrigger id={id} className='w-full'>
                <SelectValue placeholder='Pick a kind of bond' />
              </SelectTrigger>
              <SelectContent>
                {(catalogue?.bond_kinds ?? [])
                  .filter((item) => item.key !== 'worships')
                  .map((item) => (
                    <SelectItem key={item.key} value={item.key}>
                      {item.label}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          )}
        </FormRow>
        <FormRow label='Target'>
          {(id) => (
            <NamePicker
              id={id}
              value={target}
              exclude={[sourceId]}
              onChange={(value) => setTarget(value)}
            />
          )}
        </FormRow>
        <FormRow label='Description'>
          {(id) => (
            <Input
              id={id}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          )}
        </FormRow>
        <div>
          <ActionButton
            label='Create bond'
            variant='default'
            blocked={
              reason() ??
              (!kind || !target ? 'Pick a kind and a target.' : null)
            }
            pending={create.isPending}
            onRun={() => create.mutate()}
          />
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

export function SonBonds({
  sonId,
  bonds,
  total,
}: {
  sonId: number
  bonds: BondView[]
  total: number
}) {
  const shown = bonds.filter(
    (bond) => !(bond.kind === 'worships' && !bond.outgoing)
  )
  return (
    <Section title='His hand in the world' level={3}>
      <BondList bonds={shown} total={total} editable />
      <CreateBondForm sourceId={sonId} />
    </Section>
  )
}
