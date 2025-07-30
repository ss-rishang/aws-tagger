import boto3
from typing import Dict, List, Tuple
from abc import ABC, abstractmethod
from .trail import ResourceType
from .data import TaggingConfig
from .utils import logger


class TaggingStrategy(ABC):
    """Abstract base class for tagging strategies"""
    
    def __init__(self, region: str, sts_client: boto3.client, tagging_config: TaggingConfig):
        self.region = region
        self.sts_client = sts_client
        self.tagging_config = tagging_config
    
    @abstractmethod
    def tag_resource(self, resource_id: str, tags: List[Dict[str, str]]) -> bool:
        """Tag a resource with the provided tags"""
        pass
    
    def _format_tags_for_aws(self, tags: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format tags for AWS APIs that expect Key/Value pairs"""
        return [{'Key': tag['Key'], 'Value': tag['Value']} for tag in tags]
    
    def _format_tags_for_key_value(self, tags: List[Dict[str, str]]) -> Dict[str, str]:
        """Format tags for AWS APIs that expect key-value dictionaries"""
        return {tag['Key']: tag['Value'] for tag in tags}


class EC2TaggingStrategy(TaggingStrategy):
    """Tagging strategy for EC2 resources"""
    
    def __init__(self, region: str, sts_client: boto3.client, tagging_config: TaggingConfig):
        super().__init__(region, sts_client, tagging_config)
        self.ec2_client = boto3.client('ec2', region_name=region)
    
    def tag_resource(self, resource_id: str, tags: List[Dict[str, str]]) -> bool:
        """Tag an EC2 resource"""
        try:
            self.ec2_client.create_tags(Resources=[resource_id], Tags=self._format_tags_for_aws(tags))
            return True
        except Exception as e:
            logger.error(f"Error tagging EC2 resource {resource_id}: {e}")
            return False


class S3TaggingStrategy(TaggingStrategy):
    """Tagging strategy for S3 buckets"""
    
    def __init__(self, region: str, sts_client: boto3.client, tagging_config: TaggingConfig):
        super().__init__(region, sts_client, tagging_config)
        self.s3_client = boto3.client('s3')
    
    def tag_resource(self, resource_id: str, tags: List[Dict[str, str]]) -> bool:
        """Tag an S3 bucket"""
        try:
            tag_set = {'TagSet': self._format_tags_for_aws(tags)}
            self.s3_client.put_bucket_tagging(Bucket=resource_id, Tagging=tag_set)
            return True
        except Exception as e:
            logger.error(f"Error tagging S3 bucket {resource_id}: {e}")
            return False


class RDSTaggingStrategy(TaggingStrategy):
    """Tagging strategy for RDS resources"""
    
    def __init__(self, region: str, sts_client: boto3.client, tagging_config: TaggingConfig):
        super().__init__(region, sts_client, tagging_config)
        self.rds_client = boto3.client('rds', region_name=region)
    
    def tag_resource(self, resource_id: str, tags: List[Dict[str, str]]) -> bool:
        """Tag an RDS resource (DB instance or cluster)"""
        # Resource type is determined by the caller based on ResourceType
        # This method assumes the resource_id is already the full ARN
        try:
            rds_tags = self._format_tags_for_aws(tags)
            self.rds_client.add_tags_to_resource(ResourceName=resource_id, Tags=rds_tags)
            return True
        except Exception as e:
            logger.error(f"Error tagging RDS resource {resource_id}: {e}")
            return False


class LambdaTaggingStrategy(TaggingStrategy):
    """Tagging strategy for Lambda functions"""
    
    def __init__(self, region: str, sts_client: boto3.client, tagging_config: TaggingConfig):
        super().__init__(region, sts_client, tagging_config)
        self.lambda_client = boto3.client('lambda', region_name=region)
    
    def tag_resource(self, resource_id: str, tags: List[Dict[str, str]]) -> bool:
        """Tag a Lambda function"""
        try:
            # Construct the full ARN for Lambda function
            account_id = self.sts_client.get_caller_identity()['Account']
            function_arn = f"arn:aws:lambda:{self.region}:{account_id}:function:{resource_id}"
            
            lambda_tags = self._format_tags_for_key_value(tags)
            self.lambda_client.tag_resource(Resource=function_arn, Tags=lambda_tags)
            return True
        except Exception as e:
            logger.error(f"Error tagging Lambda function {resource_id}: {e}")
            return False


class ELBTaggingStrategy(TaggingStrategy):
    """Tagging strategy for ELB resources"""
    
    def __init__(self, region: str, sts_client: boto3.client, tagging_config: TaggingConfig):
        super().__init__(region, sts_client, tagging_config)
        self.elbv2_client = boto3.client('elbv2', region_name=region)
    
    def tag_resource(self, resource_id: str, tags: List[Dict[str, str]]) -> bool:
        """Tag an ELB resource (load balancer or target group)"""
        # resource_id is expected to be the full ARN
        try:
            elbv2_tags = self._format_tags_for_aws(tags)
            self.elbv2_client.add_tags(ResourceArns=[resource_id], Tags=elbv2_tags)
            return True
        except Exception as e:
            logger.error(f"Error tagging ELB resource {resource_id}: {e}")
            return False


class EKSTaggingStrategy(TaggingStrategy):
    """Tagging strategy for EKS resources"""
    
    def __init__(self, region: str, sts_client: boto3.client, tagging_config: TaggingConfig):
        super().__init__(region, sts_client, tagging_config)
        self.eks_client = boto3.client('eks', region_name=region)
    
    def tag_resource(self, resource_id: str, tags: List[Dict[str, str]]) -> bool:
        """Tag an EKS resource (cluster or nodegroup)"""
        try:
            eks_tags = self._format_tags_for_key_value(tags)
            self.eks_client.tag_resource(resourceArn=resource_id, tags=eks_tags)
            return True
        except Exception as e:
            logger.error(f"Error tagging EKS resource {resource_id}: {e}")
            return False


class TaggingStrategyFactory:
    """Factory for creating tagging strategies"""
    
    @staticmethod
    def create_strategy(resource_type: ResourceType, region: str, sts_client: boto3.client, 
                       tagging_config: TaggingConfig) -> TaggingStrategy:
        """Create a tagging strategy for the specified resource type"""
        if resource_type in [ResourceType.EC2_INSTANCE, ResourceType.EC2_VOLUME, 
                            ResourceType.EC2_SECURITY_GROUP, ResourceType.EC2_VPC,
                            ResourceType.EC2_SUBNET, ResourceType.EC2_SNAPSHOT, 
                            ResourceType.EC2_IMAGE, ResourceType.EC2_ELASTIC_IP]:
            return EC2TaggingStrategy(region, sts_client, tagging_config)
        
        elif resource_type == ResourceType.S3_BUCKET:
            return S3TaggingStrategy(region, sts_client, tagging_config)
        
        elif resource_type in [ResourceType.RDS_INSTANCE, ResourceType.RDS_CLUSTER]:
            return RDSTaggingStrategy(region, sts_client, tagging_config)
        
        elif resource_type == ResourceType.LAMBDA_FUNCTION:
            return LambdaTaggingStrategy(region, sts_client, tagging_config)
        
        elif resource_type in [ResourceType.ELB_LOAD_BALANCER, ResourceType.ELB_TARGET_GROUP]:
            return ELBTaggingStrategy(region, sts_client, tagging_config)
        
        elif resource_type in [ResourceType.EKS_CLUSTER, ResourceType.EKS_NODEGROUP]:
            return EKSTaggingStrategy(region, sts_client, tagging_config)
        
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")