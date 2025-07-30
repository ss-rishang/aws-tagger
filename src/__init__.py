"""AWS CloudTrail Resource Tagger Package"""

from .tagger import CloudTrailResourceTagger, CloudTrailResourceTaggerBuilder
from .trail import (
    ResourceType,
    EventExtractor,
    EventExtractorFactory,
    CreationEventManager
)
from .data import (
    TaggingStats,
    ResourceInfo,
    EventProcessingResult,
    ExtractorConfig,
    CloudTrailEventSummary,
    TaggingConfig
)
from .utils import logger

__all__ = [
    'CloudTrailResourceTagger',
    'CloudTrailResourceTaggerBuilder', 
    'CreationEventManager',
    'ResourceType',
    'EventExtractor',
    'EventExtractorFactory',
    'TaggingStats',
    'ResourceInfo',
    'EventProcessingResult',
    'ExtractorConfig',
    'CloudTrailEventSummary',
    'TaggingConfig',
    'logger'
]
