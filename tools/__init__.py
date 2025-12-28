# image generator
from .image_generator_doubao_seedream_yunwu_api import ImageGeneratorDoubaoSeedreamYunwuAPI

# Try to import Nanobanana Yunwu API (requires google-genai)
try:
    from .image_generator_nanobanana_yunwu_api import ImageGeneratorNanobananaYunwuAPI
    NANOBANANA_YUNWU_AVAILABLE = True
except Exception as e:
    ImageGeneratorNanobananaYunwuAPI = None
    NANOBANANA_YUNWU_AVAILABLE = False
    print(f"⚠️  ImageGeneratorNanobananaYunwuAPI not available: {type(e).__name__}: {str(e)[:100]}")

# Try to import Google API tools (optional dependency)
try:
    from .image_generator_nanobanana_google_api import ImageGeneratorNanobananaGoogleAPI
    GOOGLE_IMAGE_AVAILABLE = True
except Exception as e:
    ImageGeneratorNanobananaGoogleAPI = None
    GOOGLE_IMAGE_AVAILABLE = False
    print(f"⚠️  ImageGeneratorNanobananaGoogleAPI not available: {type(e).__name__}: {str(e)[:100]}")

# reranker for rag
from .reranker_bge_silicon_api import RerankerBgeSiliconapi

# video generator
from .video_generator_doubao_seedance_yunwu_api import VideoGeneratorDoubaoSeedanceYunwuAPI
from .video_generator_veo_yunwu_api import VideoGeneratorVeoYunwuAPI

# Try to import Google Video API (optional dependency)
try:
    from .video_generator_veo_google_api import VideoGeneratorVeoGoogleAPI
    GOOGLE_VIDEO_AVAILABLE = True
except Exception as e:
    VideoGeneratorVeoGoogleAPI = None
    GOOGLE_VIDEO_AVAILABLE = False
    print(f"⚠️  VideoGeneratorVeoGoogleAPI not available: {type(e).__name__}: {str(e)[:100]}")


__all__ = [
    "ImageGeneratorDoubaoSeedreamYunwuAPI",
    "RerankerBgeSiliconapi",
    "VideoGeneratorDoubaoSeedanceYunwuAPI",
    "VideoGeneratorVeoYunwuAPI",
]

# Add optional tools to __all__ if available
if NANOBANANA_YUNWU_AVAILABLE:
    __all__.append("ImageGeneratorNanobananaYunwuAPI")
if GOOGLE_IMAGE_AVAILABLE:
    __all__.append("ImageGeneratorNanobananaGoogleAPI")
if GOOGLE_VIDEO_AVAILABLE:
    __all__.append("VideoGeneratorVeoGoogleAPI")