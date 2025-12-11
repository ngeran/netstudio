"""
Network Topology Discovery Service

Provides automatic network topology discovery using LLDP, BGP, and routing information.
Generates interactive network visualizations and dependency maps.
"""

import asyncio
import logging
import json
import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
import re

try:
    from jnpr.junos import Device
    from jnpr.junos.rpcmeta import _RpcMetaExec
    from jnpr.junos.op.lldp import LLDPNeighborTable
    from jnpr.junos.op.routes import RouteTable
    from jnpr.junos.op.bgppeer import BgpPeerTable
    PYEZ_TOPOLOGY_AVAILABLE = True
except ImportError:
    PYEZ_TOPOLOGY_AVAILABLE = False
    logging.warning("PyEZ topology features not available, using mock implementation")

logger = logging.getLogger(__name__)


@dataclass
class NetworkNode:
    """Represents a network node in the topology"""
    device_id: str
    hostname: str
    device_type: str  # 'router', 'switch', 'firewall'
    vendor: str
    model: str
    os_version: str
    management_ip: str
    site: Optional[str]
    role: Optional[str]
    coordinates: Optional[Tuple[float, float]] = None  # For visualization layout


@dataclass
class NetworkLink:
    """Represents a network link between nodes"""
    source_device: str
    source_interface: str
    destination_device: str
    destination_interface: str
    link_type: str  # 'physical', 'virtual', 'bgp', 'ospf'
    bandwidth: Optional[int] = None
    status: str = 'unknown'
    protocol: Optional[str] = None


@dataclass
class TopologyData:
    """Complete network topology data"""
    topology_id: str
    nodes: List[NetworkNode]
    links: List[NetworkLink]
    discovery_time: datetime
    discovery_method: str
    metadata: Dict[str, Any]


class TopologyService:
    """Network topology discovery and analysis service"""

    def __init__(self, cache_dir: str = "phase3/data/topology"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # NetworkX graph for topology analysis
        self.network_graph = nx.Graph()

        # Topology cache
        self.cached_topology: Optional[TopologyData] = None
        self.last_discovery: Optional[datetime] = None

        # Discovery configuration
        self.discovery_config = {
            'lldp_enabled': True,
            'bgp_topology_enabled': True,
            'routing_table_enabled': True,
            'arp_table_enabled': True,
            'max_discovery_depth': 5,
            'discovery_timeout': 30
        }

        if not PYEZ_TOPOLOGY_AVAILABLE:
            logger.warning("Running topology service in mock mode")

    async def discover_topology(self,
                               seed_devices: List[Dict[str, Any]],
                               discovery_method: str = 'auto') -> TopologyData:
        """Discover network topology starting from seed devices"""
        topology_id = f"topology_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()

        logger.info(f"Starting topology discovery with {len(seed_devices)} seed devices")

        # Initialize data structures
        discovered_nodes: Dict[str, NetworkNode] = {}
        discovered_links: List[NetworkLink] = []
        visited_devices: Set[str] = set()

        # Discover from seed devices recursively
        for seed_device in seed_devices:
            await self._discover_device_topology(
                seed_device, discovered_nodes, discovered_links, visited_devices, depth=0
            )

        # Post-process and enhance topology
        await self._enhance_topology_data(discovered_nodes, discovered_links)

        # Create topology data structure
        topology = TopologyData(
            topology_id=topology_id,
            nodes=list(discovered_nodes.values()),
            links=discovered_links,
            discovery_time=start_time,
            discovery_method=discovery_method,
            metadata={
                'seed_devices': len(seed_devices),
                'total_nodes': len(discovered_nodes),
                'total_links': len(discovered_links),
                'discovery_duration': (datetime.now() - start_time).total_seconds(),
                'discovery_methods_used': self._get_discovery_methods_used()
            }
        )

        # Update network graph
        self._update_network_graph(topology)

        # Cache topology
        self.cached_topology = topology
        self.last_discovery = start_time

        # Save to file
        await self._save_topology(topology)

        logger.info(f"Topology discovery completed: {len(topology.nodes)} nodes, {len(topology.links)} links")
        return topology

    async def _discover_device_topology(self,
                                      device_info: Dict[str, Any],
                                      discovered_nodes: Dict[str, NetworkNode],
                                      discovered_links: List[NetworkLink],
                                      visited_devices: Set[str],
                                      depth: int) -> None:
        """Discover topology from a single device"""
        device_id = device_info['host_ip']

        if device_id in visited_devices or depth > self.discovery_config['max_discovery_depth']:
            return

        visited_devices.add(device_id)
        logger.debug(f"Discovering topology from {device_id} at depth {depth}")

        try:
            # Get device information
            node_info = await self._get_device_info(device_info)
            discovered_nodes[device_id] = node_info

            # Discover neighbors using different methods
            if self.discovery_config['lldp_enabled']:
                lldp_links = await self._discover_lldp_neighbors(device_info)
                discovered_links.extend(lldp_links)

            if self.discovery_config['bgp_topology_enabled']:
                bgp_links = await self._discover_bgp_topology(device_info)
                discovered_links.extend(bgp_links)

            if self.discovery_config['routing_table_enabled']:
                route_discovered_devices = await self._discover_from_routing_table(device_info)

                # Recursively discover new devices
                for neighbor_device in route_discovered_devices:
                    if neighbor_device['host_ip'] not in visited_devices:
                        await self._discover_device_topology(
                            neighbor_device, discovered_nodes, discovered_links,
                            visited_devices, depth + 1
                        )

        except Exception as e:
            logger.error(f"Failed to discover topology from {device_id}: {e}")

    async def _get_device_info(self, device_info: Dict[str, Any]) -> NetworkNode:
        """Get detailed device information"""
        if PYEZ_TOPOLOGY_AVAILABLE:
            try:
                device = Device(
                    host=device_info['host_ip'],
                    user=device_info['username'],
                    password=device_info['password'],
                    gather_facts=True
                )

                device.open()

                # Get system information
                facts = device.facts

                # Determine device type based on facts
                device_type = self._determine_device_type(facts)

                node = NetworkNode(
                    device_id=device_info['host_ip'],
                    hostname=facts.get('hostname', device_info['host_ip']),
                    device_type=device_type,
                    vendor=facts.get('hostname', 'juniper'),  # Assume Juniper for now
                    model=facts.get('model', 'unknown'),
                    os_version=facts.get('version', 'unknown'),
                    management_ip=device_info['host_ip'],
                    site=facts.get('location', None),
                    role=facts.get('personality', None)
                )

                device.close()
                return node

            except Exception as e:
                logger.error(f"Failed to get device info for {device_info['host_ip']}: {e}")

        # Mock implementation
        import random
        device_types = ['router', 'switch', 'firewall']
        models = ['MX480', 'EX4300', 'SRX4100', 'QFX5100', 'MX960']

        node = NetworkNode(
            device_id=device_info['host_ip'],
            hostname=f"device-{device_info['host_ip'].replace('.', '-')}",
            device_type=random.choice(device_types),
            vendor='juniper',
            model=random.choice(models),
            os_version=f"20.4R3-S{random.randint(1, 9)}",
            management_ip=device_info['host_ip'],
            site=random.choice(['datacenter1', 'datacenter2', 'branch1', 'branch2']),
            role=random.choice(['core', 'distribution', 'access', 'edge'])
        )

        return node

    def _determine_device_type(self, facts: Dict[str, Any]) -> str:
        """Determine device type based on device facts"""
        model = facts.get('model', '').lower()
        personality = facts.get('personality', '').lower()

        if 'mx' in model or personality == 'router':
            return 'router'
        elif 'ex' in model or 'qfx' in model or personality == 'switch':
            return 'switch'
        elif 'srx' in model or personality == 'firefly':
            return 'firewall'
        elif 'virtual' in model:
            return 'router'  # vMX
        else:
            return 'router'  # Default

    async def _discover_lldp_neighbors(self, device_info: Dict[str, Any]) -> List[NetworkLink]:
        """Discover LLDP neighbors"""
        links = []

        if PYEZ_TOPOLOGY_AVAILABLE:
            try:
                device = Device(
                    host=device_info['host_ip'],
                    user=device_info['username'],
                    password=device_info['password'],
                    gather_facts=False
                )

                device.open()

                lldp_table = LLDPNeighborTable(device)
                lldp_table.get()

                for neighbor in lldp_table:
                    link = NetworkLink(
                        source_device=device_info['host_ip'],
                        source_interface=neighbor.local_interface,
                        destination_device=neighbor.remote_chassis_id,
                        destination_interface=neighbor.remote_port,
                        link_type='physical',
                        status='up'
                    )
                    links.append(link)

                device.close()

            except Exception as e:
                logger.error(f"Failed to discover LLDP neighbors: {e}")

        # Mock implementation
        import random
        num_neighbors = random.randint(1, 4)
        interfaces = ['ge-0/0/0', 'ge-0/0/1', 'ge-0/0/2', 'xe-0/1/0', 'xe-0/1/1']
        remote_interfaces = ['ge-0/0/0', 'ge-0/0/1', 'xe-0/1/0', 'et-0/0/0']

        for i in range(min(num_neighbors, len(interfaces))):
            remote_ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
            link = NetworkLink(
                source_device=device_info['host_ip'],
                source_interface=interfaces[i],
                destination_device=remote_ip,
                destination_interface=random.choice(remote_interfaces),
                link_type='physical',
                bandwidth=random.choice([1000000000, 10000000000]),
                status='up'
            )
            links.append(link)

        return links

    async def _discover_bgp_topology(self, device_info: Dict[str, Any]) -> List[NetworkLink]:
        """Discover BGP topology"""
        links = []

        if PYEZ_TOPOLOGY_AVAILABLE:
            try:
                device = Device(
                    host=device_info['host_ip'],
                    user=device_info['username'],
                    password=device_info['password'],
                    gather_facts=False
                )

                device.open()

                bgp_table = BgpPeerTable(device)
                bgp_table.get()

                for peer in bgp_table:
                    if peer.peer_state == 'Established':
                        link = NetworkLink(
                            source_device=device_info['host_ip'],
                            source_interface='bgp',
                            destination_device=peer.peer_address,
                            destination_interface='bgp',
                            link_type='bgp',
                            status='up',
                            protocol='bgp'
                        )
                        links.append(link)

                device.close()

            except Exception as e:
                logger.error(f"Failed to discover BGP topology: {e}")

        # Mock implementation
        import random
        num_bgp_peers = random.randint(2, 6)
        peer_asns = [65001, 65002, 65003, 65100, 65200]

        for i in range(num_bgp_peers):
            peer_ip = f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}"
            peer_as = random.choice(peer_asns)

            link = NetworkLink(
                source_device=device_info['host_ip'],
                source_interface=f'bgp_as{peer_as}',
                destination_device=peer_ip,
                destination_interface=f'bgp_as65000',
                link_type='bgp',
                status='Established',
                protocol='bgp'
            )
            links.append(link)

        return links

    async def _discover_from_routing_table(self, device_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover devices from routing table (next hops)"""
        discovered_devices = []

        if PYEZ_TOPOLOGY_AVAILABLE:
            try:
                device = Device(
                    host=device_info['host_ip'],
                    user=device_info['username'],
                    password=device_info['password'],
                    gather_facts=False
                )

                device.open()

                route_table = RouteTable(device)
                route_table.get()

                next_hops = set()
                for route in route_table:
                    if route.nexthop and route.nexthop != '0.0.0.0':
                        next_hops.add(route.nexthop)

                # Convert next hops to device info (simplified)
                for next_hop in next_hops:
                    # This is simplified - in reality would need to correlate with known devices
                    if self._is_likely_device(next_hop):
                        device_dict = {
                            'host_ip': next_hop,
                            'username': device_info['username'],  # Assume same credentials
                            'password': device_info['password']
                        }
                        discovered_devices.append(device_dict)

                device.close()

            except Exception as e:
                logger.error(f"Failed to discover from routing table: {e}")

        # Mock implementation
        import random
        num_next_hops = random.randint(1, 3)

        for i in range(num_next_hops):
            next_hop = f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"
            device_dict = {
                'host_ip': next_hop,
                'username': 'admin',
                'password': 'password'
            }
            discovered_devices.append(device_dict)

        return discovered_devices

    def _is_likely_device(self, ip_address: str) -> bool:
        """Determine if IP is likely a network device"""
        # Simple heuristic - exclude common non-device IPs
        exclude_patterns = [
            r'127\.',
            r'0\.0\.0\.0',
            r'255\.255\.255\.255',
            r'169\.254\.',
        ]

        for pattern in exclude_patterns:
            if re.match(pattern, ip_address):
                return False

        return True

    async def _enhance_topology_data(self,
                                   nodes: Dict[str, NetworkNode],
                                   links: List[NetworkLink]) -> None:
        """Enhance topology data with additional analysis"""
        # Calculate node coordinates for visualization
        self._calculate_layout(nodes)

        # Identify network segments
        self._identify_network_segments(nodes, links)

        # Add link bandwidth aggregation
        self._aggregate_link_bandwidth(links)

    def _calculate_layout(self, nodes: Dict[str, NetworkNode]) -> None:
        """Calculate node coordinates for visualization"""
        if not nodes:
            return

        # Create NetworkX graph
        G = nx.Graph()

        for node_id, node in nodes.items():
            G.add_node(node_id, **asdict(node))

        # Add edges
        for link in links:
            if link.source_device in nodes and link.destination_device in nodes:
                G.add_edge(link.source_device, link.destination_device)

        # Use spring layout for positioning
        if G.number_of_edges() > 0:
            pos = nx.spring_layout(G, k=2, iterations=50)
            for node_id, (x, y) in pos.items():
                if node_id in nodes:
                    nodes[node_id].coordinates = (float(x), float(y))
        else:
            # Simple circular layout for isolated nodes
            import math
            for i, node_id in enumerate(nodes.keys()):
                angle = 2 * math.pi * i / len(nodes)
                nodes[node_id].coordinates = (math.cos(angle), math.sin(angle))

    def _identify_network_segments(self,
                                 nodes: Dict[str, NetworkNode],
                                 links: List[NetworkLink]) -> None:
        """Identify network segments and site boundaries"""
        # Simple site identification based on IP ranges
        for node in nodes.values():
            if node.site is None:
                # Derive site from IP address
                if '172.27' in node.management_ip:
                    node.site = 'datacenter_main'
                elif '10.0' in node.management_ip:
                    node.site = 'branch_network'
                elif '192.168' in node.management_ip:
                    node.site = 'management_network'
                else:
                    node.site = 'unknown'

    def _aggregate_link_bandwidth(self, links: List[NetworkLink]) -> None:
        """Aggregate bandwidth for parallel links"""
        # Group links by source-destination pairs
        link_groups = {}
        for link in links:
            key = (link.source_device, link.destination_device, link.link_type)
            if key not in link_groups:
                link_groups[key] = []
            link_groups[key].append(link)

        # Aggregate bandwidth for groups with multiple links
        for key, group_links in link_groups.items():
            if len(group_links) > 1:
                total_bandwidth = sum(link.bandwidth or 0 for link in group_links)
                # Update the primary link with aggregated bandwidth
                group_links[0].bandwidth = total_bandwidth

    def _get_discovery_methods_used(self) -> List[str]:
        """Get list of discovery methods that were used"""
        methods = []
        if self.discovery_config['lldp_enabled']:
            methods.append('lldp')
        if self.discovery_config['bgp_topology_enabled']:
            methods.append('bgp')
        if self.discovery_config['routing_table_enabled']:
            methods.append('routing_table')
        if self.discovery_config['arp_table_enabled']:
            methods.append('arp_table')
        return methods

    def _update_network_graph(self, topology: TopologyData) -> None:
        """Update NetworkX graph with new topology"""
        self.network_graph.clear()

        # Add nodes
        for node in topology.nodes:
            self.network_graph.add_node(
                node.device_id,
                **asdict(node)
            )

        # Add edges
        for link in topology.links:
            self.network_graph.add_edge(
                link.source_device,
                link.destination_device,
                **asdict(link)
            )

    async def _save_topology(self, topology: TopologyData) -> None:
        """Save topology to file"""
        topology_file = self.cache_dir / f"{topology.topology_id}.json"

        # Convert to dict for JSON serialization
        topology_dict = asdict(topology)
        topology_dict['discovery_time'] = topology.discovery_time.isoformat()

        # Convert datetime objects in nodes
        for i, node in enumerate(topology_dict['nodes']):
            if node.get('coordinates'):
                topology_dict['nodes'][i]['coordinates'] = tuple(node['coordinates'])

        with open(topology_file, 'w') as f:
            json.dump(topology_dict, f, indent=2, default=str)

        logger.info(f"Saved topology to {topology_file}")

    def get_topology(self, topology_id: Optional[str] = None) -> Optional[TopologyData]:
        """Get topology data"""
        if topology_id:
            # Load from file
            topology_file = self.cache_dir / f"{topology_id}.json"
            if topology_file.exists():
                return self._load_topology(topology_file)
            return None
        else:
            # Return cached topology
            return self.cached_topology

    def _load_topology(self, topology_file: Path) -> TopologyData:
        """Load topology from file"""
        with open(topology_file) as f:
            topology_dict = json.load(f)

        # Convert ISO string back to datetime
        topology_dict['discovery_time'] = datetime.fromisoformat(topology_dict['discovery_time'])

        # Convert nodes back to NetworkNode objects
        nodes = []
        for node_dict in topology_dict['nodes']:
            if isinstance(node_dict.get('coordinates'), list):
                node_dict['coordinates'] = tuple(node_dict['coordinates'])
            nodes.append(NetworkNode(**node_dict))
        topology_dict['nodes'] = nodes

        # Convert links back to NetworkLink objects
        links = [NetworkLink(**link_dict) for link_dict in topology_dict['links']]
        topology_dict['links'] = links

        return TopologyData(**topology_dict)

    def get_topology_summary(self) -> Dict[str, Any]:
        """Get topology summary statistics"""
        if not self.cached_topology:
            return {}

        topology = self.cached_topology

        # Count device types
        device_type_counts = {}
        for node in topology.nodes:
            device_type_counts[node.device_type] = device_type_counts.get(node.device_type, 0) + 1

        # Count link types
        link_type_counts = {}
        for link in topology.links:
            link_type_counts[link.link_type] = link_type_counts.get(link.link_type, 0) + 1

        # Count sites
        site_counts = {}
        for node in topology.nodes:
            if node.site:
                site_counts[node.site] = site_counts.get(node.site, 0) + 1

        # Network connectivity analysis
        connectivity_metrics = {}
        if self.network_graph.number_of_nodes() > 0:
            connectivity_metrics = {
                'is_connected': nx.is_connected(self.network_graph),
                'number_of_components': nx.number_connected_components(self.network_graph),
                'average_clustering': nx.average_clustering(self.network_graph),
                'density': nx.density(self.network_graph)
            }

        return {
            'topology_id': topology.topology_id,
            'discovery_time': topology.discovery_time.isoformat(),
            'total_nodes': len(topology.nodes),
            'total_links': len(topology.links),
            'device_types': device_type_counts,
            'link_types': link_type_counts,
            'sites': site_counts,
            'connectivity_metrics': connectivity_metrics,
            'discovery_method': topology.discovery_method,
            'metadata': topology.metadata
        }

    def get_device_path(self, source_device: str, destination_device: str) -> List[str]:
        """Get path between two devices"""
        try:
            return nx.shortest_path(self.network_graph, source_device, destination_device)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_device_neighbors(self, device_id: str, depth: int = 1) -> List[str]:
        """Get neighboring devices within specified depth"""
        try:
            neighbors = []
            for node, distance in nx.single_source_shortest_path_length(
                self.network_graph, device_id, cutoff=depth
            ).items():
                if distance > 0:
                    neighbors.append(node)
            return neighbors
        except nx.NodeNotFound:
            return []

    def find_critical_devices(self) -> List[str]:
        """Find critical devices using betweenness centrality"""
        if self.network_graph.number_of_nodes() < 2:
            return []

        centrality = nx.betweenness_centrality(self.network_graph)
        # Sort by centrality and return top 20%
        sorted_devices = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        top_count = max(1, len(sorted_devices) // 5)
        return [device for device, _ in sorted_devices[:top_count]]

    def export_topology(self, format: str = 'graphml') -> str:
        """Export topology to various formats"""
        if not self.cached_topology:
            raise ValueError("No topology available to export")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"topology_{timestamp}.{format}"
        filepath = self.cache_dir / filename

        if format.lower() == 'graphml':
            nx.write_graphml(self.network_graph, filepath)
        elif format.lower() == 'gexf':
            nx.write_gexf(self.network_graph, filepath)
        elif format.lower() == 'json':
            with open(filepath, 'w') as f:
                json.dump(asdict(self.cached_topology), f, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        logger.info(f"Exported topology to {filepath}")
        return str(filepath)

    def get_topology_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of historical topology files"""
        topology_files = sorted(self.cache_dir.glob("topology_*.json"), reverse=True)[:limit]
        history = []

        for file_path in topology_files:
            try:
                with open(file_path) as f:
                    topology_data = json.load(f)
                history.append({
                    'topology_id': topology_data['topology_id'],
                    'discovery_time': topology_data['discovery_time'],
                    'total_nodes': len(topology_data['nodes']),
                    'total_links': len(topology_data['links']),
                    'file_path': str(file_path)
                })
            except Exception as e:
                logger.error(f"Failed to read topology file {file_path}: {e}")

        return history