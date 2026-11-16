import { Link } from '@tanstack/react-router'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { EntityLink, PagedList, Section } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { type EntityContext } from '../actions/context'
import { type BondView } from '../api/types'

const RELATION_KINDS: Record<
  string,
  { label: string; tone: 'success' | 'destructive' | 'warning' | 'outline' }
> = {
  ally: { label: 'Ally', tone: 'success' },
  trades_with: { label: 'Trades with', tone: 'outline' },
  truce: { label: 'Truce', tone: 'warning' },
  enemy: { label: 'Enemy', tone: 'destructive' },
  rival: { label: 'Rival', tone: 'warning' },
  pays_tribute: { label: 'Tribute', tone: 'warning' },
  holds_captive: { label: 'Holds captive', tone: 'warning' },
}

function WarRow({ bond, selfId }: { bond: BondView; selfId: number }) {
  const ongoing = bond.state === 'active'
  const war = bond.other
  return (
    <li className='flex min-w-0 flex-wrap items-center gap-2'>
      <Badge size='sm' variant={ongoing ? 'destructive' : 'secondary'}>
        {ongoing
          ? 'Ongoing'
          : bond.role
            ? bond.role.replace('_', ' ')
            : 'Ended'}
      </Badge>
      {war && war.id !== selfId ? (
        <EntityLink kind='entity' id={String(war.id)}>
          {war.name}
        </EntityLink>
      ) : (
        <Text as='span'>{war?.name ?? 'A war'}</Text>
      )}
      <Muted as='span' variant='caption'>{`since epoch ${bond.epoch}`}</Muted>
      {bond.war_id !== null && (
        <Button variant='ghost' size='sm' asChild>
          <Link to='/wars' search={{ war: bond.war_id }}>
            Open the war
          </Link>
        </Button>
      )}
    </li>
  )
}

export function EntityRelations({ ctx }: { ctx: EntityContext }) {
  const wars = ctx.bonds.filter(
    (bond) => bond.kind === 'party_to' && bond.war_id !== null
  )
  const relations = ctx.bonds.filter(
    (bond) =>
      RELATION_KINDS[bond.kind] &&
      bond.other &&
      bond.state !== 'hidden_rejected'
  )
  if (wars.length === 0 && relations.length === 0) return null
  return (
    <Section id='section-relations' title='Wars and relations'>
      {wars.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>{`Wars ${wars.length}`}</Label>
          <PagedList
            items={wars}
            initial={5}
            noun={['war', 'wars']}
            className='flex min-w-0 flex-col gap-2'
            itemKey={(bond) => bond.id}
          >
            {(bond) => <WarRow bond={bond} selfId={ctx.entity.id} />}
          </PagedList>
        </div>
      )}
      {relations.length > 0 && (
        <div className='flex min-w-0 flex-col gap-2'>
          <Label variant='overline'>{`Relations with others ${relations.length}`}</Label>
          <PagedList
            items={relations}
            initial={10}
            noun={['relation', 'relations']}
            className='grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2'
            itemKey={(bond) => bond.id}
          >
            {(bond) => {
              const spec = RELATION_KINDS[bond.kind]
              const other = bond.other
              return (
                <li className='flex min-w-0 items-center gap-2 rounded-md border surface-sheen border-gild/60 bg-card px-2.5 py-1.5'>
                  <Badge
                    size='sm'
                    variant={bond.state === 'past' ? 'secondary' : spec.tone}
                  >
                    {bond.state === 'past'
                      ? `Once ${spec.label.toLowerCase()}`
                      : spec.label}
                  </Badge>
                  {other && other.kind === 'entity' ? (
                    <EntityLink kind='entity' id={String(other.id)}>
                      {other.name}
                    </EntityLink>
                  ) : (
                    <Text as='span'>{other?.name}</Text>
                  )}
                </li>
              )
            }}
          </PagedList>
        </div>
      )}
    </Section>
  )
}
