import { useMemo, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Medallion, Paged, ShapeFields, useShape } from '@/components/domain'
import { Label, Text } from '@/components/typography'
import { ForgeCard } from '@/features/cosmography/parts'
import { useNames } from '@/features/cosmos/api'
import { StepButton } from '@/features/cycles/parts'
import { why } from '@/features/dominion/model'
import { RecordRowsSection } from '@/features/entity/sections/RecordRowsSection'
import { ThingPicker } from '@/features/gatherings/parts'
import { useMadeAction } from '@/features/minds/api'
import { ChoiceField } from '@/features/wars/military/parts'
import { LEAGUES } from './families'
import { LEAGUE_AIMS, LEAGUE_ICON, LEAGUE_VOTE_BASES } from './labels'

type Aim = keyof typeof LEAGUE_AIMS
type Basis = keyof typeof LEAGUE_VOTE_BASES

function AimToggles({
  value,
  onChange,
  blocked,
}: {
  value: Aim[]
  onChange: (next: Aim[]) => void
  blocked: string | null
}) {
  return (
    <div className='col-span-full flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>What the league is for</Label>
      <ul className='grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-3'>
        <Paged items={Object.keys(LEAGUE_AIMS) as Aim[]} as='li'>
          {(aim) => {
            const active = value.includes(aim)
            const named = LEAGUE_AIMS[aim]
            return (
              <li key={aim} className='min-w-0'>
                <Button
                  variant='outline'
                  size='tile'
                  aria-pressed={active}
                  disabled={blocked !== null}
                  disabledReason={blocked ?? undefined}
                  onClick={() =>
                    onChange(
                      active
                        ? value.filter((item) => item !== aim)
                        : [...value, aim]
                    )
                  }
                  className={cn(active && 'border-primary/50 bg-primary/10')}
                >
                  <Medallion
                    icon={named.icon}
                    tone={active ? named.tone : 'muted'}
                    size='sm'
                  />
                  <Text as='span' weight='semibold' truncate>
                    {named.label}
                  </Text>
                </Button>
              </li>
            )
          }}
        </Paged>
      </ul>
    </div>
  )
}

function LeagueControls({ nodeId }: { nodeId: number }) {
  const names = useNames()
  const entry = useMemo(
    () => (names.data ?? []).find((item) => item.id === nodeId),
    [names.data, nodeId]
  )
  const type = entry?.kind === 'entity' ? entry.type : null
  const isRealm = type === 'polity'
  const isLeague = type === 'league'
  const [first, setFirst] = useState<number | null>(null)
  const [second, setSecond] = useState<number | null>(null)
  const [aims, setAims] = useState<Aim[]>(['defence'])
  const [basis, setBasis] = useState<Basis>('one_member_one_vote')
  const naming = useShape()
  const founding = useMadeAction(
    'league:found',
    (_: void) => ({
      founder_id: nodeId,
      partner_ids: [first ?? -1, second ?? -1],
      aims,
      vote_basis: basis,
      ...naming.body,
    }),
    'A league of realms is founded'
  )
  const dissolving = useMadeAction(
    'league:dissolve',
    (_: void) => ({ league_id: nodeId }),
    'The league is dissolved'
  )
  const notRealm = names.isPending
    ? 'Reading the record'
    : isRealm
      ? null
      : 'Only a realm founds a league; open a realm to found one'
  const partners =
    first === null || second === null
      ? 'Pick two other realms to found it with'
      : first === second || first === nodeId || second === nodeId
        ? 'A league joins three different realms'
        : null
  const aimless = aims.length ? null : 'Choose at least one aim'
  const notLeague = isLeague ? null : 'Only a league can be dissolved'
  return (
    <ForgeCard
      icon={LEAGUE_ICON}
      tone='gold'
      title={
        entry ? `Found a league with ${entry.name}` : 'Found a league of realms'
      }
      note='Members pay dues, vote by the basis you choose and are bound by what passes as far as they obey; the aims decide its organs.'
      columns={3}
      action={
        <div className='flex flex-wrap gap-2'>
          <StepButton
            icon={LEAGUE_ICON}
            label='Found it'
            variant='default'
            busy={why(notRealm ?? partners ?? aimless, founding.isPending)}
            onClick={() => founding.mutate()}
          />
          <StepButton
            icon={Trash2}
            label='Dissolve this league'
            busy={why(notLeague, dissolving.isPending)}
            onClick={() => dissolving.mutate()}
          />
        </div>
      }
    >
      <div className='col-span-full min-w-0'>
        <ShapeFields
          shape={naming.shape}
          onChange={naming.setShape}
          blocked={notRealm}
        />
      </div>
      <ThingPicker
        label='Second realm'
        value={first}
        onChange={setFirst}
        blocked={notRealm}
        types={['polity']}
      />
      <ThingPicker
        label='Third realm'
        value={second}
        onChange={setSecond}
        blocked={notRealm}
        types={['polity']}
      />
      <ChoiceField
        label='How it decides'
        value={basis}
        table={LEAGUE_VOTE_BASES}
        blocked={notRealm}
        onPick={(next) => setBasis(next as Basis)}
      />
      <AimToggles value={aims} onChange={setAims} blocked={notRealm} />
    </ForgeCard>
  )
}

export function LeaguesSection({ nodeId }: { nodeId: number }) {
  return (
    <RecordRowsSection
      nodeId={nodeId}
      family={LEAGUES}
      controls={<LeagueControls nodeId={nodeId} />}
    />
  )
}
