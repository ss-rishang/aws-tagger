import json
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum
from .utils import logger


class ResourceType(Enum):
    """Enum for supported resource types"""
    EC2_INSTANCE = "ec2:instance"
    EC2_VOLUME = "ec2:volume"
    EC2_SECURITY_GROUP = "ec2:security-group"
    EC2_VPC = "ec2:vpc"
    EC2_SUBNET = "ec2:subnet"
    EC2_SNAPSHOT = "ec2:snapshot"
    EC2_IMAGE = "ec2:image"
    EC2_ELASTIC_IP = "ec2:elastic-ip"
    S3_BUCKET = "s3:bucket"
    RDS_INSTANCE = "rds:db"
    RDS_CLUSTER = "rds:cluster"
    LAMBDA_FUNCTION = "lambda:function"
    ELB_LOAD_BALANCER = "elbv2:loadbalancer"
    ELB_TARGET_GROUP = "elbv2:targetgroup"
    EKS_CLUSTER = "eks:cluster"
    EKS_NODEGROUP = "eks:nodegroup"


class EventExtractor:
    """Universal event extractor that handles all resource types"""
    
    def __init__(self, resource_type: ResourceType, extraction_config: Dict):
        """
        Initialize extractor with resource type and extraction configuration
        
        Args:
            resource_type: The type of resource this extractor handles
            extraction_config: Configuration dict with extraction paths and logic
        """
        self.resource_type = resource_type
        self.config = extraction_config
    
    def extract_resources(self, event: Dict) -> List[Tuple[ResourceType, str]]:
        """Extract resources from CloudTrail event using configuration"""
        resources = []
        
        try:
            cloud_trail_event = self._get_cloud_trail_event(event)
            
            # Use extraction function if provided
            if 'extraction_function' in self.config:
                extraction_func = self.config['extraction_function']
                resource_ids = extraction_func(cloud_trail_event)
            else:
                # Use path-based extraction
                resource_ids = self._extract_by_path(cloud_trail_event)
            
            # Convert to resource tuples
            for resource_id in resource_ids:
                if resource_id:
                    resources.append((self.resource_type, resource_id))
                    
        except Exception as e:
            logger.error(f"Error extracting {self.resource_type.value}: {e}")
        
        return resources
    
    def _get_cloud_trail_event(self, event: Dict) -> Dict:
        """Helper to parse CloudTrail event JSON"""
        try:
            return json.loads(event.get('CloudTrailEvent', '{}'))
        except Exception as e:
            logger.error(f"Error parsing CloudTrail event: {e}")
            return {}
    
    def _extract_by_path(self, cloud_trail_event: Dict) -> List[str]:
        """Extract resource IDs using configured paths"""
        resource_ids = []
        
        # Get the section to look in (responseElements, requestParameters, etc.)
        section_name = self.config.get('section', 'responseElements')
        section = cloud_trail_event.get(section_name, {})
        
        # Handle different extraction patterns
        if 'simple_path' in self.config:
            # Simple path like ['volumeId'] or ['vpc', 'vpcId']
            value = self._get_nested_value(section, self.config['simple_path'])
            if value:
                resource_ids.append(value)
                
        elif 'array_path' in self.config:
            # Array path like ['instancesSet', 'items'] with item_key 'instanceId'
            array = self._get_nested_value(section, self.config['array_path'])
            if isinstance(array, list):
                item_key = self.config.get('item_key', 'id')
                for item in array:
                    if isinstance(item, dict) and item_key in item:
                        resource_ids.append(item[item_key])
        
        return resource_ids
    
    def _get_nested_value(self, data: Dict, path: List[str]):
        """Get nested value from dict using path list"""
        current = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current


class EventExtractorFactory:
    """Factory for creating event extractors with predefined configurations"""
    
    def __init__(self):
        self._configurations = self._get_default_configurations()
    
    def _get_default_configurations(self) -> Dict[str, Dict]:
        """Get default extraction configurations for supported events"""
        return {
            # EC2 Events
            'RunInstances': {
                'resource_type': ResourceType.EC2_INSTANCE,
                'section': 'responseElements',
                'array_path': ['instancesSet', 'items'],
                'item_key': 'instanceId'
            },
            'CreateVolume': {
                'resource_type': ResourceType.EC2_VOLUME,
                'section': 'responseElements',
                'simple_path': ['volumeId']
            },
            'CreateSecurityGroup': {
                'resource_type': ResourceType.EC2_SECURITY_GROUP,
                'section': 'responseElements',
                'simple_path': ['groupId']
            },
            'CreateVpc': {
                'resource_type': ResourceType.EC2_VPC,
                'section': 'responseElements',
                'simple_path': ['vpc', 'vpcId']
            },
            'CreateSubnet': {
                'resource_type': ResourceType.EC2_SUBNET,
                'section': 'responseElements',
                'simple_path': ['subnet', 'subnetId']
            },
            'CreateSnapshot': {
                'resource_type': ResourceType.EC2_SNAPSHOT,
                'section': 'responseElements',
                'simple_path': ['snapshotId']
            },
            'CreateImage': {
                'resource_type': ResourceType.EC2_IMAGE,
                'section': 'responseElements',
                'simple_path': ['imageId']
            },
            'AllocateAddress': {
                'resource_type': ResourceType.EC2_ELASTIC_IP,
                'section': 'responseElements',
                'simple_path': ['allocationId']
            },
            
            # S3 Events
            'CreateBucket': {
                'resource_type': ResourceType.S3_BUCKET,
                'section': 'requestParameters',
                'simple_path': ['bucketName']
            },
            
            # RDS Events
            'CreateDBInstance': {
                'resource_type': ResourceType.RDS_INSTANCE,
                'section': 'requestParameters',
                'simple_path': ['dBInstanceIdentifier']
            },
            'CreateDBCluster': {
                'resource_type': ResourceType.RDS_CLUSTER,
                'section': 'requestParameters',
                'simple_path': ['dBClusterIdentifier']
            },
            
            # Lambda Events
            'CreateFunction': {
                'resource_type': ResourceType.LAMBDA_FUNCTION,
                'section': 'requestParameters',
                'simple_path': ['functionName']
            },
            
            # ELB Events
            'CreateLoadBalancer': {
                'resource_type': ResourceType.ELB_LOAD_BALANCER,
                'section': 'responseElements',
                'array_path': ['loadBalancers'],
                'item_key': 'loadBalancerArn'
            },
            'CreateTargetGroup': {
                'resource_type': ResourceType.ELB_TARGET_GROUP,
                'section': 'responseElements',
                'array_path': ['targetGroups'],
                'item_key': 'targetGroupArn'
            },
            
            # EKS Events
            'CreateCluster': {
                'resource_type': ResourceType.EKS_CLUSTER,
                'section': 'responseElements',
                'simple_path': ['cluster', 'name']
            },
            'CreateNodegroup': {
                'resource_type': ResourceType.EKS_NODEGROUP,
                'section': 'responseElements',
                'extraction_function': lambda event: [
                    event.get('cluster', {}).get('name'),
                    event.get('nodegroup', {}).get('nodegroupName')
                ]
            }
        }
    
    def create_extractor(self, event_name: str) -> Optional[EventExtractor]:
        """Create an extractor for the given event name"""
        config = self._configurations.get(event_name)
        if not config:
            return None
        
        resource_type = config['resource_type']
        return EventExtractor(resource_type, config)
    
    def get_supported_events(self) -> List[str]:
        """Get list of supported event names"""
        return list(self._configurations.keys())
    
    def register_extractor_config(self, event_name: str, config: Dict) -> None:
        """Register a new extractor configuration"""
        self._configurations[event_name] = config
    
    def register_custom_extractor(self, event_name: str, resource_type: ResourceType, 
                                extraction_function: Callable[[Dict], List[str]]) -> None:
        """Register a custom extractor with a function"""
        config = {
            'resource_type': resource_type,
            'extraction_function': extraction_function
        }
        self._configurations[event_name] = config


class CreationEventManager:
    """Manager for handling creation events with extractors"""
    
    def __init__(self):
        self.factory = EventExtractorFactory()
        self._supported_events = set(self.factory.get_supported_events())
    
    def is_creation_event(self, event_name: str) -> bool:
        """Check if an event is a supported creation event"""
        return event_name in self._supported_events
    
    def extract_resources_from_event(self, event: Dict) -> List[Tuple[ResourceType, str]]:
        """Extract resources from a creation event"""
        event_name = event.get('EventName', '')
        
        if not self.is_creation_event(event_name):
            logger.warning(f"Unsupported creation event: {event_name}")
            return []
        
        extractor = self.factory.create_extractor(event_name)
        if extractor:
            return extractor.extract_resources(event)
        
        logger.error(f"Failed to create extractor for event: {event_name}")
        return []
    
    def get_supported_events(self) -> List[str]:
        """Get list of supported creation events"""
        return list(self._supported_events)
    
    def add_path_based_extractor(self, event_name: str, resource_type: ResourceType, 
                                section: str, simple_path: List[str] = None, 
                                array_path: List[str] = None, item_key: str = None) -> None:
        """Add a path-based extractor configuration"""
        config = {
            'resource_type': resource_type,
            'section': section
        }
        
        if simple_path:
            config['simple_path'] = simple_path
        elif array_path:
            config['array_path'] = array_path
            config['item_key'] = item_key or 'id'
        
        self.factory.register_extractor_config(event_name, config)
        self._supported_events.add(event_name)
    
    def add_function_based_extractor(self, event_name: str, resource_type: ResourceType,
                                   extraction_function: Callable[[Dict], List[str]]) -> None:
        """Add a function-based extractor"""
        self.factory.register_custom_extractor(event_name, resource_type, extraction_function)
        self._supported_events.add(event_name)