import { Users } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  EmptyState,
  EntityLink,
  PagedList,
  Portrait,
  Section,
} from '@/components/domain'
import { Label } from '@/components/typography'
import { useSons } from '@/features/pantheon/api'
import { SON_STATUS_LABEL, useLabels } from '@/features/pantheon/labels'
import { mediaUrl } from '@/features/pantheon/media'
import { BondList, CreateBondForm } from '@/features/son/SonBonds'
import { type ForeignGodDetail } from './api'

export function ForeignGodRelations({ detail }: { detail: ForeignGodDetail }) {
  const { entityType } = useLabels()
  const sons = useSons()
  const bonds = detail.bonds.filter(
    (bond) => !(bond.kind === 'worships' && !bond.outgoing)
  )
  return (
    <>
      <Section title='Worshippers' level={3}>
        {detail.worshippers.length === 0 ? (
          <EmptyState
            icon={Users}
            size='compact'
            title='No community worships this god now'
            description='While awake, ownerless communities on this world turn to the god over time.'
          />
        ) : (
          <PagedList
            items={detail.worshippers}
            initial={8}
            noun={['worshipper', 'worshippers']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={({ entity }) => entity.id}
          >
            {({ entity, cover }) => (
              <li className='flex min-w-0 flex-wrap items-center gap-2'>
                <Portrait name={entity.name} src={mediaUrl(cover)} size='sm' />
                <EntityLink kind='entity' id={String(entity.id)}>
                  {entity.name}
                </EntityLink>
                <Label>
                  {[
                    entity.subtype ?? entityType(entity.entity_type),
                    `since Epoch ${entity.birth_epoch}`,
                  ].join(' · ')}
                </Label>
              </li>
            )}
          </PagedList>
        )}
      </Section>
      {detail.sons_here.length > 0 && (
        <Section title='Sons encountered' level={3}>
          <PagedList
            items={detail.sons_here}
            initial={8}
            noun={['son', 'sons']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(node) => node.id}
          >
            {(node) => {
              const view = sons.data?.find((item) => item.son.id === node.id)
              const status = view?.son.status
              return (
                <li className='flex min-w-0 flex-wrap items-center gap-2'>
                  <Portrait
                    name={node.name}
                    src={mediaUrl(view?.cover)}
                    size='sm'
                    rarity={view?.son.rarity}
                  />
                  <EntityLink kind='son' id={String(node.id)}>
                    {node.name}
                  </EntityLink>
                  <Label>Currently on this world</Label>
                  {status && status !== 'active' && (
                    <Badge size='sm' variant='secondary'>
                      {SON_STATUS_LABEL[status]}
                    </Badge>
                  )}
                </li>
              )
            }}
          </PagedList>
        </Section>
      )}
      <Section title='Bonds' level={3}>
        <BondList bonds={bonds} total={detail.bond_total} editable />
        <CreateBondForm sourceId={detail.god.id} />
      </Section>
    </>
  )
}
