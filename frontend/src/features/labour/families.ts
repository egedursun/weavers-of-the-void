import { Flag, HardHat } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const LABOUR: RecordFamily = {
  id: 'labour',
  section: 'section-labour',
  title: 'Labour',
  description:
    'The organised work of a place or an organisation: the worker bodies that speak for its trades, with their form, members, dues, strike fund, solidarity and standing in law; the contracts that set wages, hours, safety, rest and keep between hirers and workers; and the disputes in which workers strike, slow, boycott, occupy or sabotage, or hirers lock them out, with those out, the losses of each side, the injured and how each ended.',
  icon: HardHat,
  tone: 'warning',
  empty:
    'Nothing here bargains over work. Towns hold worker bodies, contracts and disputes; a hirer of any kind, an organisation, a being, a realm, a world, a star or a god, can be a party to a contract or a dispute, and those rows show here.',
  tables: {
    worker_bodies: {
      create: 'worker_body:create',
      edit: 'worker_body:edit',
      remove: 'worker_body:delete',
    },
    labour_contracts: {
      create: 'labour_contract:create',
      edit: 'labour_contract:edit',
      remove: 'labour_contract:delete',
    },
    labour_disputes: {
      create: 'labour_dispute:create',
      edit: 'labour_dispute:edit',
      remove: 'labour_dispute:delete',
      step: {
        action: 'labour_dispute:end',
        label: 'Settle this dispute',
        field: 'record_id',
        icon: Flag,
        ready: (values) =>
          String(values.outcome) === 'ongoing'
            ? null
            : 'Only a dispute still running can be settled',
      },
    },
  },
}
