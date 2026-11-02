from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import SkyCalendarContext
from aerona.rules.registry import Rules


def sky_calendar(rules: Rules, epoch: int) -> str:
    return render(PromptId.SKY_CALENDAR, SkyCalendarContext(age=epoch, period=rules.travel.alignment_period))
