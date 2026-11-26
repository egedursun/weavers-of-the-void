import { type paths } from '@/api/generated/schema'
import { type Permission } from '@/api/teamGate'

type Method = 'post' | 'put' | 'patch' | 'delete'

type Offered<Item, M extends string> = M extends keyof Item
  ? undefined extends Item[M]
    ? never
    : M
  : never

type WritePath = {
  [P in keyof paths]: Offered<paths[P], Method> extends never ? never : P
}[keyof paths]

export type LeverPath = Extract<WritePath, `/api/actions/${string}`>

export type PlainWritePath = Exclude<WritePath, LeverPath>

export type WriteMethod<P extends PlainWritePath> = Uppercase<
  Offered<paths[P], Method>
>

export type WriteRule =
  | Permission
  | 'none'
  | 'account'
  | 'admin'
  | 'workspace_admin'
  | 'universe_admin'
  | 'author'
  | 'undo'
  | 'divine_will_mode'
  | 'presence_record'
  | { lever: string }

export type PlainWrite = {
  [P in PlainWritePath]: { method: WriteMethod<P>; path: P }
}[PlainWritePath]

export const WRITE_PERMISSIONS: {
  [P in PlainWritePath]: { [M in WriteMethod<P>]: WriteRule }
} = {
  '/api/auth/setup': { POST: 'account' },
  '/api/auth/sign-in': { POST: 'account' },
  '/api/auth/sign-out': { POST: 'account' },
  '/api/auth/password': { POST: 'account' },
  '/api/auth/profile': { PATCH: 'account' },
  '/api/auth/sessions': { DELETE: 'account' },
  '/api/auth/sessions/{session_id}': { DELETE: 'account' },
  '/api/accounts': { POST: 'account' },
  '/api/accounts/{account_id}': { PATCH: 'account', DELETE: 'account' },
  '/api/accounts/{account_id}/reset-password': { POST: 'account' },
  '/api/accounts/{account_id}/ownership': { POST: 'account' },
  '/api/workspaces': { POST: 'account' },
  '/api/workspaces/{workspace_id}': {
    PATCH: 'workspace_admin',
    DELETE: 'workspace_admin',
  },
  '/api/workspaces/{workspace_id}/leave': { POST: 'none' },
  '/api/workspaces/{workspace_id}/members': { POST: 'workspace_admin' },
  '/api/workspaces/{workspace_id}/members/{account_id}': {
    PATCH: 'workspace_admin',
    DELETE: 'workspace_admin',
  },
  '/api/workspaces/{workspace_id}/members/{account_id}/reset-password': {
    POST: 'workspace_admin',
  },
  '/api/workspaces/{workspace_id}/members/{account_id}/deactivate': {
    POST: 'workspace_admin',
  },
  '/api/workspaces/{workspace_id}/members/{account_id}/reactivate': {
    POST: 'workspace_admin',
  },
  '/api/workspaces/{workspace_id}/universes/{universe_id}/access/overrides/{account_id}':
    { PUT: 'universe_admin', DELETE: 'universe_admin' },
  '/api/workspaces/{workspace_id}/universes/{universe_id}/access/permissions': {
    PUT: 'universe_admin',
    DELETE: 'universe_admin',
  },
  '/api/workspaces/{workspace_id}/universes/{universe_id}/access/canon-approval':
    { PUT: 'universe_admin' },
  '/api/workspaces/{workspace_id}/providers/connections': {
    POST: 'workspace_admin',
  },
  '/api/workspaces/{workspace_id}/providers/connections/{connection_id}': {
    PATCH: 'workspace_admin',
    DELETE: 'workspace_admin',
  },
  '/api/workspaces/{workspace_id}/providers/connections/{connection_id}/login':
    { POST: 'workspace_admin', DELETE: 'workspace_admin' },
  '/api/workspaces/{workspace_id}/providers/connections/{connection_id}/login/input':
    { POST: 'workspace_admin' },
  '/api/workspaces/{workspace_id}/providers/connections/{connection_id}/logout':
    { POST: 'workspace_admin' },
  '/api/workspaces/{workspace_id}/providers/roles/{role}': {
    PUT: 'workspace_admin',
  },
  '/api/workspaces/{workspace_id}/providers/roles/{role}/check': {
    POST: 'workspace_admin',
  },
  '/api/server/providers/connections': { POST: 'account' },
  '/api/server/providers/connections/{connection_id}': {
    PATCH: 'account',
    DELETE: 'account',
  },
  '/api/server/providers/roles/{role}': { PUT: 'account' },
  '/api/server/providers/roles/{role}/check': { POST: 'account' },
  '/api/library/universes': { POST: 'none' },
  '/api/library/universes/{universe_id}': {
    PATCH: 'manage_shelf',
    DELETE: 'admin',
  },
  '/api/library/universes/{universe_id}/open': { POST: 'view' },
  '/api/library/universes/{universe_id}/close': { POST: 'view' },
  '/api/library/universes/{universe_id}/duplicate': { POST: 'export' },
  '/api/library/universes/{universe_id}/archive': { POST: 'manage_shelf' },
  '/api/library/universes/{universe_id}/move': { POST: 'admin' },
  '/api/library/universes/{universe_id}/restore': { POST: 'manage_shelf' },
  '/api/library/trash': { DELETE: 'none' },
  '/api/library/trash/{entry_id}/restore': { POST: 'none' },
  '/api/library/trash/{entry_id}': { DELETE: 'none' },
  '/api/library/universes/{universe_id}/export': { POST: 'export' },
  '/api/library/exports/{job_id}': { DELETE: 'none' },
  '/api/library/imports': { POST: 'none' },
  '/api/library/imports/{job_id}': { DELETE: 'none' },
  '/api/library/imports/{job_id}/confirm': { POST: 'none' },
  '/api/library/universes/{universe_id}/cover': {
    PUT: 'manage_shelf',
    DELETE: 'manage_shelf',
  },
  '/api/library/universes/{universe_id}/cover/from-media': {
    PUT: 'manage_shelf',
  },
  '/api/library/universes/{universe_id}/cover/paint': {
    POST: 'generate_images',
  },
  '/api/jobs/{job_id}/cancel': { POST: 'start_ages' },
  '/api/rules': { PATCH: 'change_rules', DELETE: 'change_rules' },
  '/api/rules/{namespace}/{key}': {
    PUT: 'change_rules',
    DELETE: 'change_rules',
  },
  '/api/genesis': { POST: 'edit_world' },
  '/api/epochs/current/complete': { POST: 'start_ages' },
  '/api/epochs/current/stop': { POST: 'start_ages' },
  '/api/creator': { PATCH: { lever: 'creator:edit' } },
  '/api/creator/note': { PUT: { lever: 'creator:note' } },
  '/api/creator/mood': { PUT: { lever: 'creator:mood' } },
  '/api/creator/passions': { PUT: { lever: 'creator:passions' } },
  '/api/creator/portrait': { POST: { lever: 'creator:content' } },
  '/api/creator/epic': { POST: { lever: 'creator:content' } },
  '/api/creator/deepen': { POST: { lever: 'creator:content' } },
  '/api/sons/{son_id}/reputation-nudge': {
    POST: { lever: 'creator:reputation' },
  },
  '/api/revelations': { POST: { lever: 'revelation' } },
  '/api/sons/{son_id}': { PATCH: { lever: 'son:edit' } },
  '/api/sons/{son_id}/act': { POST: 'start_ages' },
  '/api/sons/summon': { POST: { lever: 'summon_son' } },
  '/api/sons/distribute': { POST: { lever: 'son:distribute' } },
  '/api/sons/{son_id}/order': { PUT: { lever: 'command' } },
  '/api/sons/{son_id}/bless': { POST: { lever: 'bless' } },
  '/api/sons/{son_id}/punish': { POST: { lever: 'punish' } },
  '/api/sons/{son_id}/star': { POST: { lever: 'son:star' } },
  '/api/sons/{son_id}/ascend': { POST: { lever: 'son:ascend' } },
  '/api/sons/{son_id}/epic': { POST: { lever: 'son:epic' } },
  '/api/sons/{son_id}/resurrect': { POST: { lever: 'resurrect:son' } },
  '/api/sons/{son_id}/kill': { POST: { lever: 'kill:son' } },
  '/api/sons/{son_id}/devour': { POST: { lever: 'devour:son' } },
  '/api/sons/{son_id}/drain': { POST: { lever: 'drain:son' } },
  '/api/sons/{son_id}/absolute-command': {
    POST: { lever: 'absolute_command' },
  },
  '/api/sons/{son_id}/demote': { POST: { lever: 'demote' } },
  '/api/sons/{son_id}/strip-power': { POST: { lever: 'strip_power' } },
  '/api/sons/{son_id}/rebellion': { POST: { lever: 'rebellion:force' } },
  '/api/sons/{son_id}/scheme': { POST: { lever: 'sibling:scheme' } },
  '/api/sons/{son_id}/hinder-return': {
    POST: { lever: 'sibling:hinder_return' },
  },
  '/api/sons/{son_id}/world': { PUT: { lever: 'son:world' } },
  '/api/sons/{son_id}/protection': { DELETE: { lever: 'son:protection' } },
  '/api/sons/{son_id}/reset-counters': {
    POST: { lever: 'son:reset_counters' },
  },
  '/api/sons/{son_id}/image-prompt': { PUT: { lever: 'son:image_prompt' } },
  '/api/entities/{entity_id}': { PATCH: { lever: 'record:edit' } },
  '/api/entities/{entity_id}/archive': { PUT: 'edit_world' },
  '/api/entities/{entity_id}/deepen': { POST: 'edit_world' },
  '/api/entities/{entity_id}/image-prompt': { POST: 'generate_images' },
  '/api/entities/{entity_id}/suggest-links': { POST: 'edit_world' },
  '/api/entities/{entity_id}/canon': { PUT: { lever: 'canon:set' } },
  '/api/entities/{entity_id}/intervene': { POST: { lever: 'intervene' } },
  '/api/entities/{entity_id}/knowledge': { PUT: { lever: 'knowledge:set' } },
  '/api/entities/{entity_id}/dream': { POST: { lever: 'dream' } },
  '/api/entities/{entity_id}/favorite': { PUT: { lever: 'record:favorite' } },
  '/api/entities/{entity_id}/note': {
    PUT: { lever: 'record:note' },
    DELETE: { lever: 'record:note' },
  },
  '/api/entities/{entity_id}/merge': { POST: { lever: 'record:merge' } },
  '/api/entities/{entity_id}/stat': { PUT: { lever: 'entity:stat' } },
  '/api/entities/{entity_id}/tags': { PATCH: { lever: 'entity:tags' } },
  '/api/entities/{entity_id}/location': { PUT: { lever: 'entity:move' } },
  '/api/entities/{entity_id}/patron': { PUT: { lever: 'entity:patron' } },
  '/api/entities/{entity_id}/decree': { POST: { lever: 'decree' } },
  '/api/entities/{entity_id}/agent': { PUT: { lever: 'entity:agent' } },
  '/api/entities/{entity_id}/explore': { POST: { lever: 'explore' } },
  '/api/entities/{entity_id}/seek-route': { POST: { lever: 'seek_route' } },
  '/api/entities/{entity_id}/expedition': { POST: { lever: 'expedition' } },
  '/api/entities/{entity_id}/exile': { POST: { lever: 'exile' } },
  '/api/entities/{entity_id}/pardon': { POST: { lever: 'pardon' } },
  '/api/entities/{entity_id}/rite': { POST: { lever: 'rite' } },
  '/api/entities/{entity_id}/take-life': { POST: { lever: 'take_life' } },
  '/api/entities/{entity_id}/drain': { POST: { lever: 'drain:mortal' } },
  '/api/entities/{entity_id}/harvest': { POST: { lever: 'harvest' } },
  '/api/entities/{entity_id}/resurrect': {
    POST: { lever: 'resurrect:mortal' },
  },
  '/api/entities/{entity_id}/deify': { POST: { lever: 'deify' } },
  '/api/entities/{entity_id}/prophet': { POST: { lever: 'prophet' } },
  '/api/entities/{entity_id}/manifest': { POST: { lever: 'manifest' } },
  '/api/entities/{entity_id}/bloodline-curse': {
    POST: { lever: 'bloodline_curse' },
  },
  '/api/entities/{entity_id}/convert': { POST: { lever: 'convert' } },
  '/api/entities/{entity_id}/wrath': { POST: { lever: 'wrath' } },
  '/api/links': { POST: { lever: 'bond:add' } },
  '/api/links/{bond_id}': { DELETE: { lever: 'bond:remove' } },
  '/api/facts': { POST: { lever: 'fact:add' } },
  '/api/facts/{fact_id}': { DELETE: { lever: 'fact:remove' } },
  '/api/beliefs': { PUT: { lever: 'belief:edit' } },
  '/api/integrity/findings/resolve': { POST: 'edit_world' },
  '/api/integrity/{task}': { POST: 'edit_world' },
  '/api/entities/{entity_id}/relations/{other_id}': {
    PUT: { lever: 'relation:set' },
  },
  '/api/entities/{entity_id}/relations/{other_id}/feud': {
    POST: { lever: 'feud:start' },
    DELETE: { lever: 'feud:end' },
  },
  '/api/foreign-gods': { POST: { lever: 'foreign_god:place' } },
  '/api/foreign-gods/{god_id}': { PATCH: { lever: 'foreign_god:edit' } },
  '/api/foreign-gods/{god_id}/deepen': {
    POST: { lever: 'foreign_god:deepen' },
  },
  '/api/foreign-gods/{god_id}/drain': { POST: { lever: 'drain:foreign_god' } },
  '/api/foreign-gods/{god_id}/kill': { POST: { lever: 'kill:foreign_god' } },
  '/api/worlds': { POST: { lever: 'create_world' } },
  '/api/worlds/{world_id}': { PATCH: { lever: 'world:edit' } },
  '/api/worlds/{world_id}/orbit': { PUT: { lever: 'world:orbit' } },
  '/api/worlds/{world_id}/wrath': { POST: { lever: 'wrath:world' } },
  '/api/worlds/{world_id}/discovery-round': {
    POST: { lever: 'discovery_round' },
  },
  '/api/stars/{star_id}': {
    PATCH: { lever: 'star:edit' },
    DELETE: { lever: 'star:delete' },
  },
  '/api/routes': { POST: { lever: 'route:open' } },
  '/api/routes/{route_id}/sever': { POST: { lever: 'route' } },
  '/api/routes/{route_id}/restore': { POST: { lever: 'route' } },
  '/api/routes/{route_id}/reveal': { POST: { lever: 'route' } },
  '/api/voyages/{journey_id}/recall': { POST: { lever: 'journey:recall' } },
  '/api/climate': { PUT: { lever: 'climate' } },
  '/api/cosmic-resource': { PUT: { lever: 'cosmos:resource' } },
  '/api/cosmic-resource/deposits': { POST: { lever: 'cosmos:deposit' } },
  '/api/cosmic/hang-star': { POST: { lever: 'cosmic:hang_star' } },
  '/api/cosmic/seal-gate': { POST: { lever: 'cosmic:seal_gate' } },
  '/api/cosmic/cleanse-leak': { POST: { lever: 'cosmic:cleanse_leak' } },
  '/api/cosmic/forget-world': { POST: { lever: 'cosmic:forget_world' } },
  '/api/cosmic/sky-event': { POST: { lever: 'cosmic:sky_event' } },
  '/api/cosmic/rekindle-star': { POST: { lever: 'cosmic:rekindle_star' } },
  '/api/cosmic/soul-bind': { POST: { lever: 'cosmic:soul_bind' } },
  '/api/cosmic/legendary-quest': { POST: { lever: 'cosmic:legendary_quest' } },
  '/api/worlds/{world_id}/deepen': { POST: 'edit_world' },
  '/api/stars/{star_id}/deepen': { POST: 'edit_world' },
  '/api/map-notes': { POST: { lever: 'map_note:add' } },
  '/api/entities/{entity_id}/map-position': { PUT: 'edit_world' },
  '/api/map-notes/{note_id}': { DELETE: { lever: 'map_note:remove' } },
  '/api/threads': { POST: { lever: 'thread:open' } },
  '/api/threads/{thread_id}/close': { POST: { lever: 'thread:close' } },
  '/api/book/pdf': { POST: 'download_books' },
  '/api/prayers/{message_id}/answer': { POST: { lever: 'answer_prayer' } },
  '/api/councils': { POST: 'edit_world' },
  '/api/graph/repair': { POST: 'edit_world' },
  '/api/graph/fate-link': { POST: 'edit_world' },
  '/api/graph/fate-link/stop': { POST: 'edit_world' },
  '/api/languages/{language_id}/sample-names': { POST: 'view' },
  '/api/languages/{language_id}/translate': { POST: 'view' },
  '/api/languages/{language_id}/words': { POST: { lever: 'language:words' } },
  '/api/images': { POST: 'edit_world' },
  '/api/images/{image_id}/cover': { PUT: 'edit_world' },
  '/api/images/{image_id}/caption': { PUT: 'edit_world' },
  '/api/images/{image_id}': { DELETE: 'edit_world' },
  '/api/image-gen': { POST: 'generate_images' },
  '/api/image-gen/batch/start': { POST: 'generate_images' },
  '/api/image-gen/batch/restyle': { POST: 'generate_images' },
  '/api/image-gen/batch/stop': { POST: 'generate_images' },
  '/api/entities/prompts/write-missing': { POST: 'generate_images' },
  '/api/batch-deepen/start': { POST: 'edit_world' },
  '/api/batch-deepen/stop': { POST: 'edit_world' },
  '/api/names/assign-missing': { POST: 'edit_world' },
  '/api/notifications': { POST: 'view' },
  '/api/notifications/read': { POST: 'view' },
  '/api/notifications/settings': { PUT: 'view' },
  '/api/notifications/from-chronicle/{chronicle_id}': { POST: 'view' },
  '/api/ledger/{entry_id}/undo': { POST: 'undo' },
  '/api/scenarios': { POST: { lever: 'scenario:start' } },
  '/api/scenarios/custom': { POST: { lever: 'scenario:custom' } },
  '/api/scenarios/{scenario_id}/edit': { POST: { lever: 'scenario:edit' } },
  '/api/scenarios/{scenario_id}/hold': { POST: { lever: 'scenario:hold' } },
  '/api/scenarios/{scenario_id}/abandon': {
    POST: { lever: 'scenario:abandon' },
  },
  '/api/scenarios/{scenario_id}/delete': { POST: { lever: 'scenario:delete' } },
  '/api/settings': { PATCH: { lever: 'settings' } },
  '/api/peoples/awaken': { POST: { lever: 'awaken_peoples' } },
  '/api/federations': { POST: { lever: 'federation' } },
  '/api/cheats/essence': { POST: { lever: 'cheat:essence' } },
  '/api/backups': { POST: 'export' },
  '/api/backups/secondary': { PUT: 'admin' },
  '/api/backups/restore': { POST: 'admin' },
  '/api/world/reset': { POST: 'admin' },
  '/api/world/import': { POST: 'admin' },
  '/api/discovery/end': { POST: 'edit_world' },
  '/api/maintenance/tasks/{task}/run': { POST: 'edit_world' },
  '/api/maintenance/backups/{file_name}/verify': { POST: 'export' },
  '/api/maintenance/sons/{son_id}/powers': { POST: 'edit_world' },
  '/api/maintenance/cosmos-prompts': { POST: 'edit_world' },
  '/api/maintenance/chronicles': { POST: 'edit_world' },
  '/api/prompt-context/tired-motifs/overrides': { PUT: 'change_rules' },
  '/api/prompt-context/tired-motifs/overrides/clear': { POST: 'change_rules' },
  '/api/cosmography/nodes/{node_id}/deepen': { POST: 'edit_world' },
  '/api/divine-will/sessions/{session_id}': { PATCH: 'author' },
  '/api/divine-will/cycles': { POST: 'divine_will_mode' },
  '/api/divine-will/cycles/{cycle_id}/cancel': { POST: 'author' },
  '/api/divine-will/confirmations/{confirmation_id}': { POST: 'edit_world' },
  '/api/divine-will/session/reset': { POST: 'author' },
  '/api/divine-will/attachments': { POST: 'divine_will_read' },
  '/api/divine-will/artifacts/{artifact_id}': {
    PATCH: 'author',
    DELETE: 'author',
  },
  '/api/divine-will/plans/{plan_id}/steps': { PUT: 'edit_world' },
  '/api/divine-will/plans/{plan_id}/approve': { POST: 'edit_world' },
  '/api/divine-will/plans/{plan_id}/execute': { POST: 'edit_world' },
  '/api/divine-will/plans/{plan_id}/pause': { POST: 'edit_world' },
  '/api/divine-will/plans/{plan_id}/resume': { POST: 'edit_world' },
  '/api/divine-will/plans/{plan_id}/abandon': { POST: 'edit_world' },
  '/api/divine-will/plans/{plan_id}/steps/{ordinal}/skip': {
    POST: 'edit_world',
  },
  '/api/divine-will/plans/{plan_id}/steps/{ordinal}/undo': {
    POST: 'undo',
  },
  '/api/divine-will/forecasts/{forecast_id}/cancel': {
    POST: 'alternative_histories',
  },
  '/api/presence/sessions': { POST: 'presence_record' },
  '/api/presence/sessions/{session_id}/exchanges': { POST: 'presence_record' },
  '/api/presence/exchanges/{exchange_id}/cancel': { POST: 'author' },
  '/api/presence/sessions/{session_id}/close': { POST: 'author' },
  '/api/presence/sessions/{session_id}': { PATCH: 'author' },
  '/api/divine-will/plans/{plan_id}': { PATCH: 'author' },
  '/api/divine-will/forecasts/{forecast_id}': { PATCH: 'author' },
  '/api/presence': { POST: 'view', DELETE: 'view' },
  '/api/team/queue/{act_id}': { DELETE: 'author' },
  '/api/team/queue/{act_id}/retry': { POST: 'author' },
  '/api/team/proposals/{proposal_id}/approve': { POST: 'admin' },
  '/api/team/proposals/{proposal_id}/reject': { POST: 'admin' },
  '/api/team/proposals/{proposal_id}/withdraw': { POST: 'author' },
}
