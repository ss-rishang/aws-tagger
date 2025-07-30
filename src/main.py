from typing import Dict, List
from .tagger import CloudTrailResourceTagger, CloudTrailResourceTaggerBuilder
from .trail import CreationEventManager, ResourceType
from .utils import logger
from .data import EventProcessingResult, TaggingStats, TaggingConfig


def main(region = 'us-east-1' ):
    """Main function demonstrating different usage patterns for a single region"""
    
    try:
        # Example 1: Basic usage with default configuration
        print(f"=== Basic Usage (Region: {region}) ===")
        tagger = CloudTrailResourceTagger(region_name=region)
        result = tagger.run(hours=24)
        print(f"Basic stats: {result.stats}")
        print(f"Processing time: {result.duration_seconds:.2f} seconds")
        print(f"Success rate: {result.stats.success_rate:.1f}%")
        
        # Show detailed resource information
        if result.resources:
            print(f"\nDetailed Resource Information:")
            for resource in result.resources[:5]:  # Show first 5 resources
                status = "✅ Tagged" if resource.tagged else "❌ Failed"
                time_str = resource.event_time.strftime('%Y-%m-%d %H:%M:%S') if resource.event_time else 'Unknown'
                print(f"  {status} {resource.resource_type}:{resource.resource_id}")
                print(f"    Created by: {resource.username} at {time_str}")
                print(f"    Event: {resource.event_name}")
                if resource.error_message:
                    print(f"    Error: {resource.error_message}")
                print()
        
        # Example 2: Using Builder Pattern with custom extractors
        print(f"\n=== Using Builder Pattern with Custom Extractors (Region: {region}) ===")
        
        # Custom extraction function example
        def extract_custom_resource(cloud_trail_event: Dict) -> List[str]:
            """Custom extraction function example"""
            # Example: extract from a nested structure
            custom_data = cloud_trail_event.get('customSection', {})
            return [custom_data.get('customResourceId')] if custom_data.get('customResourceId') else []
        
        tagger_builder = (CloudTrailResourceTaggerBuilder()
                         .set_region(region)
                         .add_path_extractor(
                             event_name='CreateCustomResource',
                             resource_type=ResourceType.EC2_INSTANCE,  # or create new ResourceType
                             section='responseElements',
                             simple_path=['customResourceId']
                         )
                         .add_function_extractor(
                             event_name='CreateComplexResource',
                             resource_type=ResourceType.S3_BUCKET,
                             extraction_function=extract_custom_resource
                         )
                         .build())
        
        result = tagger_builder.run(hours=12)
        print(f"Builder stats: {result.stats}")
        print(f"Processing time: {result.duration_seconds:.2f} seconds")
        print(f"Resources found: {len(result.resources)}")
        
        # Example 3: Custom Creation Event Manager with manual configuration
        print(f"\n=== Custom Event Manager (Region: {region}) ===")
        custom_manager = CreationEventManager()
        
        # Add custom extractor using path-based approach
        custom_manager.add_path_based_extractor(
            event_name='CreateNewServiceResource',
            resource_type=ResourceType.LAMBDA_FUNCTION,
            section='requestParameters',
            simple_path=['newResourceName']
        )
        
        # Add custom extractor using function-based approach
        custom_manager.add_function_based_extractor(
            event_name='CreateComplexService',
            resource_type=ResourceType.RDS_INSTANCE,
            extraction_function=lambda event: [event.get('specialField', {}).get('resourceId')]
        )
        
        # Example 4: EKS Support demonstration
        print(f"\n=== EKS Support Example (Region: {region}) ===")
        eks_manager = CreationEventManager()
        
        # EKS cluster creation is already supported by default
        # EKS nodegroup creation is also supported by default
        # You can also add custom EKS-related extractors
        eks_manager.add_path_based_extractor(
            event_name='CreateEKSAddon',
            resource_type=ResourceType.EKS_CLUSTER,  # Could add EKS_ADDON if needed
            section='responseElements',
            simple_path=['addon', 'addonName']
        )
        
        tagger_custom = (CloudTrailResourceTaggerBuilder()
                        .set_region(region)
                        .with_creation_event_manager(custom_manager)
                        .build())
        
        result = tagger_custom.run(hours=6)
        print(f"Custom manager stats: {result.stats}")
        
        # Example 5: Configurable Tagging Example
        print(f"\n=== Configurable Tagging Example (Region: {region}) ===")
        
        # Create custom tagging configuration
        custom_tagging_config = TaggingConfig(
            owner_tag_name="CreatedBy",  # Use custom owner tag name
            creation_time_tag_name="ResourceCreatedAt",  # Custom creation time tag name
            creation_time_format="%Y-%m-%d %H:%M",  # Custom date format
            include_creation_time=True,
            additional_tags={
                "Environment": "Production",
                "ManagedBy": "AutoTagger",
                "CostCenter": "Engineering"
            }
        )
        
        # Build tagger with custom configuration
        custom_tagger = (CloudTrailResourceTaggerBuilder()
                        .set_region(region)
                        .with_tagging_config(custom_tagging_config)
                        .build())
        
        # Alternative using fluent interface methods
        fluent_tagger = (CloudTrailResourceTaggerBuilder()
                        .set_region(region)
                        .set_owner_tag_name("ResourceOwner")
                        .set_creation_time_tag_name("DateCreated")
                        .set_creation_time_format("%Y/%m/%d %H:%M:%S")
                        .add_additional_tag("Team", "DevOps")
                        .add_additional_tag("Project", "AutoTagging")
                        .enable_creation_time_tagging(True)
                        .build())
        
        result = custom_tagger.run(hours=3)
        print(f"Custom tagging stats: {result.stats}")
        print(f"Tags applied: CreatedBy, ResourceCreatedAt, Environment, ManagedBy, CostCenter")
        
        # Print supported events including EKS
        print(f"\nSupported creation events: {custom_manager.get_supported_events()}")
        
        print("\n" + "="*50)
        print(f"CLOUDTRAIL RESOURCE TAGGING SUMMARY (Region: {region})")
        print("="*50)
        print(f"Events Processed: {result.stats.processed}")
        print(f"Resources Tagged: {result.stats.tagged}")
        print(f"Errors: {result.stats.errors}")
        print(f"Success Rate: {result.stats.success_rate:.1f}%")
        print(f"Processing Duration: {result.duration_seconds:.2f} seconds")
        print(f"Total Resources Found: {len(result.resources)}")
        print("="*50)
        print("\nTags Applied to Each Resource:")
        print("- Owner tag: (configurable name, defaults to 'owner')")
        print("- Creation time tag: (configurable name and format, defaults to 'creation-time')")
        print("- Additional static tags: (configurable key-value pairs)")
        print("- All tag names and formats are customizable via TaggingConfig")
        print("\nSupported AWS Services:")
        print("- EC2 (Instances, Volumes, Security Groups, VPCs, Subnets, Snapshots, Images, Elastic IPs)")
        print("- S3 (Buckets)")
        print("- RDS (DB Instances, DB Clusters)")
        print("- Lambda (Functions)")
        print("- ELB (Load Balancers, Target Groups)")
        print("- EKS (Clusters, Node Groups)")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        raise


if __name__ == "__main__":
    main()