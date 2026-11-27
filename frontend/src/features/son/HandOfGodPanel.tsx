import { type ReactNode, useState } from 'react'
import {
  ArrowDownCircle,
  Ban,
  Crown,
  Droplet,
  Globe,
  Hand,
  HeartPulse,
  Link2,
  Megaphone,
  Play,
  Scissors,
  Shield,
  ShieldOff,
  Skull,
  Sparkles,
  Star,
  Swords,
  Utensils,
  Zap,
} from 'lucide-react'
import { api } from '@/api/client'
import { unwrap } from '@/api/errors'
import { plural } from '@/lib/units'
import { RARITY_LABEL } from '@/constants/rarity'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { Section, FieldTile } from '@/components/domain'
import { Label, Muted, Text } from '@/components/typography'
import { ActionButton } from '@/features/pantheon/ActionButton'
import { ActionJob } from '@/features/pantheon/ActionJob'
import {
  type SonPublic,
  type StatKey,
  useForeignGods,
  useSons,
  useWorldState,
} from '@/features/pantheon/api'
import { STAT_SCALE } from '@/features/pantheon/constants'
import {
  paramEquals,
  useGodGate,
  useRuleLookup,
  useRunningJob,
} from '@/features/pantheon/gate'
import { useGodAction } from '@/features/pantheon/godAction'
import { STATS } from '@/features/pantheon/labels'
import { RARITY_ORDER, statValue } from '@/features/pantheon/sonFacts'

const PERCENT = 100
const CREATOR_KEY = 'creator'
const REASON_MAX = 300

function Row({
  title,
  children,
  note,
}: {
  title: string
  children: ReactNode
  note?: string
}) {
  return (
    <div className='flex min-w-0 flex-col gap-2'>
      <Label variant='overline'>{title}</Label>
      <div className='flex min-w-0 flex-wrap items-center gap-2'>
        {children}
      </div>
      {note && <Muted variant='caption'>{note}</Muted>}
    </div>
  )
}

function Requirement({ ok, text }: { ok: boolean; text: string }) {
  return (
    <Badge size='sm' variant={ok ? 'success' : 'destructive'}>
      {text}
    </Badge>
  )
}

type HandOfGodPanelProps = {
  view: SonPublic
  ready: boolean
  killCost: number
}

export function HandOfGodPanel({ view, ready, killCost }: HandOfGodPanelProps) {
  const son = view.son
  const sonId = son.id
  const path = { params: { path: { son_id: sonId } } }
  const dead = son.status === 'dead'
  const rule = useRuleLookup()
  const { reason } = useGodGate()
  const state = useWorldState()
  const sons = useSons()
  const foreignGods = useForeignGods()
  const worlds = state.data?.worlds ?? []
  const distribution = state.data?.world?.son_distribution
  const [order, setOrder] = useState(son.standing_order ?? '')
  const [reasonText, setReasonText] = useState('')
  const firstOpen = STATS.find((stat) => statValue(son, stat.key) < STAT_SCALE)
  const [stat, setStat] = useState<StatKey>(firstOpen?.key ?? 'strength')
  const [slot, setSlot] = useState(String(view.powers[0]?.slot ?? ''))
  const [worldId, setWorldId] = useState(String(son.current_world_id ?? ''))
  const [rival, setRival] = useState('')
  const [duelStat, setDuelStat] = useState<StatKey>('strength')
  const [godId, setGodId] = useState('')
  const [sanity, setSanity] = useState(String(son.sanity ?? ''))
  const [essenceTo, setEssenceTo] = useState(CREATOR_KEY)
  const [essenceAmount, setEssenceAmount] = useState('')
  const running = useRunningJob(
    (job) => job.kind === 'son_turn' && paramEquals(job, 'son_id', sonId)
  )

  const announce = useGodAction({
    writes: [{ lever: 'command' }],
    run: (text: string) =>
      unwrap(api.PUT('/api/sons/{son_id}/order', { ...path, body: { text } })),
    success: (_result, text) =>
      text.trim() ? 'Order announced' : 'Standing order removed',
  })
  const absolute = useGodAction({
    writes: [{ lever: 'absolute_command' }],
    run: (text: string) =>
      unwrap(
        api.POST('/api/sons/{son_id}/absolute-command', {
          ...path,
          body: { text },
        })
      ),
    success: 'Irrefusable command given',
  })
  const act = useGodAction({
    writes: [{ method: 'POST', path: '/api/sons/{son_id}/act' }],
    run: () => unwrap(api.POST('/api/sons/{son_id}/act', path)),
    success: `${son.name} sets out`,
  })
  const bless = useGodAction({
    writes: [{ lever: 'bless' }],
    run: (body: {
      kind: 'essence' | 'hp' | 'stat' | 'existence'
      stat?: StatKey
    }) => unwrap(api.POST('/api/sons/{son_id}/bless', { ...path, body })),
    success: 'Blessed',
  })
  const punish = useGodAction({
    writes: [{ lever: 'punish' }],
    run: (kind: 'lightning' | 'chain' | 'exile' | 'suppress' | 'pardon') =>
      unwrap(
        api.POST('/api/sons/{son_id}/punish', { ...path, body: { kind } })
      ),
    success: (_result, kind) =>
      kind === 'pardon' ? 'Pardoned' : 'Judgment given',
  })
  const drain = useGodAction({
    writes: [{ lever: 'drain:son' }],
    run: () => unwrap(api.POST('/api/sons/{son_id}/drain', path)),
    success: 'Essence drained',
  })
  const devour = useGodAction({
    writes: [{ lever: 'devour:son' }],
    run: (text: string) =>
      unwrap(
        api.POST('/api/sons/{son_id}/devour', {
          ...path,
          body: { reason: text },
        })
      ),
    success: 'Devoured; their essence passed to you',
  })
  const kill = useGodAction({
    writes: [{ lever: 'kill:son' }],
    run: (text: string) =>
      unwrap(
        api.POST('/api/sons/{son_id}/kill', { ...path, body: { reason: text } })
      ),
    success: `${son.name} died`,
  })
  const star = useGodAction({
    writes: [{ lever: 'son:star' }],
    run: () => unwrap(api.POST('/api/sons/{son_id}/star', path)),
    success: 'Another star shone',
  })
  const ascend = useGodAction({
    writes: [{ lever: 'son:ascend' }],
    run: () => unwrap(api.POST('/api/sons/{son_id}/ascend', path)),
    success: 'Ascended to the next class',
  })
  const demote = useGodAction({
    writes: [{ lever: 'demote' }],
    run: () => unwrap(api.POST('/api/sons/{son_id}/demote', path)),
    success: 'Lowered by one class',
  })
  const strip = useGodAction({
    writes: [{ lever: 'strip_power' }],
    run: (value: number) =>
      unwrap(
        api.POST('/api/sons/{son_id}/strip-power', {
          ...path,
          body: { slot: value },
        })
      ),
    success: 'Power ripped out',
  })
  const sendWorld = useGodAction({
    writes: [{ lever: 'son:world' }],
    run: (value: number) =>
      unwrap(
        api.PUT('/api/sons/{son_id}/world', {
          ...path,
          body: { world_id: value },
        })
      ),
    success: `${son.name} was sent to a new world`,
  })
  const unprotect = useGodAction({
    writes: [{ lever: 'son:protection' }],
    run: () => unwrap(api.DELETE('/api/sons/{son_id}/protection', path)),
    success: 'Automatic distribution may move them again',
  })
  const duel = useGodAction({
    writes: [{ lever: 'son:duel' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/son:duel', {
          body: {
            challenger_id: sonId,
            defender_id: Number(rival),
            stat: duelStat,
          },
        })
      ),
  })
  const godWar = useGodAction({
    writes: [{ lever: 'son:god_war' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/son:god_war', {
          body: { son_id: sonId, god_id: Number(godId) },
        })
      ),
  })
  const sendEssence = useGodAction({
    writes: [{ lever: 'son:send_essence' }],
    run: () =>
      unwrap(
        api.POST('/api/actions/son:send_essence', {
          body: {
            son_id: sonId,
            to_son_id: essenceTo === CREATOR_KEY ? null : Number(essenceTo),
            amount: Number(essenceAmount),
          },
        })
      ),
    success: 'Essence sent',
  })
  const setSanityAction = useGodAction({
    writes: [{ lever: 'son:sanity' }],
    run: (value: number) =>
      unwrap(
        api.POST('/api/actions/son:sanity', { body: { son_id: sonId, value } })
      ),
    success: 'Sanity set',
  })

  const deadReason = dead ? 'The dead take no orders.' : null
  const keepEssence = rule('son_tools.gift_min_remaining')
  const giftCap = rule('son_tools.gift_max_essence')
  const essenceBlock = (() => {
    const amount = Number(essenceAmount)
    if (essenceAmount === '' || !Number.isInteger(amount) || amount < 1)
      return 'Enter how much essence to send.'
    if (giftCap !== undefined && amount > giftCap)
      return `At most ${giftCap} essence at once.`
    if (keepEssence !== undefined && son.essence - keepEssence < 1)
      return `${son.name} must keep ${keepEssence} essence and has ${son.essence}.`
    return null
  })()
  const absoluteCost = rule('god_power.absolute_command_cost')
  const essenceCost = rule('costs.bless_essence')
  const hpCost = rule('costs.bless_hp')
  const statCost = rule('costs.bless_stat')
  const lightningCost = rule('costs.lightning')
  const suppressCost = rule('balance.suppress_revolt')
  const demoteCost = rule('god_power.demote_cost')
  const stripCost = rule('god_power.strip_power_cost')
  const drainPct = rule('god_power.drain_son_pct')
  const drainEfficiency = rule('god_power.drain_son_efficiency_pct')
  const devourMight = rule('god_power.devour_son_essence_per_might')
  const devourLevel = rule('god_power.devour_son_essence_per_level')
  const protectEpochs = rule('god_hand.assignment_protection_epochs')
  const drainGain =
    drainPct !== undefined && drainEfficiency !== undefined
      ? Math.round(
          (Math.round((son.essence * drainPct) / PERCENT) * drainEfficiency) /
            PERCENT
        )
      : undefined
  const devourGain =
    devourMight !== undefined && devourLevel !== undefined
      ? son.essence + son.might * devourMight + son.level * devourLevel
      : undefined
  const rarityIndex = RARITY_ORDER.indexOf(son.rarity)
  const lowerRarity = rarityIndex > 0 ? RARITY_ORDER[rarityIndex - 1] : null
  const exiledOrChained = son.status === 'exiled' || son.chained
  const notReady = !ready
    ? 'Acted this epoch, asleep, chained, exiled or fading.'
    : null
  const allMax = !firstOpen
  const otherSons = (sons.data ?? []).filter(
    (other) => other.son.id !== sonId && other.son.status !== 'dead'
  )
  const nextStar = view.next_star
  const ascension = view.ascension
  const orderText = order.trim()

  return (
    <Section
      id='section-son-hand'
      title='Hand of God'
      description={`Every power you hold over ${son.name}. All of it also unfolds on its own as epochs pass.`}
      surface='card'
      level={3}
    >
      <FieldTile id={`order-${sonId}`} label='Order for their next action'>
        <Textarea
          id={`order-${sonId}`}
          value={order}
          disabled={dead}
          placeholder='What you command, in your own words'
          onChange={(event) => setOrder(event.target.value)}
        />
        {son.order_absolute && (
          <div>
            <Badge size='sm' variant='destructive'>
              Absolute command in force
            </Badge>
          </div>
        )}
      </FieldTile>
      <Row
        title='Orders'
        note='An absolute command is done first on their next turn and costs a little loyalty.'
      >
        <ActionButton
          act={announce}
          label={orderText ? 'Announce order' : 'Clear standing order'}
          icon={Megaphone}
          blocked={reason() ?? deadReason}
          pending={announce.isPending}
          onRun={() => announce.mutate(orderText)}
        />
        <ActionButton
          act={absolute}
          label='Absolute command'
          icon={Crown}
          variant='destructive'
          cost={absoluteCost}
          rule='god_power.absolute_command_cost'
          blocked={
            reason({ cost: absoluteCost }) ??
            deadReason ??
            (orderText ? null : 'Write the command in the order box first.')
          }
          pending={absolute.isPending}
          confirm={{
            title: 'Give an irrefusable command?',
            description: `${son.name} cannot refuse it. It is done first on their next turn.`,
          }}
          onRun={() => absolute.mutate(orderText)}
        />
        <ActionButton
          act={act}
          label='Act now'
          icon={Play}
          variant='default'
          blocked={
            reason({ world: true, llm: true }) ??
            (dead ? 'A dead son cannot act.' : notReady) ??
            (running ? 'Their turn is already running.' : null)
          }
          pending={act.isPending}
          onRun={() => act.mutate()}
        />
      </Row>
      <ActionJob
        jobId={act.jobId}
        title={`${son.name}'s turn`}
        onDismiss={act.clearJob}
      />
      <Separator />
      <Row title='Bless'>
        <ActionButton
          act={bless}
          label='Essence'
          icon={Sparkles}
          cost={essenceCost}
          rule='costs.bless_essence'
          blocked={
            reason({ cost: essenceCost }) ??
            deadReason ??
            (son.essence >= view.max_essence
              ? `Essence already full (${son.essence}/${view.max_essence}).`
              : null)
          }
          pending={bless.isPending}
          onRun={() => bless.mutate({ kind: 'essence' })}
        />
        <ActionButton
          act={bless}
          label='Fill life'
          icon={HeartPulse}
          cost={hpCost}
          rule='costs.bless_hp'
          blocked={
            reason({ cost: hpCost }) ??
            deadReason ??
            (son.hp >= view.max_hp ? 'Life is already full.' : null)
          }
          pending={bless.isPending}
          onRun={() => bless.mutate({ kind: 'hp' })}
        />
        <ActionButton
          act={bless}
          label='Remember them'
          icon={Sparkles}
          cost={essenceCost}
          rule='costs.bless_essence'
          blocked={
            reason({ cost: essenceCost }) ??
            deadReason ??
            (son.existence >= STAT_SCALE
              ? 'Their existence is already whole.'
              : null)
          }
          pending={bless.isPending}
          onRun={() => bless.mutate({ kind: 'existence' })}
        />
      </Row>
      <Row title='Raise a stat'>
        <Select
          value={stat}
          onValueChange={(value) => setStat(value as StatKey)}
        >
          <SelectTrigger aria-label='Stat to raise' className='w-48'>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATS.map((item) => {
              const value = statValue(son, item.key)
              return (
                <SelectItem
                  key={item.key}
                  value={item.key}
                  disabled={value >= STAT_SCALE}
                >
                  {value >= STAT_SCALE
                    ? `${item.label} · ${value} (at top)`
                    : `${item.label} · ${value}`}
                </SelectItem>
              )
            })}
          </SelectContent>
        </Select>
        <ActionButton
          act={bless}
          label='Raise'
          icon={ArrowDownCircle}
          cost={statCost}
          rule='costs.bless_stat'
          blocked={
            reason({ cost: statCost }) ??
            deadReason ??
            (allMax ? 'Every stat is at the top.' : null)
          }
          pending={bless.isPending}
          onRun={() => bless.mutate({ kind: 'stat', stat })}
        />
      </Row>
      <Separator />
      <Row
        title='Punish'
        note='Above a strong will, punishment lowers loyalty and grows anger; below it, they bow in fear.'
      >
        <ActionButton
          act={punish}
          label='Lightning'
          icon={Zap}
          variant='destructive'
          cost={lightningCost}
          rule='costs.lightning'
          blocked={reason({ cost: lightningCost }) ?? deadReason}
          pending={punish.isPending}
          confirm={{
            title: 'Let lightning strike?',
            description: `${son.name} is struck and remembers it.`,
          }}
          onRun={() => punish.mutate('lightning')}
        />
        <ActionButton
          act={punish}
          label='Chain this epoch'
          icon={Link2}
          variant='destructive'
          blocked={
            reason() ??
            deadReason ??
            (son.chained ? 'Already chained.' : null) ??
            (!ready
              ? 'Already acted or cannot act; the chain does not carry to the next epoch.'
              : null)
          }
          pending={punish.isPending}
          confirm={{
            title: 'Chain them this epoch?',
            description: 'They cannot act until the epoch ends.',
          }}
          onRun={() => punish.mutate('chain')}
        />
        {exiledOrChained ? (
          <ActionButton
            act={punish}
            label='Pardon'
            icon={Hand}
            blocked={reason()}
            pending={punish.isPending}
            onRun={() => punish.mutate('pardon')}
          />
        ) : (
          <ActionButton
            act={punish}
            label='Exile'
            icon={Ban}
            variant='destructive'
            blocked={reason() ?? deadReason}
            pending={punish.isPending}
            confirm={{
              title: 'Exile them?',
              description: `${son.name} is cast out until you pardon them.`,
            }}
            onRun={() => punish.mutate('exile')}
          />
        )}
      </Row>
      {son.rebel && (
        <Row
          title='Rebellion'
          note='Your power is tested against their will; if you fail, the cost still falls.'
        >
          <Badge variant='destructive'>In rebellion against the Creator</Badge>
          <ActionButton
            act={punish}
            label='Suppress the rebellion'
            icon={Shield}
            variant='destructive'
            cost={suppressCost}
            rule='balance.suppress_revolt'
            blocked={reason({ cost: suppressCost })}
            pending={punish.isPending}
            confirm={{
              title: 'Suppress the rebellion?',
              description: 'It may fail.',
            }}
            onRun={() => punish.mutate('suppress')}
          />
          <ActionButton
            act={punish}
            label='Forgive'
            icon={Hand}
            blocked={reason()}
            pending={punish.isPending}
            onRun={() => punish.mutate('pardon')}
          />
        </Row>
      )}
      {!dead && (
        <>
          <Separator />
          <FieldTile
            id={`reason-${sonId}`}
            label='Why? Written in the chronicle'
          >
            <Input
              id={`reason-${sonId}`}
              value={reasonText}
              maxLength={REASON_MAX}
              onChange={(event) => setReasonText(event.target.value)}
            />
          </FieldTile>
          <Row title='Essence and death'>
            <ActionButton
              act={drain}
              label='Drain their essence'
              icon={Droplet}
              variant='destructive'
              gain={drainGain}
              blocked={
                reason() ?? (son.essence <= 0 ? 'No essence left.' : null)
              }
              pending={drain.isPending}
              confirm={{
                title: 'Drain their essence?',
                description:
                  'They lose loyalty and grow angry; their siblings are bound by fear.',
              }}
              onRun={() => drain.mutate()}
            />
            <ActionButton
              act={devour}
              label='Devour'
              icon={Utensils}
              variant='destructive'
              gain={devourGain}
              blocked={reason({ world: true })}
              pending={devour.isPending}
              confirm={{
                title: `Devour ${son.name}?`,
                description: `${son.name} will be devoured and their essence will pass to you.`,
              }}
              onRun={() => devour.mutate(reasonText.trim())}
            />
            <ActionButton
              act={kill}
              label='Kill'
              icon={Skull}
              variant='destructive'
              cost={killCost}
              blocked={reason({ cost: killCost, world: true })}
              pending={kill.isPending}
              confirm={{
                title: `Kill ${son.name}?`,
                description:
                  'Their body becomes a corpse and their loyal worshippers a resurrection cult. The others are bound by fear; their friends are angered.',
              }}
              onRun={() => kill.mutate(reasonText.trim())}
            />
          </Row>
        </>
      )}
      <Separator />
      <Row title='Star and class'>
        {nextStar ? (
          <>
            <ActionButton
              act={star}
              label={`Give star ${nextStar.stars}`}
              icon={Star}
              variant='default'
              cost={nextStar.essence}
              blocked={
                reason({ cost: nextStar.essence }) ??
                deadReason ??
                (son.level < nextStar.level || son.fame < nextStar.fame
                  ? 'They do not meet the requirements yet.'
                  : null)
              }
              pending={star.isPending}
              onRun={() => star.mutate()}
            />
            <Requirement
              ok={son.level >= nextStar.level}
              text={`Level ${son.level}/${nextStar.level}`}
            />
            <Requirement
              ok={son.fame >= nextStar.fame}
              text={`Fame ${son.fame}/${nextStar.fame}`}
            />
          </>
        ) : ascension ? (
          <>
            <ActionButton
              act={ascend}
              label={`Ascend to ${RARITY_LABEL[ascension.target]}`}
              icon={Crown}
              variant='default'
              cost={ascension.essence}
              blocked={
                reason({ cost: ascension.essence }) ??
                deadReason ??
                (son.level < ascension.level || son.fame < ascension.fame
                  ? 'They do not meet the requirements yet.'
                  : null)
              }
              pending={ascend.isPending}
              onRun={() => ascend.mutate()}
            />
            <Requirement
              ok={son.level >= ascension.level}
              text={`Level ${son.level}/${ascension.level}`}
            />
            <Requirement
              ok={son.fame >= ascension.fame}
              text={`Fame ${son.fame}/${ascension.fame}`}
            />
          </>
        ) : (
          <Text variant='caption'>
            They have reached the highest class and star.
          </Text>
        )}
      </Row>
      {!dead && (
        <Row
          title='Class and power'
          note='Demotion drops stats to the lower class cap; ripping out a power returns some essence to you.'
        >
          <ActionButton
            act={demote}
            label={
              lowerRarity ? `Lower to ${RARITY_LABEL[lowerRarity]}` : 'Demote'
            }
            icon={ArrowDownCircle}
            variant='destructive'
            cost={demoteCost}
            rule='god_power.demote_cost'
            blocked={
              reason({ cost: demoteCost }) ??
              (lowerRarity ? null : 'Already the lowest class.')
            }
            pending={demote.isPending}
            confirm={{
              title: `Demote ${son.name}?`,
              description: 'They lose loyalty and grow angry.',
            }}
            onRun={() => demote.mutate()}
          />
          {view.powers.length > 0 ? (
            <>
              <Select value={slot} onValueChange={setSlot}>
                <SelectTrigger aria-label='Power to rip out' className='w-48'>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {view.powers.map((power) => (
                    <SelectItem key={power.slot} value={String(power.slot)}>
                      {power.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <ActionButton
                act={strip}
                label='Rip out the power'
                icon={Scissors}
                variant='destructive'
                cost={stripCost}
                rule='god_power.strip_power_cost'
                blocked={
                  reason({ cost: stripCost }) ?? (slot ? null : 'Pick a power.')
                }
                pending={strip.isPending}
                confirm={{
                  title: 'Rip out this power?',
                  description: 'They grow angry.',
                }}
                onRun={() => strip.mutate(Number(slot))}
              />
            </>
          ) : (
            <Text variant='caption'>They have no power to rip out.</Text>
          )}
        </Row>
      )}
      {!dead && worlds.length > 1 && (
        <Row
          title='World'
          note={
            distribution === 'auto'
              ? `Distribution is automatic; a son you send by hand is protected from it${protectEpochs !== undefined ? ` for ${plural(protectEpochs, 'epoch', 'epochs')}` : ''}.`
              : 'Distribution is manual; sons stay where you send them.'
          }
        >
          <Select
            value={
              worlds.some((world) => String(world.id) === worldId)
                ? worldId
                : ''
            }
            onValueChange={setWorldId}
          >
            <SelectTrigger aria-label='World to send them to' className='w-56'>
              <SelectValue placeholder='Pick a world' />
            </SelectTrigger>
            <SelectContent>
              {worlds
                .filter((world) => world.discovery !== 'forgotten')
                .map((world) => (
                  <SelectItem key={world.id} value={String(world.id)}>
                    {world.id === son.current_world_id
                      ? `${world.name} (current)`
                      : world.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
          <ActionButton
            act={sendWorld}
            label='Send to world'
            icon={Globe}
            blocked={
              reason() ??
              (!worldId || Number(worldId) === son.current_world_id
                ? 'Pick another world.'
                : null)
            }
            pending={sendWorld.isPending}
            onRun={() => sendWorld.mutate(Number(worldId))}
          />
          {son.manually_assigned_epoch !== null && (
            <ActionButton
              act={unprotect}
              label='Release to distribution'
              icon={ShieldOff}
              blocked={reason()}
              pending={unprotect.isPending}
              onRun={() => unprotect.mutate()}
            />
          )}
        </Row>
      )}
      {!dead && (
        <>
          <Separator />
          <Row
            title='Strife'
            note='These happen on their own between rivals; here you set them off yourself.'
          >
            <Select value={rival} onValueChange={setRival}>
              <SelectTrigger aria-label='Sibling to duel' className='w-48'>
                <SelectValue placeholder='Pick a sibling' />
              </SelectTrigger>
              <SelectContent>
                {otherSons.map((other) => (
                  <SelectItem key={other.son.id} value={String(other.son.id)}>
                    {other.son.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={duelStat}
              onValueChange={(value) => setDuelStat(value as StatKey)}
            >
              <SelectTrigger aria-label='Duel stat' className='w-40'>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATS.map((item) => (
                  <SelectItem key={item.key} value={item.key}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <ActionButton
              act={duel}
              label='Duel'
              icon={Swords}
              blocked={reason() ?? (rival ? null : 'Pick a sibling.')}
              pending={duel.isPending}
              confirm={{
                title: 'Start a duel?',
                description: 'The loser is wounded and both remember it.',
              }}
              onRun={() => duel.mutate()}
            />
          </Row>
          <Row
            title='Pass on essence'
            note={`Moves essence from ${son.name} to a sibling or to you. A sibling takes only what they can still hold${keepEssence !== undefined ? `, and ${son.name} keeps at least ${keepEssence}` : ''}. Sons may also do this of their own will.`}
          >
            <Select value={essenceTo} onValueChange={setEssenceTo}>
              <SelectTrigger
                aria-label='Who receives the essence'
                className='w-48'
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={CREATOR_KEY}>The Creator</SelectItem>
                {otherSons.map((other) => (
                  <SelectItem key={other.son.id} value={String(other.son.id)}>
                    {other.son.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              aria-label='Essence to send'
              type='number'
              min={1}
              max={giftCap}
              value={essenceAmount}
              className='w-32'
              onChange={(event) => setEssenceAmount(event.target.value)}
            />
            <ActionButton
              act={sendEssence}
              label='Send essence'
              icon={Droplet}
              blocked={reason() ?? essenceBlock}
              pending={sendEssence.isPending}
              onRun={() => sendEssence.mutate()}
            />
          </Row>
          {(foreignGods.data ?? []).length > 0 && (
            <Row title='War of gods'>
              <Select value={godId} onValueChange={setGodId}>
                <SelectTrigger aria-label='Foreign god' className='w-56'>
                  <SelectValue placeholder='Pick a foreign god' />
                </SelectTrigger>
                <SelectContent>
                  {(foreignGods.data ?? [])
                    .filter((god) => god.status !== 'dead')
                    .map((god) => (
                      <SelectItem key={god.id} value={String(god.id)}>
                        {god.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <ActionButton
                act={godWar}
                label='Go to war'
                icon={Swords}
                variant='destructive'
                blocked={reason() ?? (godId ? null : 'Pick a foreign god.')}
                pending={godWar.isPending}
                confirm={{
                  title: 'Send them to war?',
                  description:
                    'They fight the foreign god with their strength and will.',
                }}
                onRun={() => godWar.mutate()}
              />
            </Row>
          )}
          <Row
            title='Sanity'
            note='Cosmic horror erodes it; low sanity clouds their mind.'
          >
            <Input
              aria-label='Sanity'
              type='number'
              min={0}
              max={STAT_SCALE}
              value={sanity}
              className='w-32'
              onChange={(event) => setSanity(event.target.value)}
            />
            <ActionButton
              act={setSanityAction}
              label='Set sanity'
              blocked={reason() ?? (sanity === '' ? 'Enter a value.' : null)}
              pending={setSanityAction.isPending}
              onRun={() => setSanityAction.mutate(Number(sanity))}
            />
          </Row>
        </>
      )}
    </Section>
  )
}
