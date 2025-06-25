#!/usr/bin/env python3
"""
CloudWatch Metrics Collector for EKS Nodes

This module collects CloudWatch metrics for EC2 instances in an EKS cluster.
"""

import boto3
import logging
from datetime import datetime, timedelta
import config as cfg

logger = logging.getLogger('metrics_collector')


class CloudWatchMetricsCollector:
    def __init__(self, region):
        """Initialize the CloudWatch metrics collector"""
        self.region = region
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        logger.info(f"CloudWatch Metrics Collector initialized for region {region}")

    def get_instance_metrics(self, instance_id, period_minutes=5):
        """
        Get CloudWatch metrics for an EC2 instance
        
        Args:
            instance_id (str): EC2 instance ID
            period_minutes (int): Period in minutes to look back for metrics
            
        Returns:
            dict: Dictionary of metrics with their values
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=period_minutes)
        
        metrics = {}
        
        try:
            # Get CPU utilization
            metrics['CPUUtilization'] = self._get_metric_statistic(
                namespace='AWS/EC2',
                metric_name='CPUUtilization',
                dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                start_time=start_time,
                end_time=end_time
            )
            
            # Get memory utilization (requires CloudWatch agent)
            metrics['MemoryUtilization'] = self._get_metric_statistic(
                namespace='CWAgent',
                metric_name='mem_used_percent',
                dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                start_time=start_time,
                end_time=end_time
            )
            
            # Get disk utilization (requires CloudWatch agent)
            metrics['DiskUtilization'] = self._get_metric_statistic(
                namespace='CWAgent',
                metric_name='disk_used_percent',
                dimensions=[
                    {'Name': 'InstanceId', 'Value': instance_id},
                    {'Name': 'fstype', 'Value': 'xfs'},
                    {'Name': 'path', 'Value': '/'}
                ],
                start_time=start_time,
                end_time=end_time
            )
            
            # Get network in/out
            metrics['NetworkIn'] = self._get_metric_statistic(
                namespace='AWS/EC2',
                metric_name='NetworkIn',
                dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                start_time=start_time,
                end_time=end_time,
                statistic='Sum'
            )
            
            metrics['NetworkOut'] = self._get_metric_statistic(
                namespace='AWS/EC2',
                metric_name='NetworkOut',
                dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                start_time=start_time,
                end_time=end_time,
                statistic='Sum'
            )
            
            # Filter out None values
            metrics = {k: v for k, v in metrics.items() if v is not None}
            
            logger.info(f"Collected {len(metrics)} metrics for instance {instance_id}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics for instance {instance_id}: {str(e)}")
            return {}

    def _get_metric_statistic(self, namespace, metric_name, dimensions, start_time, end_time, statistic='Average', period=300):
        """
        Get a specific CloudWatch metric statistic
        
        Args:
            namespace (str): CloudWatch namespace
            metric_name (str): Metric name
            dimensions (list): List of dimension dictionaries
            start_time (datetime): Start time for metrics
            end_time (datetime): End time for metrics
            statistic (str): Statistic type (Average, Maximum, Minimum, Sum, SampleCount)
            period (int): Period in seconds
            
        Returns:
            float: Metric value or None if not available
        """
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistic]
            )
            
            datapoints = response.get('Datapoints', [])
            if datapoints:
                # Sort by timestamp and get the most recent
                datapoints.sort(key=lambda x: x['Timestamp'], reverse=True)
                return datapoints[0][statistic]
            else:
                logger.warning(f"No datapoints found for metric {metric_name} in {namespace}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting metric {metric_name} from {namespace}: {str(e)}")
            return None

    def get_cluster_metrics(self, cluster_name):
        """
        Get EKS cluster level metrics
        
        Args:
            cluster_name (str): EKS cluster name
            
        Returns:
            dict: Dictionary of cluster metrics
        """
        # This is a placeholder for cluster-level metrics
        # EKS doesn't provide many built-in CloudWatch metrics at the cluster level
        # You would typically aggregate node-level metrics or use Container Insights
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=30)
        
        metrics = {}
        
        try:
            # If using Container Insights, you can get pod and node metrics
            metrics['pod_count'] = self._get_metric_statistic(
                namespace='ContainerInsights',
                metric_name='pod_number',
                dimensions=[{'Name': 'ClusterName', 'Value': cluster_name}],
                start_time=start_time,
                end_time=end_time
            )
            
            metrics['node_count'] = self._get_metric_statistic(
                namespace='ContainerInsights',
                metric_name='node_number',
                dimensions=[{'Name': 'ClusterName', 'Value': cluster_name}],
                start_time=start_time,
                end_time=end_time
            )
            
            # Filter out None values
            metrics = {k: v for k, v in metrics.items() if v is not None}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get cluster metrics for {cluster_name}: {str(e)}")
            return {}