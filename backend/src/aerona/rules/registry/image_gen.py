from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ImageGenRules:
    width: int = rule(720, 256, 3840, RuleGroup.IMAGE_GENERATION, "Width of the generated image (px)")
    height: int = rule(720, 256, 3840, RuleGroup.IMAGE_GENERATION, "Height of the generated image (px)")
    steps: int = rule(4, 1, 50, RuleGroup.IMAGE_GENERATION, "Denoising steps per image (few: fast, many: detailed)")
    auto: int = rule(0, 0, 1, RuleGroup.IMAGE_GENERATION, "At epoch end, automatically start generation for all records without an image (0 off)")
    idle_unload_seconds: int = rule(
        600, 0, 86400, RuleGroup.IMAGE_GENERATION, "Time for an idle image worker to release the model from memory (s; 0 never releases)"
    )
    startup_timeout_seconds: int = rule(300, 10, 3600, RuleGroup.IMAGE_GENERATION, "Maximum wait for the image worker to load the model (s)")
    image_timeout_seconds: int = rule(300, 10, 3600, RuleGroup.IMAGE_GENERATION, "Maximum time for a single image (s); if exceeded the worker is restarted")
    retries: int = rule(1, 0, 5, RuleGroup.IMAGE_GENERATION, "Retry a failed image in batch generation")
    log_lines: int = rule(200, 20, 5000, RuleGroup.IMAGE_GENERATION, "Lines kept in the image-generation log")
