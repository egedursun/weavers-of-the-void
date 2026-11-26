from aerona_image_worker.domain.enums import BackendName

DEFAULT_MODEL_IDS = {
    BackendName.MLX: "mflux-community/z-image-turbo-mflux-q4",
    BackendName.DIFFUSERS: "unsloth/Z-Image-Turbo-unsloth-bnb-4bit",
    BackendName.FAKE: "aerona/fake-gradient",
}
BACKEND_MODULES = {
    BackendName.MLX: "aerona_image_worker.backends.mlx",
    BackendName.DIFFUSERS: "aerona_image_worker.backends.diffusers",
    BackendName.FAKE: "aerona_image_worker.backends.fake",
}
MLX_PROMPT_PLACEHOLDER = "-"
DIFFUSERS_GPU_DEVICE = "cuda"
DIFFUSERS_CPU_DEVICE = "cpu"
DIFFUSERS_GUIDANCE_SCALE = 0.0
PNG_FORMAT = "PNG"
