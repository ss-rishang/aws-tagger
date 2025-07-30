# AWS CloudTrail Resource Tagger Architecture

```mermaid
graph TD
    A[CloudTrailResourceTagger] --> B[CloudTrail Client]
    A --> C[CreationEventManager]
    A --> D[TaggingStrategyFactory]
    A --> E[Data Classes]
    
    C --> F[EventExtractorFactory]
    F --> G[EventExtractor]
    
    D --> H[EC2TaggingStrategy]
    D --> I[S3TaggingStrategy]
    D --> J[RDSTaggingStrategy]
    D --> K[LambdaTaggingStrategy]
    D --> L[ELBTaggingStrategy]
    D --> M[EKSTaggingStrategy]
    
    A --> N[AWS Service Clients]
    N --> H
    N --> I
    N --> J
    N --> K
    N --> L
    N --> M
    
    O[CloudTrailResourceTaggerBuilder] --> A
    
    subgraph "Configuration"
        O
        E
    end
    
    subgraph "Event Processing"
        B
        C
        F
        G
    end
    
    subgraph "Resource Tagging"
        D
        H
        I
        J
        K
        L
        M
        N
    end
    
    subgraph "Data Structures"
        E
    end
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style O fill:#fce4ec
    style E fill:#f1f8e9
```

## Detailed Flow

```mermaid
sequenceDiagram
    participant User
    participant Builder
    participant Tagger
    participant CloudTrail
    participant EventManager
    participant Extractor
    participant StrategyFactory
    participant Strategies
    participant AWS
    
    User->>Builder: Configure tagger
    Builder->>Tagger: Build instance
    User->>Tagger: run(hours)
    Tagger->>CloudTrail: get_cloudtrail_events(hours)
    CloudTrail-->>Tagger: events
    Tagger->>EventManager: filter_creation_events(events)
    EventManager-->>Tagger: creation_events
    loop For each event
        Tagger->>EventManager: extract_resources_from_event(event)
        EventManager->>Extractor: extract_resources(event)
        Extractor-->>EventManager: resources
        EventManager-->>Tagger: resources
        loop For each resource
            Tagger->>StrategyFactory: create_strategy(resource_type)
            StrategyFactory-->>Tagger: strategy
            Tagger->>Strategies: tag_resource(resource_id, tags)
            Strategies->>AWS: AWS API calls
            AWS-->>Strategies: response
            Strategies-->>Tagger: success/failure
        end
    end
    Tagger->>User: EventProcessingResult
```

## Component Relationships

```mermaid
classDiagram
    class CloudTrailResourceTaggerBuilder {
        +set_region()
        +with_creation_event_manager()
        +with_tagging_config()
        +add_path_extractor()
        +add_function_extractor()
        +build()
    }
    
    class CloudTrailResourceTagger {
        +get_cloudtrail_events()
        +filter_creation_events()
        +process_events()
        +tag_resource()
        +get_event_summary()
        +run()
    }
    
    class CreationEventManager {
        +is_creation_event()
        +extract_resources_from_event()
        +add_path_based_extractor()
        +add_function_based_extractor()
    }
    
    class EventExtractorFactory {
        +create_extractor()
        +register_extractor_config()
        +register_custom_extractor()
    }
    
    class EventExtractor {
        +extract_resources()
    }
    
    class TaggingStrategyFactory {
        +create_strategy()
    }
    
    class TaggingStrategy {
        <<abstract>>
        +tag_resource()
    }
    
    class TaggingConfig {
        +owner_tag_name
        +creation_time_tag_name
        +additional_tags
    }
    
    class ResourceInfo {
        +resource_type
        +resource_id
        +event_name
        +username
    }
    
    class TaggingStats {
        +processed
        +tagged
        +errors
        +success_rate
    }
    
    class EventProcessingResult {
        +stats
        +resources
        +start_time
        +end_time
    }
    
    CloudTrailResourceTaggerBuilder --> CloudTrailResourceTagger
    CloudTrailResourceTagger --> CreationEventManager
    CloudTrailResourceTagger --> TaggingStrategyFactory
    CloudTrailResourceTagger --> TaggingConfig
    CreationEventManager --> EventExtractorFactory
    EventExtractorFactory --> EventExtractor
    CloudTrailResourceTagger --> TaggingStrategyFactory
