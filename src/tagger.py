import boto3
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Tuple

from .trail import ResourceType, CreationEventManager
from .utils import logger
from .data import TaggingStats, ResourceInfo, EventProcessingResult, CloudTrailEventSummary, TaggingConfig
from .tagging_strategy import TaggingStrategyFactory


class CloudTrailResourceTaggerBuilder:
    """Builder for CloudTrailResourceTagger configuration"""
    
    def __init__(self):
        self._region = 'us-east-1'
        self._creation_event_manager = None
        self._custom_extractors = []
        self._tagging_config = TaggingConfig()
    
    def set_region(self, region: str) -> 'CloudTrailResourceTaggerBuilder':
        """Set AWS region"""
        self._region = region
        return self
    
    def with_creation_event_manager(self, manager: CreationEventManager) -> 'CloudTrailResourceTaggerBuilder':
        """Set custom creation event manager"""
        self._creation_event_manager = manager
        return self
    
    def with_tagging_config(self, config: TaggingConfig) -> 'CloudTrailResourceTaggerBuilder':
        """Set custom tagging configuration"""
        self._tagging_config = config
        return self
    
    def set_owner_tag_name(self, tag_name: str) -> 'CloudTrailResourceTaggerBuilder':
        """Set the name for the owner tag"""
        self._tagging_config.owner_tag_name = tag_name
        return self
    
    def set_creation_time_tag_name(self, tag_name: str) -> 'CloudTrailResourceTaggerBuilder':
        """Set the name for the creation time tag"""
        self._tagging_config.creation_time_tag_name = tag_name
        return self
    
    def set_creation_time_format(self, format_string: str) -> 'CloudTrailResourceTaggerBuilder':
        """Set the format for creation time tags"""
        self._tagging_config.creation_time_format = format_string
        return self
    
    def enable_creation_time_tagging(self, enable: bool = True) -> 'CloudTrailResourceTaggerBuilder':
        """Enable or disable creation time tagging"""
        self._tagging_config.include_creation_time = enable
        return self
    
    def add_additional_tag(self, key: str, value: str) -> 'CloudTrailResourceTaggerBuilder':
        """Add an additional static tag to all resources"""
        self._tagging_config.additional_tags[key] = value
        return self
    
    def add_path_extractor(self, event_name: str, resource_type: ResourceType, 
                          section: str, simple_path: List[str] = None,
                          array_path: List[str] = None, item_key: str = None) -> 'CloudTrailResourceTaggerBuilder':
        """Add path-based extractor"""
        self._custom_extractors.append({
            'type': 'path',
            'event_name': event_name,
            'resource_type': resource_type,
            'section': section,
            'simple_path': simple_path,
            'array_path': array_path,
            'item_key': item_key
        })
        return self
    
    def add_function_extractor(self, event_name: str, resource_type: ResourceType,
                             extraction_function: Callable[[Dict], List[str]]) -> 'CloudTrailResourceTaggerBuilder':
        """Add function-based extractor"""
        self._custom_extractors.append({
            'type': 'function',
            'event_name': event_name,
            'resource_type': resource_type,
            'extraction_function': extraction_function
        })
        return self
    
    def build(self) -> 'CloudTrailResourceTagger':
        """Build the CloudTrailResourceTagger instance"""
        # Create creation event manager if not provided
        if self._creation_event_manager is None:
            self._creation_event_manager = CreationEventManager()
        
        # Add any custom extractors
        for extractor_config in self._custom_extractors:
            if extractor_config['type'] == 'path':
                self._creation_event_manager.add_path_based_extractor(
                    extractor_config['event_name'],
                    extractor_config['resource_type'],
                    extractor_config['section'],
                    extractor_config.get('simple_path'),
                    extractor_config.get('array_path'),
                    extractor_config.get('item_key')
                )
            elif extractor_config['type'] == 'function':
                self._creation_event_manager.add_function_based_extractor(
                    extractor_config['event_name'],
                    extractor_config['resource_type'],
                    extractor_config['extraction_function']
                )
        
        return CloudTrailResourceTagger(self._region, self._creation_event_manager, self._tagging_config)


class CloudTrailResourceTagger:
    """Main class for CloudTrail resource tagging"""
    
    def __init__(self, region_name: str = 'us-east-1', creation_event_manager: CreationEventManager = None, tagging_config: TaggingConfig = None):
        """Initialize AWS clients and creation event manager"""
        self.region = region_name
        self.tagging_config = tagging_config or TaggingConfig()
        self.cloudtrail = boto3.client('cloudtrail', region_name=region_name)
        self.ec2 = boto3.client('ec2', region_name=region_name)
        self.s3 = boto3.client('s3')
        self.rds = boto3.client('rds', region_name=region_name)
        self.lambda_client = boto3.client('lambda', region_name=region_name)
        self.elbv2 = boto3.client('elbv2', region_name=region_name)
        self.eks = boto3.client('eks', region_name=region_name)
        self.iam = boto3.client('iam')
        self.sts = boto3.client('sts')
        
        # Use provided manager or create default one
        self.creation_event_manager = creation_event_manager or CreationEventManager()

    def get_cloudtrail_events(self, hours=24) -> List[Dict]:
        """Retrieve CloudTrail events from the past specified hours"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        logger.info(f"Fetching CloudTrail events from {start_time} to {end_time}")
        
        events = []
        paginator = self.cloudtrail.get_paginator('lookup_events')
        
        try:
            for page in paginator.paginate(
                StartTime=start_time,
                EndTime=end_time,
                LookupAttributes=[
                    {
                        'AttributeKey': 'ReadOnly',
                        'AttributeValue': 'false'
                    }
                ]
            ):
                events.extend(page['Events'])
                
        except Exception as e:
            logger.error(f"Error fetching CloudTrail events: {e}")
            return []
            
        logger.info(f"Retrieved {len(events)} write-only events")
        return events

    def filter_creation_events(self, events: List[Dict]) -> List[Dict]:
        """Filter events to only include resource creation events"""
        creation_events = []
        
        for event in events:
            event_name = event.get('EventName', '')
            if self.creation_event_manager.is_creation_event(event_name):
                creation_events.append(event)
                logger.info(f"Found creation event: {event_name} by {event.get('Username', 'Unknown')}")
        
        logger.info(f"Filtered to {len(creation_events)} creation events")
        return creation_events

    def _prepare_tags(self, username: str, creation_time: str = None) -> List[Dict[str, str]]:
        """Prepare tags for resource tagging"""
        tags = [{'Key': self.tagging_config.owner_tag_name, 'Value': username}]
        
        # Add creation time tag if enabled and provided
        if self.tagging_config.include_creation_time and creation_time:
            tags.append({'Key': self.tagging_config.creation_time_tag_name, 'Value': creation_time})
        
        # Add any additional static tags
        for key, value in self.tagging_config.additional_tags.items():
            tags.append({'Key': key, 'Value': value})
        
        return tags
    
    def _construct_arn(self, resource_type: ResourceType, resource_id: str) -> str:
        """Construct ARN for resources that need it"""
        account_id = self.sts.get_caller_identity()['Account']
        
        if resource_type == ResourceType.RDS_INSTANCE:
            return f"arn:aws:rds:{self.region}:{account_id}:db:{resource_id}"
        elif resource_type == ResourceType.RDS_CLUSTER:
            return f"arn:aws:rds:{self.region}:{account_id}:cluster:{resource_id}"
        elif resource_type == ResourceType.EKS_CLUSTER:
            return f"arn:aws:eks:{self.region}:{account_id}:cluster/{resource_id}"
        elif resource_type == ResourceType.EKS_NODEGROUP:
            # For EKS nodegroups, we need to find the cluster name
            # This is a simplified approach - in practice, you might need the cluster name
            # from the CloudTrail event or implement a lookup mechanism
            try:
                clusters = self.eks.list_clusters()['clusters']
                for cluster_name in clusters:
                    try:
                        nodegroups = self.eks.list_nodegroups(clusterName=cluster_name)['nodegroups']
                        if resource_id in nodegroups:
                            return f"arn:aws:eks:{self.region}:{account_id}:nodegroup/{cluster_name}/{resource_id}"
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Could not construct ARN for EKS nodegroup {resource_id}: {e}")
        return resource_id  # Return as-is if no ARN construction is needed or failed
    
    def tag_resource(self, resource_type: ResourceType, resource_id: str, username: str, creation_time: str = None) -> bool:
        """Tag a resource with owner information and creation time using strategy pattern"""
        try:
            # Prepare tags
            tags = self._prepare_tags(username, creation_time)
            
            # For certain resource types, we need to construct the full ARN
            if resource_type in [ResourceType.RDS_INSTANCE, ResourceType.RDS_CLUSTER,
                                ResourceType.EKS_CLUSTER, ResourceType.EKS_NODEGROUP]:
                resource_id = self._construct_arn(resource_type, resource_id)
                # If ARN construction failed for EKS nodegroup, return False
                if not resource_id:
                    return False
            
            # Create appropriate tagging strategy
            strategy = TaggingStrategyFactory.create_strategy(
                resource_type, self.region, self.sts, self.tagging_config
            )
            
            # Tag the resource using the strategy
            success = strategy.tag_resource(resource_id, tags)
            
            if success:
                # Build tag info string for logging
                tag_info = f"{self.tagging_config.owner_tag_name}:{username}"
                if self.tagging_config.include_creation_time and creation_time:
                    tag_info += f", {self.tagging_config.creation_time_tag_name}:{creation_time}"
                for key, value in self.tagging_config.additional_tags.items():
                    tag_info += f", {key}:{value}"
                    
                logger.info(f"Successfully tagged {resource_type.value}:{resource_id} with {tag_info}")
            else:
                logger.error(f"Failed to tag {resource_type.value}:{resource_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error tagging {resource_type.value}:{resource_id}: {e}")
            return False

    def process_events(self, events: List[Dict]) -> Tuple[TaggingStats, List[ResourceInfo]]:
        """Process events and tag resources, returning stats and detailed resource info"""
        stats = TaggingStats()
        resources_info = []
        
        for event in events:
            stats.processed += 1
            event_name = event.get('EventName', '')
            username = event.get('Username', 'Unknown')
            
            # Extract creation time from event
            event_time = event.get('EventTime')
            creation_time_str = None
            parsed_event_time = None
            
            if event_time:
                # Format the datetime for AWS tags (ISO format)
                if isinstance(event_time, datetime):
                    creation_time_str = event_time.strftime(self.tagging_config.creation_time_format)
                    parsed_event_time = event_time
                else:
                    # If it's a string, try to parse and reformat
                    try:
                        parsed_event_time = datetime.fromisoformat(str(event_time).replace('Z', '+00:00'))
                        creation_time_str = parsed_event_time.strftime(self.tagging_config.creation_time_format)
                    except (ValueError, AttributeError):
                        creation_time_str = str(event_time)
            
            logger.info(f"Processing event: {event_name} by {username} at {creation_time_str}")
            
            # Extract resources using the creation event manager
            resources = self.creation_event_manager.extract_resources_from_event(event)
            
            # Tag each resource
            for resource_type, resource_id in resources:
                success = self.tag_resource(resource_type, resource_id, username, creation_time_str)
                
                # Create ResourceInfo object
                resource_info = ResourceInfo(
                    resource_type=resource_type.value,
                    resource_id=resource_id,
                    event_name=event_name,
                    username=username,
                    event_time=parsed_event_time,
                    tagged=success,
                    error_message=None if success else f"Failed to tag {resource_type.value}:{resource_id}"
                )
                resources_info.append(resource_info)
                
                if success:
                    stats.tagged += 1
                else:
                    stats.errors += 1
                
        return stats, resources_info

    def get_event_summary(self, hours: int = 24) -> CloudTrailEventSummary:
        """Get summary of CloudTrail events without processing them"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        events = self.get_cloudtrail_events(hours)
        creation_events = self.filter_creation_events(events)
        
        return CloudTrailEventSummary(
            total_events=len(events),
            creation_events=len(creation_events),
            time_range_hours=hours,
            region=self.region,
            start_time=start_time,
            end_time=end_time
        )

    def run(self, hours: int = 24) -> EventProcessingResult:
        """Main execution method"""
        start_time = datetime.utcnow()
        logger.info("Starting CloudTrail Resource Tagging Process")
        
        # Get CloudTrail events
        events = self.get_cloudtrail_events(hours)
        if not events:
            logger.warning("No events found")
            end_time = datetime.utcnow()
            return EventProcessingResult(
                stats=TaggingStats(),
                resources=[],
                start_time=start_time,
                end_time=end_time,
                region=self.region
            )
        
        # Filter to creation events only
        creation_events = self.filter_creation_events(events)
        if not creation_events:
            logger.warning("No creation events found")
            end_time = datetime.utcnow()
            return EventProcessingResult(
                stats=TaggingStats(),
                resources=[],
                start_time=start_time,
                end_time=end_time,
                region=self.region
            )
        
        # Process events and tag resources
        stats, resources_info = self.process_events(creation_events)
        end_time = datetime.utcnow()
        
        result = EventProcessingResult(
            stats=stats,
            resources=resources_info,  # Could be populated with detailed resource info if needed
            start_time=start_time,
            end_time=end_time,
            region=self.region
        )
        
        logger.info(f"Process completed. Stats: {stats}")
        return result
