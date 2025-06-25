#!/usr/bin/env python3
"""
EKS Node Monitoring Tool

This script monitors EKS nodes (EC2 instances) and collects metrics about their health and performance.
"""

import boto3
import logging
import time
import schedule
from datetime import datetime
from kubernetes import client, config
from metrics_collector import CloudWatchMetricsCollector
import config as cfg

# Configure logging
logging.basicConfig(
    level=getattr(logging, cfg.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=cfg.LOG_FILE,
    filemode='a'
)
logger = logging.getLogger('eks_monitor')

# Add console handler
console = logging.StreamHandler()
console.setLevel(getattr(logging, cfg.LOG_LEVEL))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logger.addHandler(console)


class EKSMonitor:
    def __init__(self):
        """Initialize the EKS Monitor with AWS and Kubernetes clients"""
        self.region = cfg.AWS_REGION
        self.cluster_name = cfg.EKS_CLUSTER_NAME
        
        # Initialize AWS clients
        self.eks_client = boto3.client('eks', region_name=self.region)
        self.ec2_client = boto3.client('ec2', region_name=self.region)
        
        # Initialize metrics collector
        self.metrics_collector = CloudWatchMetricsCollector(self.region)
        
        # Initialize Kubernetes client
        self._init_kubernetes_client()
        
        logger.info(f"EKS Monitor initialized for cluster: {self.cluster_name}")

    def _init_kubernetes_client(self):
        """Initialize Kubernetes client using AWS EKS credentials"""
        try:
            # Get cluster info
            cluster_info = self.eks_client.describe_cluster(name=self.cluster_name)
            
            # Update kubeconfig
            cmd = f"aws eks update-kubeconfig --name {self.cluster_name} --region {self.region}"
            logger.info(f"To update kubeconfig manually, run: {cmd}")
            
            # Load kubeconfig
            config.load_kube_config()
            self.k8s_api = client.CoreV1Api()
            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {str(e)}")
            raise

    def get_cluster_nodes(self):
        """Get all nodes in the EKS cluster"""
        try:
            nodes = self.k8s_api.list_node()
            logger.info(f"Found {len(nodes.items)} nodes in the cluster")
            return nodes.items
        except Exception as e:
            logger.error(f"Failed to get cluster nodes: {str(e)}")
            return []

    def get_node_instance_ids(self, nodes):
        """Extract EC2 instance IDs from Kubernetes nodes"""
        instance_ids = []
        for node in nodes:
            provider_id = node.spec.provider_id
            if provider_id and provider_id.startswith('aws:///'):
                # Extract instance ID from provider ID (format: aws:///availability-zone/instance-id)
                instance_id = provider_id.split('/')[-1]
                instance_ids.append(instance_id)
        
        logger.info(f"Extracted {len(instance_ids)} EC2 instance IDs")
        return instance_ids

    def get_node_details(self, instance_ids):
        """Get detailed information about EC2 instances"""
        if not instance_ids:
            return []
            
        try:
            response = self.ec2_client.describe_instances(InstanceIds=instance_ids)
            instances = []
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append(instance)
                    
            logger.info(f"Retrieved details for {len(instances)} EC2 instances")
            return instances
        except Exception as e:
            logger.error(f"Failed to get EC2 instance details: {str(e)}")
            return []

    def check_node_health(self, nodes):
        """Check the health status of Kubernetes nodes"""
        healthy_nodes = 0
        unhealthy_nodes = []
        
        for node in nodes:
            node_name = node.metadata.name
            node_status = True  # Assume healthy by default
            
            # Check node conditions
            for condition in node.status.conditions:
                if condition.type == 'Ready' and condition.status != 'True':
                    node_status = False
                if condition.type in ['DiskPressure', 'MemoryPressure', 'PIDPressure', 'NetworkUnavailable'] and condition.status == 'True':
                    node_status = False
            
            if node_status:
                healthy_nodes += 1
            else:
                unhealthy_nodes.append(node_name)
        
        logger.info(f"Node health check: {healthy_nodes} healthy, {len(unhealthy_nodes)} unhealthy")
        if unhealthy_nodes:
            logger.warning(f"Unhealthy nodes: {', '.join(unhealthy_nodes)}")
        
        return healthy_nodes, unhealthy_nodes

    def collect_node_metrics(self, instance_ids):
        """Collect CloudWatch metrics for EC2 instances"""
        if not instance_ids:
            logger.warning("No instance IDs provided for metrics collection")
            return {}
            
        metrics = {}
        
        for instance_id in instance_ids:
            instance_metrics = self.metrics_collector.get_instance_metrics(instance_id)
            metrics[instance_id] = instance_metrics
            
            # Check for alerts
            self._check_alerts(instance_id, instance_metrics)
            
        return metrics

    def _check_alerts(self, instance_id, metrics):
        """Check if any metrics exceed thresholds and trigger alerts"""
        if not metrics:
            return
            
        alerts = []
        
        # Check CPU utilization
        if 'CPUUtilization' in metrics and metrics['CPUUtilization'] > cfg.ALERT_THRESHOLD_CPU:
            alerts.append(f"High CPU utilization: {metrics['CPUUtilization']:.2f}%")
            
        # Check memory utilization
        if 'MemoryUtilization' in metrics and metrics['MemoryUtilization'] > cfg.ALERT_THRESHOLD_MEMORY:
            alerts.append(f"High memory utilization: {metrics['MemoryUtilization']:.2f}%")
            
        # Check disk utilization
        if 'DiskUtilization' in metrics and metrics['DiskUtilization'] > cfg.ALERT_THRESHOLD_DISK:
            alerts.append(f"High disk utilization: {metrics['DiskUtilization']:.2f}%")
            
        if alerts:
            alert_msg = f"ALERT for instance {instance_id}: {'; '.join(alerts)}"
            logger.warning(alert_msg)
            
            # Send alert to SNS if configured
            if cfg.SNS_TOPIC_ARN:
                self._send_sns_alert(instance_id, alert_msg)

    def _send_sns_alert(self, instance_id, message):
        """Send an alert to SNS topic"""
        try:
            sns_client = boto3.client('sns', region_name=self.region)
            sns_client.publish(
                TopicArn=cfg.SNS_TOPIC_ARN,
                Subject=f"EKS Node Alert - {instance_id}",
                Message=message
            )
            logger.info(f"Alert sent to SNS topic for instance {instance_id}")
        except Exception as e:
            logger.error(f"Failed to send SNS alert: {str(e)}")

    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        logger.info("Starting monitoring cycle")
        
        # Get cluster nodes
        nodes = self.get_cluster_nodes()
        if not nodes:
            logger.warning("No nodes found in the cluster")
            return
            
        # Check node health
        healthy_nodes, unhealthy_nodes = self.check_node_health(nodes)
        
        # Get instance IDs
        instance_ids = self.get_node_instance_ids(nodes)
        
        # Get node details
        instances = self.get_node_details(instance_ids)
        
        # Collect metrics
        metrics = self.collect_node_metrics(instance_ids)
        
        # Print summary
        self._print_summary(nodes, healthy_nodes, unhealthy_nodes, instances, metrics)
        
        logger.info("Monitoring cycle completed")

    def _print_summary(self, nodes, healthy_nodes, unhealthy_nodes, instances, metrics):
        """Print a summary of the monitoring results"""
        print("\n" + "="*50)
        print(f"EKS CLUSTER MONITORING SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        print(f"Cluster: {self.cluster_name}")
        print(f"Total Nodes: {len(nodes)}")
        print(f"Healthy Nodes: {healthy_nodes}")
        print(f"Unhealthy Nodes: {len(unhealthy_nodes)}")
        
        if unhealthy_nodes:
            print("\nUnhealthy Node Details:")
            for node_name in unhealthy_nodes:
                print(f"  - {node_name}")
        
        print("\nNode Metrics:")
        for instance in instances:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']
            private_ip = instance.get('PrivateIpAddress', 'N/A')
            state = instance['State']['Name']
            
            print(f"\n  Instance: {instance_id}")
            print(f"  Type: {instance_type}")
            print(f"  IP: {private_ip}")
            print(f"  State: {state}")
            
            if instance_id in metrics:
                instance_metrics = metrics[instance_id]
                print("  Metrics:")
                for metric_name, metric_value in instance_metrics.items():
                    print(f"    - {metric_name}: {metric_value:.2f}%")
        
        print("\n" + "="*50 + "\n")

    def start_monitoring(self):
        """Start continuous monitoring with scheduled intervals"""
        logger.info(f"Starting EKS monitoring for cluster {self.cluster_name}")
        
        # Run immediately
        self.run_monitoring_cycle()
        
        # Schedule regular runs
        schedule.every(cfg.METRICS_INTERVAL).seconds.do(self.run_monitoring_cycle)
        
        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")


if __name__ == "__main__":
    try:
        monitor = EKSMonitor()
        monitor.start_monitoring()
    except Exception as e:
        logger.critical(f"Failed to start monitoring: {str(e)}")