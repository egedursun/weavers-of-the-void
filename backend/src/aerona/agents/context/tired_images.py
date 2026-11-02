from aerona.agents.context.scope import Scope
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.blocks import TiredImagesContext
from aerona.prompts.contexts.common import TiredImages


async def tired_images(scope: Scope, world_id: int | None) -> TiredImages:
    return await scope.motifs.context(scope.session, scope.rules, world_id)


def tired_images_text(images: TiredImages) -> str:
    return render(PromptId.TIRED_IMAGES, TiredImagesContext(images=images)) if images.present else ""
