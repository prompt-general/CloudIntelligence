from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import networkx as nx
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

class NodeType(Enum):
    IAM_USER = "iam_user"
    IAM_ROLE = "iam_role"
    EC2_INSTANCE = "ec2_instance"
    S3_BUCKET = "s3_bucket"
    LAMBDA_FUNCTION = "lambda_function"
    RDS_INSTANCE = "rds_instance"
    KMS_KEY = "kms_key"
    SECRET = "secret"
    VPC = "vpc"
    SUBNET = "subnet"

class EdgeType(Enum):
    CAN_ASSUME = "can_assume"
    CAN_ACCESS = "can_access"
    CAN_EXECUTE = "can_execute"
    CAN_MODIFY = "can_modify"
    NETWORK_REACHABLE = "network_reachable"
    CONTAINS = "contains"
    HAS_PERMISSION = "has_permission"

@dataclass
class AttackNode:
    id: str
    type: NodeType
    name: str
    account_id: str
    region: str
    properties: Dict[str, Any]
    risk_score: float = 0.0
    criticality: str = "medium"  # low, medium, high, critical

@dataclass
class AttackEdge:
    source_id: str
    target_id: str
    type: EdgeType
    properties: Dict[str, Any]
    weight: float = 1.0

@dataclass
class AttackPath:
    nodes: List[AttackNode]
    edges: List[AttackEdge]
    total_risk: float
    path_length: int
    critical_nodes: List[str]

class AttackPathAnalyzer:
    """Analyze potential attack paths in cloud environment."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.graph = nx.DiGraph()
    
    async def build_attack_graph(self, organization_id: str):
        """Build attack graph for the organization and sync to Neo4j."""
        self.graph.clear()
        
        # Get all resources for the organization
        from app.models.cloud_account import CloudAccount
        from app.models.resource import Resource
        
        result = await self.db.execute(
            select(CloudAccount).where(
                CloudAccount.organization_id == organization_id
            )
        )
        accounts = result.scalars().all()
        
        nodes = []
        edges = []
        
        for account in accounts:
            # Get IAM roles and users
            iam_nodes, iam_edges = await self._analyze_iam(account)
            nodes.extend(iam_nodes)
            edges.extend(iam_edges)
            
            # Get EC2 instances and relationships
            ec2_nodes, ec2_edges = await self._analyze_ec2(account)
            nodes.extend(ec2_nodes)
            edges.extend(ec2_edges)
            
            # Get S3 buckets and access
            s3_nodes, s3_edges = await self._analyze_s3(account)
            nodes.extend(s3_nodes)
            edges.extend(s3_edges)
            
            # Get Lambda functions
            lambda_nodes, lambda_edges = await self._analyze_lambda(account)
            nodes.extend(lambda_nodes)
            edges.extend(lambda_edges)
            
            # Get network relationships
            network_edges = await self._analyze_network(account)
            edges.extend(network_edges)
        
        # Add nodes to memory graph
        for node in nodes:
            self.graph.add_node(
                node.id,
                type=node.type.value,
                name=node.name,
                account_id=node.account_id,
                region=node.region,
                risk_score=node.risk_score,
                criticality=node.criticality,
                properties=node.properties
            )
        
        # Add edges to memory graph
        for edge in edges:
            self.graph.add_edge(
                edge.source_id,
                edge.target_id,
                type=edge.type.value,
                weight=edge.weight,
                properties=edge.properties
            )
            
        # Sync to Neo4j
        await self._sync_to_neo4j(nodes, edges, organization_id)
        
        return {
            "nodes": len(nodes),
            "edges": len(edges),
            "accounts": len(accounts)
        }

    async def _sync_to_neo4j(self, nodes: List[AttackNode], edges: List[AttackEdge], organization_id: str):
        """Persist graph data to Neo4j."""
        from app.core.neo4j_client import neo4j_client
        
        # Clear existing data for this organization
        clear_query = "MATCH (n {organization_id: $org_id}) DETACH DELETE n"
        await neo4j_client.execute_query(clear_query, {"org_id": organization_id})
        
        # Create nodes
        create_node_query = """
        UNWIND $nodes as node
        MERGE (n:Resource {id: node.id})
        SET n += node.properties,
            n.name = node.name,
            n.type = node.type,
            n.account_id = node.account_id,
            n.region = node.region,
            n.risk_score = node.risk_score,
            n.criticality = node.criticality,
            n.organization_id = $org_id
        WITH n, node
        CALL apoc.create.addLabels(n, [node.type_label]) YIELD node as labeled_node
        RETURN count(labeled_node)
        """
        
        node_data = []
        for node in nodes:
            node_data.append({
                "id": node.id,
                "name": node.name,
                "type": node.type.value,
                "type_label": node.type.value.replace('_', '').capitalize(),
                "account_id": node.account_id,
                "region": node.region,
                "risk_score": node.risk_score,
                "criticality": node.criticality,
                "properties": node.properties
            })
            
        await neo4j_client.execute_query(create_node_query, {"nodes": node_data, "org_id": organization_id})
        
        # Create edges
        create_edge_query = """
        UNWIND $edges as edge
        MATCH (source {id: edge.source_id})
        MATCH (target {id: edge.target_id})
        CALL apoc.create.relationship(source, edge.type, edge.properties, target) YIELD rel
        RETURN count(rel)
        """
        
        edge_data = []
        for edge in edges:
            edge_data.append({
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "type": edge.type.value.upper(),
                "properties": {**edge.properties, "weight": edge.weight}
            })
            
        await neo4j_client.execute_query(create_edge_query, {"edges": edge_data})

    async def find_attack_paths_neo4j(self, organization_id: str, limit: int = 5):
        """Use Cypher to find deep attack paths from public exposure to critical data."""
        from app.core.neo4j_client import neo4j_client
        
        query = """
        MATCH (source {organization_id: $org_id, is_public: true})
        MATCH (target {organization_id: $org_id, criticality: 'critical'})
        MATCH path = shortestPath((source)-[*..10]->(target))
        WHERE source <> target
        RETURN path, 
               reduce(s = 0, n IN nodes(path) | s + n.risk_score) as total_risk
        ORDER BY total_risk DESC
        LIMIT $limit
        """
        
        results = await neo4j_client.execute_query(query, {"org_id": organization_id, "limit": limit})
        return results
    
    async def find_attack_paths(
        self, 
        source_node_id: Optional[str] = None,
        target_node_id: Optional[str] = None,
        max_path_length: int = 5
    ) -> List[AttackPath]:
        """Find potential attack paths in the graph."""
        paths = []
        
        if source_node_id and target_node_id:
            # Find paths between specific nodes
            try:
                all_paths = nx.all_simple_paths(
                    self.graph,
                    source=source_node_id,
                    target=target_node_id,
                    cutoff=max_path_length
                )
                
                for path in all_paths:
                    attack_path = self._path_to_attack_path(path)
                    paths.append(attack_path)
            except nx.NetworkXNoPath:
                pass
            
        elif source_node_id:
            # Find all paths from source node to high-value targets
            high_value_nodes = [
                node for node, data in self.graph.nodes(data=True)
                if data.get('criticality') in ['high', 'critical']
            ]
            
            for target in high_value_nodes:
                try:
                    all_paths = nx.all_simple_paths(
                        self.graph,
                        source=source_node_id,
                        target=target,
                        cutoff=max_path_length
                    )
                    
                    for path in all_paths:
                        attack_path = self._path_to_attack_path(path)
                        paths.append(attack_path)
                except nx.NetworkXNoPath:
                    continue
        
        else:
            # Find high-risk paths automatically
            critical_nodes = [
                node for node, data in self.graph.nodes(data=True)
                if data.get('criticality') in ['critical']
            ]
            
            for i in range(len(critical_nodes)):
                for j in range(i + 1, len(critical_nodes)):
                    source = critical_nodes[i]
                    target = critical_nodes[j]
                    
                    try:
                        all_paths = nx.all_simple_paths(
                            self.graph,
                            source=source,
                            target=target,
                            cutoff=max_path_length
                        )
                        
                        for path in all_paths:
                            attack_path = self._path_to_attack_path(path)
                            paths.append(attack_path)
                    except nx.NetworkXNoPath:
                        continue
        
        # Sort by total risk
        paths.sort(key=lambda x: x.total_risk, reverse=True)
        
        return paths[:20]  # Return top 20 paths
    
    async def calculate_blast_radius(self, node_id: str) -> Dict[str, Any]:
        """Calculate blast radius for a given node."""
        if node_id not in self.graph:
            return {"error": "Node not found"}
        
        # Calculate reachable nodes
        reachable = nx.descendants(self.graph, node_id)
        
        # Calculate risk metrics
        total_risk = 0
        critical_count = 0
        high_value_targets = []
        
        for node in reachable:
            node_data = self.graph.nodes[node]
            total_risk += node_data.get('risk_score', 0)
            
            if node_data.get('criticality') in ['high', 'critical']:
                critical_count += 1
                high_value_targets.append({
                    'id': node,
                    'name': node_data.get('name', ''),
                    'type': node_data.get('type', ''),
                    'risk_score': node_data.get('risk_score', 0)
                })
        
        avg_risk = total_risk / len(reachable) if reachable else 0
        
        return {
            'node_id': node_id,
            'node_name': self.graph.nodes[node_id].get('name', ''),
            'node_type': self.graph.nodes[node_id].get('type', ''),
            'reachable_nodes': len(reachable),
            'critical_reachable': critical_count,
            'average_risk': avg_risk,
            'total_risk': total_risk,
            'high_value_targets': high_value_targets,
            'recommendations': self._generate_blast_radius_recommendations(node_id, reachable)
        }
    
    async def get_high_risk_nodes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get nodes with highest risk scores."""
        nodes_with_data = [
            (node, data) for node, data in self.graph.nodes(data=True)
        ]
        
        # Sort by risk score
        nodes_with_data.sort(key=lambda x: x[1].get('risk_score', 0), reverse=True)
        
        high_risk_nodes = []
        for node, data in nodes_with_data[:limit]:
            # Calculate blast radius for each
            reachable = nx.descendants(self.graph, node)
            
            high_risk_nodes.append({
                'id': node,
                'name': data.get('name', ''),
                'type': data.get('type', ''),
                'account_id': data.get('account_id', ''),
                'region': data.get('region', ''),
                'risk_score': data.get('risk_score', 0),
                'criticality': data.get('criticality', 'medium'),
                'reachable_nodes': len(reachable),
                'properties': data.get('properties', {})
            })
        
        return high_risk_nodes
    
    def _path_to_attack_path(self, path: List[str]) -> AttackPath:
        """Convert a graph path to AttackPath object."""
        nodes = []
        edges = []
        total_risk = 0
        critical_nodes = []
        
        for node_id in path:
            node_data = self.graph.nodes[node_id]
            
            node = AttackNode(
                id=node_id,
                type=NodeType(node_data['type']),
                name=node_data['name'],
                account_id=node_data['account_id'],
                region=node_data['region'],
                properties=node_data['properties'],
                risk_score=node_data['risk_score'],
                criticality=node_data['criticality']
            )
            
            nodes.append(node)
            total_risk += node_data['risk_score']
            
            if node_data['criticality'] in ['high', 'critical']:
                critical_nodes.append(node_id)
        
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            edge_data = self.graph[source][target]
            
            edge = AttackEdge(
                source_id=source,
                target_id=target,
                type=EdgeType(edge_data['type']),
                properties=edge_data['properties'],
                weight=edge_data['weight']
            )
            
            edges.append(edge)
        
        return AttackPath(
            nodes=nodes,
            edges=edges,
            total_risk=total_risk,
            path_length=len(edges),
            critical_nodes=critical_nodes
        )
    
    async def _analyze_iam(self, account) -> Tuple[List[AttackNode], List[AttackEdge]]:
        """Analyze IAM relationships for attack graph."""
        nodes = []
        edges = []
        
        # This would query AWS IAM data
        # For now, create mock data
        
        # Create IAM role node
        admin_role = AttackNode(
            id=f"arn:aws:iam::{account.account_id}:role/AdminRole",
            type=NodeType.IAM_ROLE,
            name="AdminRole",
            account_id=account.account_id,
            region="global",
            properties={
                "assume_role_policy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": f"arn:aws:iam::{account.account_id}:root"
                            },
                            "Action": "sts:AssumeRole"
                        }
                    ]
                },
                "attached_policies": ["AdministratorAccess"],
                "trusted_entities": ["root"]
            },
            risk_score=90.0,
            criticality="critical"
        )
        nodes.append(admin_role)
        
        # Create IAM user node
        admin_user = AttackNode(
            id=f"arn:aws:iam::{account.account_id}:user/AdminUser",
            type=NodeType.IAM_USER,
            name="AdminUser",
            account_id=account.account_id,
            region="global",
            properties={
                "policies": ["AdministratorAccess"],
                "access_keys": 2,
                "mfa_enabled": False
            },
            risk_score=85.0,
            criticality="critical"
        )
        nodes.append(admin_user)
        
        # Create edge: user can assume role
        edges.append(AttackEdge(
            source_id=admin_user.id,
            target_id=admin_role.id,
            type=EdgeType.CAN_ASSUME,
            properties={
                "permission": "sts:AssumeRole",
                "condition": None
            },
            weight=0.8
        ))
        
        return nodes, edges
    
    async def _analyze_ec2(self, account) -> Tuple[List[AttackNode], List[AttackEdge]]:
        """Analyze EC2 instances and relationships."""
        nodes = []
        edges = []
        
        # Create EC2 instance node
        ec2_instance = AttackNode(
            id=f"arn:aws:ec2:{account.regions[0] if account.regions else 'us-east-1'}:{account.account_id}:instance/i-1234567890",
            type=NodeType.EC2_INSTANCE,
            name="web-server-1",
            account_id=account.account_id,
            region=account.regions[0] if account.regions else "us-east-1",
            properties={
                "instance_type": "t3.large",
                "public_ip": "54.123.45.67",
                "security_groups": ["sg-12345678"],
                "iam_instance_profile": f"arn:aws:iam::{account.account_id}:instance-profile/WebServerProfile",
                "tags": {"Name": "web-server-1", "Environment": "production"}
            },
            risk_score=70.0,
            criticality="high"
        )
        nodes.append(ec2_instance)
        
        # Create edge: IAM role can access EC2
        edges.append(AttackEdge(
            source_id=f"arn:aws:iam::{account.account_id}:role/AdminRole",
            target_id=ec2_instance.id,
            type=EdgeType.CAN_ACCESS,
            properties={
                "permission": "ec2:*",
                "condition": None
            },
            weight=0.9
        ))
        
        return nodes, edges
    
    async def _analyze_s3(self, account) -> Tuple[List[AttackNode], List[AttackEdge]]:
        """Analyze S3 buckets and access."""
        nodes = []
        edges = []
        
        # Create S3 bucket node
        s3_bucket = AttackNode(
            id=f"arn:aws:s3:::customer-data-{account.account_id}",
            type=NodeType.S3_BUCKET,
            name=f"customer-data-{account.account_id}",
            account_id=account.account_id,
            region="us-east-1",
            properties={
                "encryption": "AES-256",
                "versioning": "Enabled",
                "public_access": False,
                "sensitive_data": True,
                "tags": {"Classification": "Confidential", "Department": "Finance"}
            },
            risk_score=80.0,
            criticality="critical"
        )
        nodes.append(s3_bucket)
        
        # Create edge: EC2 instance can access S3
        edges.append(AttackEdge(
            source_id=f"arn:aws:ec2:{account.regions[0] if account.regions else 'us-east-1'}:{account.account_id}:instance/i-1234567890",
            target_id=s3_bucket.id,
            type=EdgeType.CAN_ACCESS,
            properties={
                "permission": "s3:GetObject",
                "condition": None
            },
            weight=0.7
        ))
        
        return nodes, edges
    
    async def _analyze_lambda(self, account) -> Tuple[List[AttackNode], List[AttackEdge]]:
        """Analyze Lambda functions and permissions."""
        nodes = []
        edges = []
        
        # Create Lambda function node
        lambda_func = AttackNode(
            id=f"arn:aws:lambda:{account.regions[0] if account.regions else 'us-east-1'}:{account.account_id}:function:data-processor",
            type=NodeType.LAMBDA_FUNCTION,
            name="data-processor",
            account_id=account.account_id,
            region=account.regions[0] if account.regions else "us-east-1",
            properties={
                "runtime": "python3.9",
                "memory_mb": 512,
                "timeout_seconds": 300,
                "environment_variables": {"DB_PASSWORD": "encrypted"},
                "vpc_config": {
                    "subnet_ids": ["subnet-12345678"],
                    "security_group_ids": ["sg-12345678"]
                }
            },
            risk_score=60.0,
            criticality="medium"
        )
        nodes.append(lambda_func)
        
        # Create edge: Lambda can access S3
        edges.append(AttackEdge(
            source_id=lambda_func.id,
            target_id=f"arn:aws:s3:::customer-data-{account.account_id}",
            type=EdgeType.CAN_ACCESS,
            properties={
                "permission": "s3:*",
                "condition": None
            },
            weight=0.8
        ))
        
        return nodes, edges
    
    async def _analyze_network(self, account) -> List[AttackEdge]:
        """Analyze network relationships."""
        edges = []
        
        # Network reachability edges would be added here
        # Based on security groups, VPC peering, etc.
        
        return edges
    
    def _generate_blast_radius_recommendations(self, node_id: str, reachable: set) -> List[str]:
        """Generate recommendations to reduce blast radius."""
        recommendations = []
        
        node_data = self.graph.nodes[node_id]
        
        if node_data['type'] == 'iam_role':
            if node_data.get('criticality') == 'critical':
                recommendations.append("Apply principle of least privilege to IAM role")
                recommendations.append("Add conditional IAM policies to restrict access")
                recommendations.append("Enable IAM Access Analyzer for policy validation")
        
        elif node_data['type'] == 'ec2_instance':
            if len(reachable) > 10:  # Large blast radius
                recommendations.append("Restrict IAM instance profile permissions")
                recommendations.append("Move instance to private subnet")
                recommendations.append("Implement network segmentation")
        
        elif node_data['type'] == 's3_bucket':
            recommendations.append("Enable S3 Block Public Access")
            recommendations.append("Implement S3 bucket policies with conditions")
            recommendations.append("Enable S3 access logging")
        
        if len(reachable) > 20:
            recommendations.append("Consider implementing Zero Trust architecture")
            recommendations.append("Review and reduce cross-service permissions")
            recommendations.append("Implement just-in-time access for sensitive resources")
        
        return recommendations
    
    def visualize_graph(self) -> Dict[str, Any]:
        """Generate graph visualization data for frontend."""
        nodes = []
        edges = []
        
        # Convert nodes to D3.js format
        for node_id, data in self.graph.nodes(data=True):
            nodes.append({
                'id': node_id,
                'name': data.get('name', node_id),
                'type': data.get('type', ''),
                'group': data.get('type', ''),
                'risk_score': data.get('risk_score', 0),
                'criticality': data.get('criticality', 'medium'),
                'account_id': data.get('account_id', ''),
                'region': data.get('region', ''),
                'size': self._calculate_node_size(data)
            })
        
        # Convert edges to D3.js format
        for source, target, data in self.graph.edges(data=True):
            edges.append({
                'source': source,
                'target': target,
                'type': data.get('type', ''),
                'weight': data.get('weight', 1.0),
                'value': data.get('weight', 1.0)
            })
        
        return {
            'nodes': nodes,
            'links': edges
        }
    
    def _calculate_node_size(self, node_data: Dict) -> int:
        """Calculate node size for visualization based on risk."""
        risk_score = node_data.get('risk_score', 0)
        
        if risk_score > 80:
            return 20
        elif risk_score > 60:
            return 15
        elif risk_score > 40:
            return 10
        else:
            return 5