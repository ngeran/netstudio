"""
BGP Toolbox Screen

Comprehensive BGP management interface for monitoring and managing BGP sessions.
View peer status, routing tables, and detailed peer information.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    Button,
    Static,
    DataTable,
    Select,
    Label,
    TabbedContent,
    TabPane,
)
from textual.reactive import reactive
from textual import work

# Import legacy BGP functions
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.connect_to_hosts import connect_to_hosts, disconnect_from_hosts

logger = logging.getLogger(__name__)


class BGPToolboxScreen(Screen):
    """BGP management and monitoring screen"""

    # Selected device
    selected_device: reactive[Optional[str]] = reactive(None)

    # BGP data
    bgp_peers: reactive[List[Dict]] = reactive([])
    bgp_running: reactive[bool] = reactive(False)
    is_loading: reactive[bool] = reactive(False)

    # Connection
    device_connection = None

    # Reports directory
    reports_dir = Path("reports")

    def __init__(self, inventory_service, api_service):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service
        self.reports_dir.mkdir(exist_ok=True)

        # Load available devices
        try:
            self.available_devices = self.inventory_service.load_devices()
        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
            self.available_devices = []

    def compose(self):
        """Compose the BGP toolbox screen layout"""
        yield Header("🔀 BGP Toolbox")

        with Container(classes="bgp-container"):
            # Control panel
            with Horizontal(classes="bgp-controls"):
                with Vertical(classes="control-section"):
                    yield Label("Device:")
                    device_options = [
                        (f"{d.host_name} ({d.ip_address})", d.ip_address)
                        for d in self.available_devices
                    ]
                    yield Select(
                        options=device_options
                        if device_options
                        else [("No devices", "none")],
                        id="device_select",
                        allow_blank=False,
                    )

                with Vertical(classes="control-section"):
                    yield Label("Actions:")
                    with Horizontal():
                        yield Button("🔄 Refresh", id="btn_refresh", variant="primary")
                        yield Button(
                            "📊 Export Report", id="btn_export", variant="default"
                        )

            # Status bar
            yield Static(
                "Select a device to view BGP information",
                id="bgp_status",
                classes="bgp-status",
            )

            # Tabbed content area
            with TabbedContent(id="bgp_tabs"):
                # Tab 1: Peer Summary
                with TabPane("Peer Summary", id="tab_peers"):
                    yield Static("BGP Peer Status", classes="panel-title")
                    yield DataTable(id="peers_table", classes="bgp-table")

                # Tab 2: Routing Table
                with TabPane("Routing Table", id="tab_routes"):
                    yield Static("BGP Routes (inet.0)", classes="panel-title")
                    yield DataTable(id="routes_table", classes="bgp-table")

                # Tab 3: Peer Details
                with TabPane("Peer Details", id="tab_details"):
                    yield Static("Detailed Peer Information", classes="panel-title")
                    with VerticalScroll(
                        id="peer_details_scroll", classes="peer-details"
                    ):
                        yield Static(
                            "Select a device and click Refresh to view peer details",
                            id="peer_details_content",
                        )

        yield Button("🔙 Back", id="btn_back")
        yield Footer()

    def on_mount(self):
        """Initialize when screen is mounted"""
        self._setup_peers_table()
        self._setup_routes_table()

    def _setup_peers_table(self):
        """Setup the BGP peers table"""
        table = self.query_one("#peers_table", DataTable)
        table.clear(columns=True)
        table.add_column("Peer Address", width=18)
        table.add_column("AS", width=10)
        table.add_column("State", width=12)
        table.add_column("Received", width=12)
        table.add_column("Advertised", width=12)
        table.add_column("Up/Down", width=12)

    def _setup_routes_table(self):
        """Setup the BGP routes table"""
        table = self.query_one("#routes_table", DataTable)
        table.clear(columns=True)
        table.add_column("Prefix", width=20)
        table.add_column("Next Hop", width=18)
        table.add_column("AS Path", width=25)
        table.add_column("MED", width=10)
        table.add_column("Local Pref", width=12)

    def _update_peers_table(self):
        """Update the peers table with current data"""
        table = self.query_one("#peers_table", DataTable)
        table.clear()

        if not self.bgp_peers:
            return

        for peer in self.bgp_peers:
            # Color code based on state
            state = peer.get("state", "Unknown")
            if state == "Established":
                state_display = f"[green]{state}[/]"
            else:
                state_display = f"[red]{state}[/]"

            table.add_row(
                peer.get("peer_address", "-"),
                peer.get("peer_as", "-"),
                state_display,
                peer.get("received_routes", "0"),
                peer.get("advertised_routes", "0"),
                peer.get("uptime", "-"),
            )

    def _update_routes_table(self, routes: List[Dict]):
        """Update the routes table with BGP routes"""
        table = self.query_one("#routes_table", DataTable)
        table.clear()

        if not routes:
            return

        # Limit to 100 routes for performance
        for route in routes[:100]:
            table.add_row(
                route.get("prefix", "-"),
                route.get("next_hop", "-"),
                route.get("as_path", "-"),
                route.get("med", "-"),
                route.get("local_pref", "-"),
            )

    def _update_peer_details(self, peer_details: List[Dict]):
        """Update the peer details view"""
        details_widget = self.query_one("#peer_details_content", Static)

        if not peer_details:
            details_widget.update("[dim]No peer details available[/]")
            return

        output = []
        for peer in peer_details:
            output.append(
                f"\n[bold cyan]Peer: {peer.get('peer_address', 'Unknown')}[/]"
            )
            output.append(f"  [bold]AS Number:[/] {peer.get('peer_as', 'N/A')}")
            output.append(f"  [bold]State:[/] {peer.get('state', 'Unknown')}")
            output.append(f"  [bold]Router ID:[/] {peer.get('router_id', 'N/A')}")
            output.append(f"  [bold]Group:[/] {peer.get('group', 'N/A')}")
            output.append(f"  [bold]Uptime:[/] {peer.get('uptime', 'N/A')}")

            output.append(f"\n  [bold yellow]Route Statistics:[/]")
            output.append(f"    Received: {peer.get('received_routes', '0')}")
            output.append(f"    Advertised: {peer.get('advertised_routes', '0')}")
            output.append(f"    Active: {peer.get('active_routes', '0')}")

            # Advertised routes
            if peer.get("advertised_prefixes"):
                output.append(f"\n  [bold green]Advertised Prefixes:[/]")
                for prefix in peer["advertised_prefixes"][:10]:  # Show first 10
                    output.append(f"    • {prefix}")
                if len(peer["advertised_prefixes"]) > 10:
                    output.append(
                        f"    [dim]... and {len(peer['advertised_prefixes']) - 10} more[/]"
                    )

            # Received routes
            if peer.get("received_prefixes"):
                output.append(f"\n  [bold blue]Received Prefixes:[/]")
                for prefix in peer["received_prefixes"][:10]:  # Show first 10
                    output.append(f"    • {prefix}")
                if len(peer["received_prefixes"]) > 10:
                    output.append(
                        f"    [dim]... and {len(peer['received_prefixes']) - 10} more[/]"
                    )

            output.append("\n" + "─" * 60)

        details_widget.update("\n".join(output))

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "btn_back":
            await self._cleanup_connection()
            self.app.pop_screen()

        elif button_id == "btn_refresh":
            self._refresh_bgp_data()

        elif button_id == "btn_export":
            self._export_report()

    def on_select_changed(self, event: Select.Changed):
        """Handle device selection changes"""
        if event.select.id == "device_select":
            self.selected_device = event.value
            # Auto-refresh when device changes
            self._refresh_bgp_data()

    @work(exclusive=True)
    async def _refresh_bgp_data(self):
        """Refresh BGP data from selected device"""
        if not self.selected_device or self.selected_device == "none":
            self.notify("Please select a device first", severity="warning")
            return

        if self.is_loading:
            return

        self.is_loading = True
        status_widget = self.query_one("#bgp_status", Static)
        status_widget.update("🔄 Loading BGP information...")

        try:
            # Get device credentials
            device = next(
                (
                    d
                    for d in self.available_devices
                    if d.ip_address == self.selected_device
                ),
                None,
            )

            if not device:
                raise ValueError("Selected device not found")

            username = device.username if device.username else "admin"
            password = device.password if device.password else "password"

            # Connect to device
            if not self.device_connection:
                connections = await asyncio.to_thread(
                    connect_to_hosts, [self.selected_device], username, password
                )

                if not connections:
                    raise Exception("Failed to connect to device")

                self.device_connection = connections[0]

            # Check if BGP is running
            self.bgp_running = await asyncio.to_thread(
                self._check_bgp_running, self.device_connection
            )

            if not self.bgp_running:
                status_widget.update(
                    "⚠️ BGP is not configured or running on this device"
                )
                self.notify("BGP is not running on this device", severity="warning")
                return

            # Fetch BGP data in parallel
            peers_task = asyncio.to_thread(self._get_bgp_peers, self.device_connection)

            routes_task = asyncio.to_thread(
                self._get_bgp_routes, self.device_connection
            )

            details_task = asyncio.to_thread(
                self._get_peer_details, self.device_connection
            )

            peers_data, routes_data, details_data = await asyncio.gather(
                peers_task, routes_task, details_task, return_exceptions=True
            )

            # Update tables
            if not isinstance(peers_data, Exception):
                self.bgp_peers = peers_data
                self._update_peers_table()

            if not isinstance(routes_data, Exception):
                self._update_routes_table(routes_data)

            if not isinstance(details_data, Exception):
                self._update_peer_details(details_data)

            status_widget.update(
                f"✅ BGP data loaded | Peers: {len(self.bgp_peers)} | "
                f"Last update: {datetime.now().strftime('%H:%M:%S')}"
            )
            self.notify("BGP data refreshed successfully", severity="success")

        except Exception as e:
            status_widget.update(f"❌ Failed to load BGP data: {str(e)}")
            self.notify(f"Failed to refresh: {str(e)}", severity="error")
            logger.error(f"BGP refresh error: {e}", exc_info=True)

        finally:
            self.is_loading = False

    def _check_bgp_running(self, device) -> bool:
        """Check if BGP is running on device"""
        try:
            response = device.rpc.get_bgp_summary_information()
            if response.findtext(".//bgp-peer") is not None:
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking BGP status: {e}")
            return False

    def _get_bgp_peers(self, device) -> List[Dict]:
        """Get BGP peer information"""
        peers = []
        try:
            summary = device.rpc.get_bgp_summary_information()
            for peer in summary.findall(".//bgp-peer"):
                peer_data = {
                    "peer_address": peer.findtext("peer-address") or "-",
                    "peer_as": peer.findtext("peer-as") or "-",
                    "state": peer.findtext("peer-state") or "Unknown",
                    "received_routes": peer.findtext("received-prefix-count") or "0",
                    "advertised_routes": peer.findtext("advertised-prefix-count")
                    or "0",
                    "active_routes": peer.findtext("active-prefix-count") or "0",
                    "uptime": peer.findtext("elapsed-time") or "-",
                }
                peers.append(peer_data)
        except Exception as e:
            logger.error(f"Error getting BGP peers: {e}")

        return peers

    def _get_bgp_routes(self, device) -> List[Dict]:
        """Get BGP routes from routing table"""
        routes = []
        try:
            response = device.rpc.get_route_information(table="inet.0", protocol="bgp")
            for rt in response.findall(".//rt"):
                route_data = {
                    "prefix": rt.findtext("rt-destination") or "-",
                    "next_hop": rt.findtext(".//to") or "-",
                    "as_path": rt.findtext(".//as-path") or "-",
                    "med": rt.findtext(".//med") or "-",
                    "local_pref": rt.findtext(".//local-preference") or "-",
                }
                routes.append(route_data)
        except Exception as e:
            logger.error(f"Error getting BGP routes: {e}")

        return routes

    def _get_peer_details(self, device) -> List[Dict]:
        """Get detailed peer information including advertised/received prefixes"""
        peer_details = []
        try:
            # Get basic peer info with groups
            groups = device.rpc.get_bgp_group_information()
            peer_to_group = {}

            for group in groups.findall(".//bgp-group"):
                group_name = group.findtext("group-name")
                for peer in group.findall(".//bgp-peer"):
                    peer_ip = peer.findtext("peer-address")
                    if peer_ip:
                        peer_to_group[peer_ip] = group_name

            # Get summary info
            summary = device.rpc.get_bgp_summary_information()
            for peer in summary.findall(".//bgp-peer"):
                peer_ip = peer.findtext("peer-address")

                detail = {
                    "peer_address": peer_ip,
                    "peer_as": peer.findtext("peer-as") or "-",
                    "state": peer.findtext("peer-state") or "Unknown",
                    "router_id": peer.findtext("peer-id") or "-",
                    "group": peer_to_group.get(peer_ip, "Unknown"),
                    "uptime": peer.findtext("elapsed-time") or "-",
                    "received_routes": peer.findtext("received-prefix-count") or "0",
                    "advertised_routes": peer.findtext("advertised-prefix-count")
                    or "0",
                    "active_routes": peer.findtext("active-prefix-count") or "0",
                    "advertised_prefixes": [],
                    "received_prefixes": [],
                }

                # Get advertised prefixes
                try:
                    advertised = device.rpc.get_route_information(
                        protocol="bgp", peer=peer_ip, advertising_protocol_name="bgp"
                    )
                    for rt in advertised.findall(".//rt"):
                        prefix = rt.findtext("rt-destination")
                        if prefix:
                            detail["advertised_prefixes"].append(prefix)
                except Exception:
                    pass

                # Get received prefixes
                try:
                    received = device.rpc.get_route_information(
                        protocol="bgp", receive_protocol_name="bgp", peer=peer_ip
                    )
                    for rt in received.findall(".//rt"):
                        prefix = rt.findtext("rt-destination")
                        if prefix:
                            detail["received_prefixes"].append(prefix)
                except Exception:
                    pass

                peer_details.append(detail)

        except Exception as e:
            logger.error(f"Error getting peer details: {e}")

        return peer_details

    @work(exclusive=True)
    async def _export_report(self):
        """Export BGP report to file"""
        if not self.bgp_peers:
            self.notify("No BGP data to export", severity="warning")
            return

        try:
            report_file = (
                self.reports_dir
                / f"bgp_report_{self.selected_device}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )

            with open(report_file, "w") as f:
                f.write(f"BGP Report: {self.selected_device}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")

                f.write("BGP Peer Summary:\n")
                f.write("-" * 80 + "\n")
                f.write(
                    f"{'Peer Address':<18} {'AS':<10} {'State':<12} {'Received':<12} {'Advertised':<12} {'Uptime':<12}\n"
                )
                f.write("-" * 80 + "\n")

                for peer in self.bgp_peers:
                    f.write(
                        f"{peer.get('peer_address', '-'):<18} "
                        f"{peer.get('peer_as', '-'):<10} "
                        f"{peer.get('state', '-'):<12} "
                        f"{peer.get('received_routes', '0'):<12} "
                        f"{peer.get('advertised_routes', '0'):<12} "
                        f"{peer.get('uptime', '-'):<12}\n"
                    )

            self.notify(f"Report saved: {report_file.name}", severity="success")
            logger.info(f"BGP report saved to {report_file}")

        except Exception as e:
            self.notify(f"Failed to save report: {str(e)}", severity="error")
            logger.error(f"Report save error: {e}", exc_info=True)

    async def _cleanup_connection(self):
        """Clean up device connection"""
        if self.device_connection:
            try:
                await asyncio.to_thread(disconnect_from_hosts, [self.device_connection])
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            self.device_connection = None
