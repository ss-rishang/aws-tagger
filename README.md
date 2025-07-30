# AWS CloudTrail Resource Tagger

An automated tool for tagging AWS resources with owner information based on CloudTrail events. This tool monitors CloudTrail events and automatically applies ownership tags to newly created resources.

## Features

- **Multi-Service Support**: Supports EC2, S3, RDS, Lambda, ELB, and EKS resources
- **Flexible Architecture**: Builder pattern with extensible event extractors
- **Real-time Processing**: Processes CloudTrail events from the past 24 hours (configurable)
- **Custom Extractors**: Support for both path-based and function-based resource extraction
- **EKS Support**: Full support for EKS clusters and node groups
- **Dual Tagging**: Automatically applies both owner and creation-time tags
- **Detailed Tracking**: Returns comprehensive information about each processed resource

## Supported AWS Services

- **EC2**: Instances, Volumes, Security Groups, VPCs, Subnets, Snapshots, Images, Elastic IPs
- **S3**: Buckets
- **RDS**: DB Instances, DB Clusters
- **Lambda**: Functions
- **ELB**: Load Balancers, Target Groups
- **EKS**: Clusters, Node Groups

## Project Structure

```
aws-tagger/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── utils.py             # Shared utilities and logging
│   ├── data.py              # Dataclasses for return types
│   ├── trail.py             # CloudTrail event processing classes
│   ├── tagger.py            # Main resource tagging functionality
│   └── main.py              # Example usage and demonstrations
├── main.py                  # Entry point script
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd aws-tagger
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure AWS credentials:
```bash
aws configure
# or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

## Usage

### Basic Usage

```python
from src import CloudTrailResourceTagger

# Simple usage with default configuration
tagger = CloudTrailResourceTagger(region_name='us-east-1')
result = tagger.run(hours=24)
print(f"Tagged {result.stats.tagged} resources with {result.stats.success_rate:.1f}% success rate")
print(f"Processing took {result.duration_seconds:.2f} seconds")
```

### Getting Event Summary

```python
from src import CloudTrailResourceTagger

tagger = CloudTrailResourceTagger(region_name='us-east-1')
summary = tagger.get_event_summary(hours=24)
print(f"Found {summary.creation_events} creation events out of {summary.total_events} total events")
```

### Using Builder Pattern

```python
from src import CloudTrailResourceTaggerBuilder, ResourceType

# Advanced configuration using builder pattern
tagger = (CloudTrailResourceTaggerBuilder()
          .set_region('us-west-2')
          .add_path_extractor(
              event_name='CreateCustomResource',
              resource_type=ResourceType.EC2_INSTANCE,
              section='responseElements',
              simple_path=['customResourceId']
          )
          .build())

result = tagger.run(hours=12)
print(f"Processing result: {result}")
```

### Working with Dataclasses

```python
from src import CloudTrailResourceTagger, TaggingStats, EventProcessingResult

tagger = CloudTrailResourceTagger()
result: EventProcessingResult = tagger.run(hours=6)

# Access structured data
stats: TaggingStats = result.stats
print(f"Success rate: {stats.success_rate:.1f}%")
print(f"Error rate: {stats.error_rate:.1f}%")
print(f"Duration: {result.duration_seconds:.2f}s")
print(f"Region: {result.region}")
```

### Configurable Tagging

```python
from src import CloudTrailResourceTaggerBuilder, TaggingConfig

# Method 1: Using TaggingConfig dataclass
custom_config = TaggingConfig(
    owner_tag_name="CreatedBy",
    creation_time_tag_name="ResourceCreatedAt", 
    creation_time_format="%Y-%m-%d %H:%M",
    include_creation_time=True,
    additional_tags={
        "Environment": "Production",
        "ManagedBy": "AutoTagger"
    }
)

tagger = (CloudTrailResourceTaggerBuilder()
          .set_region('us-east-1')
          .with_tagging_config(custom_config)
          .build())

# Method 2: Using fluent interface
tagger = (CloudTrailResourceTaggerBuilder()
          .set_region('us-east-1')
          .set_owner_tag_name("ResourceOwner")
          .set_creation_time_tag_name("DateCreated")
          .set_creation_time_format("%Y/%m/%d %H:%M:%S")
          .add_additional_tag("Team", "DevOps")
          .add_additional_tag("Project", "CloudTagging")
          .enable_creation_time_tagging(True)
          .build())

result = tagger.run(hours=24)
```

## Data Types

The library uses dataclasses for type-safe return values and configuration:

### TaggingStats
Statistics from a tagging operation:
```python
@dataclass
class TaggingStats:
    processed: int = 0    # Number of events processed
    tagged: int = 0       # Number of resources successfully tagged
    errors: int = 0       # Number of errors encountered
    
    # Computed properties
    success_rate: float   # Success rate as percentage
    error_rate: float     # Error rate as percentage
```

### EventProcessingResult
Complete result from processing CloudTrail events:
```python
@dataclass
class EventProcessingResult:
    stats: TaggingStats           # Processing statistics
    resources: List[ResourceInfo] # List of processed resources
    start_time: datetime          # Processing start time
    end_time: datetime           # Processing end time
    region: str                  # AWS region
    
    # Computed properties
    duration_seconds: float      # Processing duration
```

### CloudTrailEventSummary
Summary of retrieved CloudTrail events:
```python
@dataclass
class CloudTrailEventSummary:
    total_events: int      # Total events retrieved
    creation_events: int   # Creation events found
    time_range_hours: int  # Time range queried
    region: str           # AWS region
    start_time: datetime  # Query start time
    end_time: datetime    # Query end time
```

### ResourceInfo
Information about a discovered resource:
```python
@dataclass
class ResourceInfo:
    resource_type: str              # Type of AWS resource
    resource_id: str               # Resource identifier
    event_name: str                # CloudTrail event name
    username: str                  # User who created the resource
    event_time: Optional[datetime] # When the event occurred
    tagged: bool = False           # Whether tagging was successful
    error_message: Optional[str]   # Error message if tagging failed
```

## Custom Event Manager

```python
from src import CreationEventManager, ResourceType

# Create custom event manager
custom_manager = CreationEventManager()

# Add custom extractors
custom_manager.add_path_based_extractor(
    event_name='CreateNewServiceResource',
    resource_type=ResourceType.LAMBDA_FUNCTION,
    section='requestParameters',
    simple_path=['newResourceName']
)

# Use with tagger
tagger = CloudTrailResourceTagger(
    region_name='eu-west-1',
    creation_event_manager=custom_manager
)
```

### EKS Support Example

```python
from src import CreationEventManager, ResourceType

# EKS support is included by default
# CreateCluster and CreateNodegroup events are automatically supported

eks_manager = CreationEventManager()

# Add custom EKS-related extractors if needed
eks_manager.add_path_based_extractor(
    event_name='CreateEKSAddon',
    resource_type=ResourceType.EKS_CLUSTER,
    section='responseElements',
    simple_path=['addon', 'addonName']
)
```

## Running the Examples

Run the main script to see all usage examples:

```bash
python main.py
```

Or run the src main directly:

```bash
python src/main.py
```

## Configuration

### Event Extractors

The tool supports two types of event extractors:

1. **Path-based Extractors**: Extract resource IDs using JSON path specifications
2. **Function-based Extractors**: Use custom functions for complex extraction logic

### Supported CloudTrail Events

- `RunInstances` → EC2 Instances
- `CreateVolume` → EC2 Volumes
- `CreateSecurityGroup` → EC2 Security Groups
- `CreateVpc` → EC2 VPCs
- `CreateSubnet` → EC2 Subnets
- `CreateSnapshot` → EC2 Snapshots
- `CreateImage` → EC2 Images
- `AllocateAddress` → EC2 Elastic IPs
- `CreateBucket` → S3 Buckets
- `CreateDBInstance` → RDS Instances
- `CreateDBCluster` → RDS Clusters
- `CreateFunction` → Lambda Functions
- `CreateLoadBalancer` → ELB Load Balancers
- `CreateTargetGroup` → ELB Target Groups
- `CreateCluster` → EKS Clusters
- `CreateNodegroup` → EKS Node Groups

## Architecture

### Key Classes

- **`ResourceType`**: Enum defining supported AWS resource types
- **`EventExtractor`**: Universal extractor for CloudTrail events
- **`EventExtractorFactory`**: Factory for creating event extractors
- **`CreationEventManager`**: Manages creation event extractors
- **`CloudTrailResourceTaggerBuilder`**: Builder for tagger configuration
- **`CloudTrailResourceTagger`**: Main class for resource tagging
- **`TaggingConfig`**: Configuration for customizable tagging behavior

### Design Patterns

- **Builder Pattern**: For flexible tagger configuration
- **Factory Pattern**: For creating event extractors
- **Strategy Pattern**: For different extraction methods
- **Configuration Pattern**: For customizable tagging behavior

## Requirements

- Python 3.7+
- boto3 >= 1.26.0
- Valid AWS credentials with appropriate permissions

### Required AWS Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudtrail:LookupEvents",
                "ec2:CreateTags",
                "s3:PutBucketTagging",
                "rds:AddTagsToResource",
                "lambda:TagResource",
                "elasticloadbalancing:AddTags",
                "eks:TagResource",
                "eks:ListClusters",
                "eks:ListNodegroups",
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```