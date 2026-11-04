import {
  BookOpen,
  Coins,
  Gem,
  Languages,
  Megaphone,
  Mic,
  PenLine,
  Sprout,
  Target,
} from 'lucide-react'
import { KpiTile, Paged } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import {
  AdjustBlock,
  DictField,
  LoreAdjust,
  LoreCard,
  LoreFields,
  LoreHero,
  NamedChip,
  RefChip,
  RoleRow,
  ShiftChips,
  Who,
} from '../LoreFields'
import { KPI_GRID, LORE_GRID, MEDIUMS, PERCENT, VALUES, lookup } from '../model'
import { ArtControls } from './ArtControls'
import { type Card } from './shared'

export function ArtworkPanel({
  id,
  card,
  blocked,
}: {
  id: number
  card: Card<'artwork'>
  blocked: string | null
}) {
  const medium = lookup(MEDIUMS, card.medium)
  return (
    <div data-surface='ArtworkCard' className='flex min-w-0 flex-col gap-4'>
      <LoreHero spec={medium} kicker='A work of art'>
        <NamedChip
          spec={
            card.performed
              ? { label: 'Performed aloud', icon: Mic, tone: 'info' }
              : { label: 'Kept as an object', icon: Gem, tone: 'muted' }
          }
        />
        {card.propaganda && (
          <NamedChip
            spec={{ label: 'Propaganda', icon: Megaphone, tone: 'warning' }}
          />
        )}
        <RefChip icon={Languages} label='In' item={card.language} />
      </LoreHero>
      <div className={KPI_GRID}>
        <KpiTile
          label='Quality'
          value={card.quality}
          icon={medium.icon}
          hint='The mastery in it'
          meter={{ value: card.quality, max: PERCENT, label: 'Quality' }}
        />
        <KpiTile
          label='Copies'
          value={card.copies}
          icon={BookOpen}
          tone='info'
          hint='Copies made carry it further'
        />
        <KpiTile
          label='Translations'
          value={card.translations.length}
          icon={Languages}
          tone='verdigris'
          hint='Tongues it has been carried into'
        />
        <KpiTile
          label='Propaganda'
          value={card.propaganda ? 'Yes' : 'No'}
          icon={Megaphone}
          tone={card.propaganda ? 'warning' : 'muted'}
          hint='Propaganda presses its message on all who hear it'
        />
      </div>
      <div className={LORE_GRID}>
        <LoreCard title='Its makers and subject' icon={PenLine}>
          {!card.author && !card.subject && !card.patron ? (
            <Muted>Its maker is forgotten.</Muted>
          ) : (
            <div className='flex min-w-0 flex-col gap-2.5'>
              {card.author && (
                <RoleRow icon={PenLine} tone='gold' label='By'>
                  <Who item={card.author} />
                </RoleRow>
              )}
              {card.subject && (
                <RoleRow icon={Target} tone='info' label='Of'>
                  <Who item={card.subject} />
                </RoleRow>
              )}
              {card.patron && (
                <RoleRow icon={Coins} tone='gold' label='For'>
                  <Who item={card.patron} />
                </RoleRow>
              )}
            </div>
          )}
        </LoreCard>
        <LoreCard title='What it stirs' icon={Sprout} tone='success'>
          <ShiftChips
            entries={card.message}
            table={VALUES}
            empty='It stirs no value.'
          />
          {card.translations.length > 0 && (
            <div className='flex min-w-0 flex-col gap-1.5'>
              <Label>Translated into</Label>
              <div className='flex min-w-0 flex-wrap gap-1.5'>
                <Paged items={card.translations}>
                  {(item) => (
                    <RefChip
                      key={item.id}
                      icon={Languages}
                      label=''
                      item={item}
                    />
                  )}
                </Paged>
              </div>
            </div>
          )}
        </LoreCard>
      </div>
      <LoreAdjust
        entityId={id}
        noun='work'
        locked={card.locked}
        blocked={blocked}
      >
        <AdjustBlock title='The work' icon={medium.icon}>
          <LoreFields
            entityId={id}
            surface='ArtworkForm'
            fields={[
              { key: 'medium', kind: 'enum', table: MEDIUMS },
              { key: 'quality', kind: 'number', min: 0, max: PERCENT },
              { key: 'copies', kind: 'number', min: 0 },
              { key: 'performed', kind: 'bool' },
              { key: 'propaganda', kind: 'bool' },
            ]}
            current={card}
            blocked={blocked}
          />
        </AdjustBlock>
        <AdjustBlock title='What it stirs' icon={Sprout}>
          <DictField
            entityId={id}
            spec={{ key: 'message', label: 'Its message', value: card.message }}
            blocked={blocked}
            table={VALUES}
          />
        </AdjustBlock>
        <ArtControls id={id} card={card} blocked={blocked} />
      </LoreAdjust>
    </div>
  )
}
