import { CandlestickChart } from 'lucide-react'
import type { RecordFamily } from '@/features/entity/sections/recordLevers'

export const SECURITIES: RecordFamily = {
  id: 'securities',
  section: 'section-securities',
  title: 'Securities',
  description:
    'Claims traded at a price: the exchanges a town holds, with their owner, brokers, listing fee, margin and mood; the shares, bonds, annuities, notes and futures an issuer has listed, with their amount, face value, coupon, maturity, price, the belief behind it, bubbles, defaults and delisting; the holdings of each holder with what they paid and what they bought on credit; and the price and volume of each claim epoch by epoch.',
  icon: CandlestickChart,
  tone: 'gold',
  empty:
    'Nothing here is traded. A town with a bank and enough people opens an exchange; a company, a realm, a town or any issuer can list claims, and anyone who holds one, a being, an organisation, a realm, a world, a star or a god, shows its holdings here.',
  tables: {
    stock_exchanges: {
      create: 'stock_exchange:create',
      edit: 'stock_exchange:edit',
      remove: 'stock_exchange:delete',
    },
    issued_securities: {
      create: 'issued_security:create',
      edit: 'issued_security:edit',
      remove: 'issued_security:delete',
    },
    security_holdings: {
      create: 'security_holding:create',
      edit: 'security_holding:edit',
      remove: 'security_holding:delete',
    },
    security_prices: {
      create: 'security_price:create',
      edit: 'security_price:edit',
      remove: 'security_price:delete',
    },
  },
}
