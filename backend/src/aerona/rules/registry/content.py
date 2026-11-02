from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ContentRules:
    image_prompt_batch: int = rule(24, 1, 500, RuleGroup.CONTENT_JOBS, "Maximum entities in one image-prompt batch")
    image_prompt_description_chars: int = rule(500, 20, 20000, RuleGroup.CONTEXT_BUDGETS, "Image-prompt request: entity description (characters)")
    image_prompt_min_chars: int = rule(20, 0, 2000, RuleGroup.CONTENT_JOBS, "An image prompt shorter than this is not accepted (characters)")
    cosmic_image_prompt_max_chars: int = rule(1200, 50, 20000, RuleGroup.CONTENT_JOBS, "Maximum length of a cosmic body's image prompt (characters)")
    cosmic_prompt_batch: int = rule(16, 1, 500, RuleGroup.CONTENT_JOBS, "Cosmic bodies whose image prompts are written in one batch")
    cosmic_prompt_world_chars: int = rule(400, 20, 20000, RuleGroup.CONTEXT_BUDGETS, "Cosmos prompt request: world description (characters)")
    cosmic_prompt_other_chars: int = rule(300, 20, 20000, RuleGroup.CONTEXT_BUDGETS, "Cosmos prompt request: star and foreign-god description (characters)")
    revelation_max_power: int = rule(10, 1, 11, RuleGroup.CONTENT_JOBS, "Maximum power level of a revelation")
    deepen_neighbor_links: int = rule(20, 0, 1000, RuleGroup.CONTEXT_BUDGETS, "Deepening: neighbouring links")
