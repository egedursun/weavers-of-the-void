import { useState } from 'react'
import { Hourglass, Pencil, Plus, Shapes, X } from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { EmptyState, Section, StatBar, Paged } from '@/components/domain'
import { Label, Muted } from '@/components/typography'
import { type AdjustGroup, AdjustStats } from '@/features/pantheon/AdjustStats'
import { useGodGate } from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { useVariants } from '@/features/world-rules/VariantForge'
import { RowAction } from '../actions/RowAction'
import { type Mind, type MindSkill, type SkillKind, useMind } from '../mind/api'
import {
  SKILLS_ICON,
  SKILL_FAMILIES,
  SKILL_ICONS,
  SKILL_SOURCES,
  named,
  plain,
} from '../mind/labels'
import { ControlPanel, MindCard, MindPicker } from '../mind/parts'

const PERCENT = 100
const SKILLED = 60
const TRAINED = 30
const WORKING = 'Working on it.'
const ALL_SKILLS: Record<string, string> = {
  blade: 'Blade',
  spear: 'Spear',
  axe: 'Axe',
  blunt: 'Mace and hammer',
  bow: 'Bow',
  sling: 'Sling',
  throwing: 'Throwing',
  shield: 'Shield',
  unarmed: 'Unarmed fighting',
  riding: 'Riding',
  mounted_combat: 'Mounted combat',
  siegecraft: 'Siegecraft',
  naval_combat: 'Naval combat',
  beast_handling: 'Beast handling',
  tactics: 'Tactics',
  strategy: 'Strategy',
  logistics: 'Logistics',
  leadership: 'Leadership',
  intimidation: 'Intimidation',
  oratory: 'Oratory',
  negotiation: 'Negotiation',
  intrigue: 'Intrigue',
  etiquette: 'Etiquette',
  deception: 'Deception',
  teaching: 'Teaching',
  smithing: 'Smithing',
  carpentry: 'Carpentry',
  masonry: 'Masonry',
  weaving: 'Weaving',
  pottery: 'Pottery',
  jewelling: 'Jewelling',
  shipwright: 'Shipwright',
  engineering: 'Engineering',
  alchemy: 'Alchemy',
  lore: 'Lore',
  medicine: 'Medicine',
  surgery: 'Surgery',
  astronomy: 'Astronomy',
  law: 'Law',
  theology: 'Theology',
  languages: 'Languages',
  writing: 'Writing',
  accounting: 'Accounting',
  hunting: 'Hunting',
  tracking: 'Tracking',
  foraging: 'Foraging',
  sailing: 'Sailing',
  navigation: 'Navigation',
  mountaineering: 'Mountaineering',
  swimming: 'Swimming',
  ritual: 'Ritual',
  prophecy: 'Prophecy',
  spellcraft: 'Spellcraft',
  spirit_speaking: 'Spirit-speaking',
}

function SkillRow({
  skill,
  blocked,
  onForget,
}: {
  skill: MindSkill
  blocked: string | null
  onForget: () => void
}) {
  const variants = useVariants()
  const kinds = (variants.data ?? [])
    .filter((item) => item.family === 'skill' && item.base === skill.skill)
    .map((item) => ({ value: String(item.id), label: item.name }))
  const madeKind = (variants.data ?? []).find(
    (item) => item.id === skill.variant_id
  )
  const spec = named(SKILL_ICONS, skill.skill)
  const hampered = skill.effective < skill.level
  return (
    <div className='flex min-w-0 flex-col gap-1'>
      <div className='flex min-w-0 items-center gap-2'>
        <div className='min-w-0 flex-1'>
          <StatBar
            label={skill.label}
            value={skill.level}
            max={PERCENT}
            icon={spec.icon}
            tone={
              skill.level >= SKILLED
                ? 'success'
                : skill.level >= TRAINED
                  ? 'default'
                  : 'muted'
            }
          />
        </div>
        <RowAction
          path='/api/actions/mind:skill_edit'
          icon={Pencil}
          label={`Edit ${skill.label}`}
          iconOnly
          fixed={{ skill_id: skill.id }}
          defaults={{
            level: skill.level,
            xp: skill.xp,
            peak: skill.peak,
            subject_id: skill.subject?.id ?? null,
            clear_subject: false,
          }}
          labels={{
            xp: 'Practice toward the next level',
            peak: 'Best level ever reached',
            subject_id: 'What the skill is about',
            clear_subject: 'About nothing in particular',
          }}
          pickers={{ subject_id: { source: 'entity' } }}
        />
        {kinds.length > 0 && (
          <RowAction
            path='/api/actions/variant:assign'
            icon={Shapes}
            label={`Give ${skill.label} a made kind`}
            iconOnly
            fixed={{ family: 'skill', row_id: skill.id }}
            defaults={{ variant_id: skill.variant_id ?? null }}
            labels={{ variant_id: 'Made kind' }}
            choices={{ variant_id: kinds }}
          />
        )}
        <Button
          size='icon-sm'
          variant='ghost'
          aria-label={`Forget ${skill.label}`}
          disabled={blocked !== null}
          disabledReason={blocked ?? undefined}
          onClick={onForget}
        >
          <X />
        </Button>
      </div>
      <div className='flex min-w-0 flex-wrap items-center gap-1.5'>
        <Muted variant='caption'>{`${skill.xp}/${skill.next_level_xp} toward the next level · best ${skill.peak} · ${plain(SKILL_SOURCES, skill.source)}`}</Muted>
        {skill.subject && (
          <Badge
            size='sm'
            variant='outline'
          >{`About ${skill.subject.name}`}</Badge>
        )}
        {madeKind && (
          <Badge size='sm' variant='info'>
            <Shapes />
            {madeKind.name}
          </Badge>
        )}
        {hampered && (
          <Badge
            size='sm'
            variant='warning'
          >{`Only ${skill.effective} with this body`}</Badge>
        )}
        {skill.rusting && (
          <Badge size='sm' variant='secondary'>
            <Hourglass />
            {`Rusting, last used in epoch ${skill.last_used_epoch}`}
          </Badge>
        )}
      </div>
    </div>
  )
}

function SkillControls({ mind }: { mind: Mind }) {
  const { reason } = useGodGate()
  const [hold, setHold] = useState(false)
  const [picked, setPicked] = useState('')
  const [level, setLevel] = useState('40')
  const set = ({ key, value }: { key: string; value: number }) =>
    unwrap(
      api.POST('/api/actions/mind:skill', {
        body: {
          node_id: mind.node_id,
          skill: key as SkillKind,
          level: value,
          lock: hold,
        },
      })
    )
  const teach = useGodAction({
    run: () =>
      unwrap(
        api.POST('/api/actions/mind:skill', {
          body: {
            node_id: mind.node_id,
            skill: picked as SkillKind,
            level: Number(level),
            lock: hold,
          },
        })
      ),
    onDone: () => setPicked(''),
  })
  const parsed = Number(level)
  const invalid = !Number.isInteger(parsed) || parsed < 0 || parsed > PERCENT
  const busy = reason() ?? (teach.isPending ? WORKING : null)
  const known = new Set(mind.skills.map((item) => item.skill))
  const choices = Object.fromEntries(
    Object.entries(ALL_SKILLS).filter(([key]) => !known.has(key as SkillKind))
  )
  const groups: AdjustGroup[] = Object.keys(SKILL_FAMILIES)
    .map((family) => ({
      title: named(SKILL_FAMILIES, family).label,
      fields: mind.skills
        .filter((item) => item.family === family)
        .map((item) => ({
          key: item.skill,
          label: item.label,
          value: item.level,
          min: 0,
          max: PERCENT,
        })),
    }))
    .filter((group) => group.fields.length > 0)
  return (
    <ControlPanel
      title='Shape these skills'
      note='Teach a new skill or set any level. Held skills stop rusting and growing until you release them from the Mind section. Every change goes into the ledger and can be undone.'
      hold={hold}
      onHold={setHold}
    >
      <div className='grid min-w-0 grid-cols-1 items-end gap-3 @md/skills:grid-cols-3'>
        <MindPicker
          label='Teach a skill'
          value={picked}
          table={choices}
          blocked={busy}
          placeholder='Choose a skill'
          onPick={setPicked}
        />
        <div className='flex min-w-0 flex-col gap-1'>
          <Label as='label' htmlFor={`skill-level-${mind.node_id}`}>
            Level (0–100)
          </Label>
          <Input
            id={`skill-level-${mind.node_id}`}
            type='number'
            min={0}
            max={PERCENT}
            value={level}
            disabled={busy !== null}
            onChange={(event) => setLevel(event.target.value)}
          />
        </div>
        <div className='flex justify-end'>
          <Button
            size='sm'
            disabled={busy !== null || picked === '' || invalid}
            disabledReason={
              busy ??
              (picked === ''
                ? 'Choose a skill first.'
                : 'Write a level from 0 to 100.')
            }
            onClick={() => teach.mutate()}
          >
            <Plus />
            Teach it
          </Button>
        </div>
      </div>
      {groups.length > 0 && (
        <AdjustStats
          id={`skills-${mind.node_id}`}
          groups={groups}
          note='Skill levels run from 0 to 100.'
          run={set}
        />
      )}
    </ControlPanel>
  )
}

export function SkillsSection({ nodeId }: { nodeId: number }) {
  const { reason } = useGodGate()
  const query = useMind(nodeId)
  const forget = useGodAction({
    run: (skill: SkillKind) =>
      unwrap(
        api.POST('/api/actions/mind:skill_remove', {
          body: { node_id: nodeId, skill },
        })
      ),
  })
  const mind = query.data
  const blocked = reason() ?? (forget.isPending ? WORKING : null)
  return (
    <Section
      id='section-skills'
      title='Skills'
      description='What this mortal can do and how well: learned by doing, from masters and in battle; rusting when unused and fading in old age. Their best skills decide their calling.'
      icon={SKILLS_ICON}
    >
      {!mind ? (
        <EmptyState
          icon={SKILLS_ICON}
          title='No skills yet'
          description='The next epoch gives this mortal the skills of their life so far.'
        />
      ) : (
        <div className='@container/skills flex min-w-0 flex-col gap-4'>
          {mind.skills.length === 0 ? (
            <EmptyState
              icon={SKILLS_ICON}
              title='Unskilled'
              description='This mortal has learned nothing worth naming yet.'
            />
          ) : (
            <div className='@container/mind grid min-w-0 grid-cols-1 gap-3 @xl/skills:grid-cols-2'>
              {Object.keys(SKILL_FAMILIES).map((family) => {
                const rows = mind.skills.filter(
                  (item) => item.family === family
                )
                if (rows.length === 0) return null
                const spec = named(SKILL_FAMILIES, family)
                return (
                  <MindCard key={family} title={spec.label} icon={spec.icon}>
                    <Paged items={rows}>
                      {(skill) => (
                        <SkillRow
                          key={skill.skill}
                          skill={skill}
                          blocked={blocked}
                          onForget={() => forget.mutate(skill.skill)}
                        />
                      )}
                    </Paged>
                  </MindCard>
                )
              })}
            </div>
          )}
          <Muted variant='caption'>{`${mind.skills.length} skills known`}</Muted>
          <SkillControls mind={mind} />
        </div>
      )}
    </Section>
  )
}
