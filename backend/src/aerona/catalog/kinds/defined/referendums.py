from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.referendums import CampaignMeans, Franchise

CAMPAIGN_MEANS = total(
    CampaignMeans,
    {
        CampaignMeans.MONEY: Defined("Money", checked_by=("tools.mortal.referendums.campaign_for_vote_tool",), used_by=()),
        CampaignMeans.MEDIA: Defined("Media", checked_by=("tools.mortal.referendums.campaign_for_vote_tool",), used_by=()),
        CampaignMeans.SPEECH: Defined("Speech", checked_by=("tools.mortal.referendums.campaign_for_vote_tool",), used_by=()),
        CampaignMeans.FRAUD: Defined("Fraud", checked_by=("tools.mortal.referendums.campaign_for_vote_tool",), used_by=()),
    },
)

FRANCHISE = total(
    Franchise,
    {
        Franchise.NOBLES: Defined("Nobles", checked_by=(), used_by=("db.tables.referendums.ReferendumRow", "engine.referendums.book.franchise_at")),
        Franchise.LANDHOLDERS: Defined("Landholders", checked_by=(), used_by=()),
        Franchise.CITIZENS: Defined("Citizens", checked_by=(), used_by=()),
        Franchise.FREE: Defined("Free", checked_by=(), used_by=()),
        Franchise.ALL: Defined("All", checked_by=(), used_by=("engine.referendums.book.franchise_at",)),
    },
)
