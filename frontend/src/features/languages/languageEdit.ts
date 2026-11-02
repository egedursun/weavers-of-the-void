import { type LanguageEdit, type WritingSystem } from './api'
import { type LanguageNode } from './languageFamilies'

export const UNWRITTEN = 'unwritten'
const NAMES_MAX = 50

export type ScriptChoice = WritingSystem | typeof UNWRITTEN

export type Draft = {
  script: ScriptChoice
  alphabet: string
  names: string
  forgetNames: boolean
  consonants: string
  cluster: string
  ending: string
  clearSignature: boolean
}

export function initialDraft(node: LanguageNode): Draft {
  return {
    script: node.writing_system ?? UNWRITTEN,
    alphabet: node.alphabet.join(''),
    names: '',
    forgetNames: false,
    consonants: node.signature?.consonants ?? '',
    cluster: node.signature?.cluster ?? '',
    ending: node.signature?.ending ?? '',
    clearSignature: false,
  }
}

function nameList(text: string): string[] {
  return text
    .split('\n')
    .map((name) => name.trim())
    .filter(Boolean)
    .slice(0, NAMES_MAX)
}

export function changesOf(node: LanguageNode, draft: Draft): LanguageEdit {
  const change: LanguageEdit = {
    language_id: node.language.id,
    clear_writing_system: false,
    clear_signature: false,
  }
  const script = node.writing_system ?? UNWRITTEN
  if (draft.script !== script) {
    if (draft.script === UNWRITTEN) change.clear_writing_system = true
    else change.writing_system = draft.script
  }
  if (draft.alphabet.trim() !== node.alphabet.join(''))
    change.alphabet = draft.alphabet.trim()
  const names = nameList(draft.names)
  if (draft.forgetNames) change.sample_names = []
  else if (names.length > 0) change.sample_names = names
  if (draft.clearSignature) change.clear_signature = node.signature !== null
  else {
    const before = node.signature
    const consonants = draft.consonants.trim()
    const changed =
      consonants !== (before?.consonants ?? '') ||
      draft.cluster.trim() !== (before?.cluster ?? '') ||
      draft.ending.trim() !== (before?.ending ?? '')
    if (changed && consonants)
      change.signature = {
        consonants,
        cluster: draft.cluster.trim(),
        ending: draft.ending.trim(),
        length_bias: before?.length_bias ?? 0,
      }
  }
  return change
}

export function hasChanges(change: LanguageEdit): boolean {
  return (
    change.clear_writing_system ||
    change.clear_signature ||
    change.writing_system !== undefined ||
    change.alphabet !== undefined ||
    change.sample_names !== undefined ||
    change.signature !== undefined
  )
}
