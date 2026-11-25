import { cycleNoticeValues } from '@/api/generated/schema'
import {
  type WillActive,
  type WillArtifact,
  type WillArtifactSummary,
  type WillConfirmation,
  type WillCycle,
  type WillCycleEvent,
  type WillForecast,
  type WillPlan,
  type WillPlanStep,
  type WillScenario,
  type CycleNotice,
} from './types'

const AT = '2026-11-20T10:00:00Z'

let nextEvent = 100

export function willEvent(
  kind: WillCycleEvent['kind'],
  payload: Record<string, unknown>,
  tool = ''
): WillCycleEvent {
  nextEvent += 1
  return {
    id: nextEvent,
    ordinal: nextEvent,
    kind,
    tool,
    payload,
    handle: '',
    created_at: AT,
    notice: noticeOf(payload),
  }
}

function noticeOf(payload: Record<string, unknown>): CycleNotice | null {
  const value = payload['notice']
  return cycleNoticeValues.find((notice) => notice === value) ?? null
}

export function willCycle(change: Partial<WillCycle> = {}): WillCycle {
  return {
    id: 1,
    session_id: 1,
    ordinal: 1,
    mode: 'command',
    epoch: 3,
    status: 'done',
    player_text: 'Raise a mountain in the north',
    final_text: '',
    model: 'claude-haiku-5-5',
    input_tokens: 1200,
    output_tokens: 300,
    steps: 2,
    error: '',
    started_at: AT,
    finished_at: AT,
    events: [],
    confirmations: [],
    attachments: [],
    ...change,
  }
}

export function willConfirmation(
  change: Partial<WillConfirmation> = {}
): WillConfirmation {
  return {
    id: 7,
    cycle_id: 1,
    action_id: 'smite_entity',
    input: { entity_id: 12 },
    reason: 'destructive',
    preview: {
      title: 'Smite a record',
      essence: 30,
      deleted_nodes: [{ node_id: 12, name: 'Old Keep', kind: 'entity' }],
      changes: [
        {
          table: 'nodes',
          operation: 'delete',
          node_id: 12,
          node_name: 'Old Keep',
          field: '',
          before: '',
          after: '',
        },
      ],
      tallies: [{ operation: 'delete', table: 'nodes', count: 1 }],
    },
    status: 'pending',
    decided_at: null,
    ledger_entry_id: null,
    created_at: AT,
    ...change,
  }
}

export const OWNED = {
  author_account_id: null,
  author_name: null,
  shared: false,
  mine: true,
}

export function willActive(
  cycles: WillCycle[],
  change: Partial<WillActive> = {}
): WillActive {
  return {
    session: {
      id: 1,
      title: '',
      opened_epoch: 1,
      opened_at: AT,
      closed_epoch: null,
      closed_at: null,
      cycle_count: cycles.length,
      author: null,
      shared: false,
      mine: true,
    },
    cycles,
    memory_boundary: 1,
    has_earlier: false,
    remembered_cycles: 10,
    running_cycle_id: null,
    capabilities: {
      enabled: true,
      images: false,
      probed: true,
      note: '',
      model: 'claude-haiku-5-5',
      upload_max_files: 10,
      upload_max_mb: 50,
    },
    ...change,
  }
}

export function willStep(change: Partial<WillPlanStep> = {}): WillPlanStep {
  return {
    ordinal: 1,
    title: 'Raise the range',
    action_id: 'raise_mountain',
    action_title: 'Raise a mountain',
    input: { region_id: 4 },
    depends_on: [],
    declared_impact: 'safe',
    estimated_essence: 5,
    status: 'pending',
    ledger_entry_id: null,
    job_id: '',
    result_text: '',
    error: '',
    ...change,
  }
}

export function willPlan(change: Partial<WillPlan> = {}): WillPlan {
  return {
    owner: OWNED,
    id: 5,
    title: 'Shape the north',
    status: 'draft',
    cycle_id: 1,
    artifact_id: null,
    approved_at: null,
    finished_at: null,
    created_at: AT,
    steps: [
      willStep(),
      willStep({
        ordinal: 2,
        title: 'Seed the valleys',
        action_id: 'seed_forest',
        depends_on: [1],
      }),
    ],
    job_id: '',
    waiting_step: null,
    ...change,
  }
}

function scenario(change: Partial<WillScenario> = {}): WillScenario {
  return {
    population: 1000,
    prosperity: 40,
    communities: 12,
    deaths: [{ category: 'plague', deaths: 30 }],
    wars: { ongoing: 1, begun: 1, ended: 0 },
    nodes: [],
    chronicle: [
      { epoch: 4, year: 12, text: 'The harvest failed in the east.' },
    ],
    seconds: 30,
    ...change,
  }
}

export function willForecast(change: Partial<WillForecast> = {}): WillForecast {
  return {
    owner: OWNED,
    id: 9,
    cycle_id: 1,
    epochs: 2,
    status: 'queued',
    eta_seconds: 70,
    interventions: [{ action_id: 'raise_mountain', input: { region_id: 4 } }],
    report: null,
    job_id: 'job-9',
    error: '',
    epochs_done: 0,
    started_at: null,
    finished_at: null,
    created_at: AT,
    ...change,
  }
}

export const DONE_REPORT: WillForecast['report'] = {
  start_epoch: 3,
  end_epoch: 5,
  start_population: 900,
  start_prosperity: 35,
  start_communities: 10,
  start_wars: 0,
  interventions: [
    {
      action_id: 'raise_mountain',
      action_title: 'Raise a mountain',
      message: 'A range rises.',
      essence_spent: 5,
    },
  ],
  baseline: scenario(),
  intervened: scenario({
    population: 1100,
    chronicle: [
      { epoch: 5, year: null, text: 'The range sheltered the valleys.' },
    ],
  }),
  seconds: 61,
}

export function willArtifactSummary(
  change: Partial<WillArtifactSummary> = {}
): WillArtifactSummary {
  return {
    owner: OWNED,
    id: 3,
    title: 'The First Winter',
    kind: 'story',
    format: 'markdown',
    status: 'draft',
    language: 'English',
    mode: 'creative_work',
    tags: ['winter'],
    subjects: [],
    current_version: 2,
    characters: 1800,
    created_cycle_id: 1,
    plan_id: null,
    created_at: AT,
    updated_at: AT,
    ...change,
  }
}

export function willArtifact(
  summary: WillArtifactSummary,
  body: string
): WillArtifact {
  return {
    artifact: summary,
    body,
    version: summary.current_version,
    versions: [
      {
        version: 1,
        summary: 'First draft',
        cycle_id: 1,
        characters: 900,
        created_at: AT,
      },
      {
        version: 2,
        summary: 'Longer',
        cycle_id: 1,
        characters: 1800,
        created_at: AT,
      },
    ],
  }
}
