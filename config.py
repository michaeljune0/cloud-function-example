"""
Configuration settings for EKS monitoring
"""

# AWS Configuration
AWS_REGION = "us-west-2"  # Change to your AWS region

# EKS Configuration
EKS_CLUSTER_NAME = "my-eks-cluster"  # Change to your EKS cluster name

# Monitoring Configuration
METRICS_INTERVAL = 60  # Seconds between metrics collection
ALERT_THRESHOLD_CPU = 80  # CPU utilization percentage threshold for alerts
ALERT_THRESHOLD_MEMORY = 80  # Memory utilization percentage threshold for alerts
ALERT_THRESHOLD_DISK = 85  # Disk utilization percentage threshold for alerts

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FILE = "eks_monitoring.log"

# Optional: SNS Topic for alerts
SNS_TOPIC_ARN = ""  # Set this if you want to send alerts to an SNS topic