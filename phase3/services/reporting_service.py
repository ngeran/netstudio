"""
Reporting and Analytics Service

Provides comprehensive reporting, analytics, and operational insights.
Generates scheduled reports and exports in multiple formats.
"""

import asyncio
import logging
import json
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import csv
from io import StringIO, BytesIO
from enum import Enum

# For PDF generation (optional, with fallback)
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("ReportLab not available, PDF reports disabled")

# For advanced charts (optional)
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import base64
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib not available, chart generation disabled")

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Report types"""
    DEPLOYMENT_SUMMARY = "deployment_summary"
    DEVICE_HEALTH = "device_health"
    CONFIGURATION_DRIFT = "configuration_drift"
    BGP_ANALYSIS = "bgp_analysis"
    PERFORMANCE_TRENDS = "performance_trends"
    COMPLIANCE_AUDIT = "compliance_audit"
    ALERT_SUMMARY = "alert_summary"
    TOPOLOGY_ANALYSIS = "topology_analysis"


class ReportFormat(str, Enum):
    """Report export formats"""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"


@dataclass
class ReportDefinition:
    """Report definition and configuration"""
    report_id: str
    name: str
    description: str
    report_type: ReportType
    parameters: Dict[str, Any]
    schedule: Optional[str] = None  # Cron expression
    recipients: List[str] = None
    created_at: datetime = None
    last_run: Optional[datetime] = None
    enabled: bool = True

    def __post_init__(self):
        if self.recipients is None:
            self.recipients = []
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ReportExecution:
    """Report execution record"""
    execution_id: str
    report_id: str
    status: str  # 'running', 'completed', 'failed'
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    output_file: Optional[str] = None
    format: ReportFormat = ReportFormat.JSON
    parameters: Dict[str, Any] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class ReportingService:
    """Reporting and analytics service"""

    def __init__(self,
                 db_path: str = "phase3/data/monitoring.db",
                 output_dir: str = "phase3/reports"):
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize reporting database
        self._init_reporting_db()

        # Report definitions
        self.report_definitions: Dict[str, ReportDefinition] = {}
        self._create_default_reports()

        # Report execution tracking
        self.active_executions: Dict[str, ReportExecution] = {}

        logger.info("Reporting service initialized")

    def _init_reporting_db(self):
        """Initialize reporting database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Report definitions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS report_definitions (
                report_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                report_type TEXT NOT NULL,
                parameters TEXT,
                schedule TEXT,
                recipients TEXT,
                created_at DATETIME,
                last_run DATETIME,
                enabled BOOLEAN DEFAULT TRUE
            )
        ''')

        # Report executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS report_executions (
                execution_id TEXT PRIMARY KEY,
                report_id TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                duration REAL,
                output_file TEXT,
                format TEXT,
                parameters TEXT,
                error_message TEXT,
                FOREIGN KEY (report_id) REFERENCES report_definitions (report_id)
            )
        ''')

        conn.commit()
        conn.close()

    def _create_default_reports(self):
        """Create default report definitions"""
        default_reports = [
            ReportDefinition(
                report_id="daily_deployment_summary",
                name="Daily Deployment Summary",
                description="Summary of all configuration deployments in the last 24 hours",
                report_type=ReportType.DEPLOYMENT_SUMMARY,
                parameters={"time_range": "24h", "include_details": True},
                schedule="0 8 * * *",  # Daily at 8 AM
                recipients=["admin@company.com"]
            ),
            ReportDefinition(
                report_id="weekly_device_health",
                name="Weekly Device Health Report",
                description="Health status and performance metrics for all monitored devices",
                report_type=ReportType.DEVICE_HEALTH,
                parameters={"time_range": "7d", "include_charts": True},
                schedule="0 9 * * 1",  # Weekly on Monday at 9 AM
                recipients=["ops@company.com"]
            ),
            ReportDefinition(
                report_id="monthly_bgp_analysis",
                name="Monthly BGP Analysis",
                description="Comprehensive BGP session analysis and stability metrics",
                report_type=ReportType.BGP_ANALYSIS,
                parameters={"time_range": "30d", "include_peer_details": True},
                schedule="0 10 1 * *",  # Monthly on 1st at 10 AM
                recipients=["network@company.com"]
            ),
            ReportDefinition(
                report_id="alert_summary",
                name="Alert Summary Report",
                description="Summary of all alerts and their resolution status",
                report_type=ReportType.ALERT_SUMMARY,
                parameters={"time_range": "7d", "include_resolved": True},
                schedule="0 8 * * *",  # Daily at 8 AM
                recipients=["ops@company.com", "management@company.com"]
            )
        ]

        for report in default_reports:
            self.report_definitions[report.report_id] = report
            self._save_report_definition(report)

    def _save_report_definition(self, report: ReportDefinition):
        """Save report definition to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO report_definitions
            (report_id, name, description, report_type, parameters, schedule,
             recipients, created_at, last_run, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.report_id,
            report.name,
            report.description,
            report.report_type.value,
            json.dumps(report.parameters),
            report.schedule,
            json.dumps(report.recipients),
            report.created_at.isoformat(),
            report.last_run.isoformat() if report.last_run else None,
            report.enabled
        ))

        conn.commit()
        conn.close()

    async def generate_report(self,
                            report_id: str,
                            format: ReportFormat = ReportFormat.JSON,
                            parameters: Optional[Dict[str, Any]] = None) -> ReportExecution:
        """Generate a report"""
        if report_id not in self.report_definitions:
            raise ValueError(f"Report definition not found: {report_id}")

        report_def = self.report_definitions[report_id]
        execution_id = f"exec_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Merge parameters
        merged_params = report_def.parameters.copy()
        if parameters:
            merged_params.update(parameters)

        execution = ReportExecution(
            execution_id=execution_id,
            report_id=report_id,
            status='running',
            start_time=datetime.now(),
            parameters=merged_params,
            format=format
        )

        self.active_executions[execution_id] = execution
        self._save_execution(execution)

        try:
            logger.info(f"Starting report generation: {execution_id}")

            # Generate report data
            report_data = await self._generate_report_data(report_def, merged_params)

            # Export to requested format
            output_file = await self._export_report(
                report_data, format, report_def, execution_id
            )

            # Update execution
            execution.status = 'completed'
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            execution.output_file = output_file

            # Update report definition
            report_def.last_run = execution.end_time

            logger.info(f"Report generation completed: {execution_id}")

        except Exception as e:
            execution.status = 'failed'
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            execution.error_message = str(e)
            logger.error(f"Report generation failed: {execution_id} - {e}")

        # Save final execution state
        self._save_execution(execution)
        self._save_report_definition(report_def)

        # Remove from active executions
        if execution_id in self.active_executions:
            del self.active_executions[execution_id]

        return execution

    async def _generate_report_data(self,
                                  report_def: ReportDefinition,
                                  parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report data based on report type"""
        report_type = report_def.report_type

        if report_type == ReportType.DEPLOYMENT_SUMMARY:
            return await self._generate_deployment_summary(parameters)
        elif report_type == ReportType.DEVICE_HEALTH:
            return await self._generate_device_health_report(parameters)
        elif report_type == ReportType.BGP_ANALYSIS:
            return await self._generate_bgp_analysis(parameters)
        elif report_type == ReportType.ALERT_SUMMARY:
            return await self._generate_alert_summary(parameters)
        elif report_type == ReportType.PERFORMANCE_TRENDS:
            return await self._generate_performance_trends(parameters)
        else:
            raise ValueError(f"Unsupported report type: {report_type}")

    async def _generate_deployment_summary(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate deployment summary report"""
        time_range = parameters.get('time_range', '24h')
        include_details = parameters.get('include_details', False)

        # Calculate time range
        end_time = datetime.now()
        if time_range == '24h':
            start_time = end_time - timedelta(hours=24)
        elif time_range == '7d':
            start_time = end_time - timedelta(days=7)
        elif time_range == '30d':
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=24)

        # Query deployment data (mock implementation)
        deployments = await self._get_deployment_data(start_time, end_time)

        # Calculate statistics
        total_deployments = len(deployments)
        successful_deployments = len([d for d in deployments if d['status'] == 'success'])
        failed_deployments = total_deployments - successful_deployments
        success_rate = (successful_deployments / total_deployments * 100) if total_deployments > 0 else 0

        # Group by device
        device_stats = {}
        for deployment in deployments:
            device_id = deployment['device_id']
            if device_id not in device_stats:
                device_stats[device_id] = {'total': 0, 'success': 0, 'failed': 0}
            device_stats[device_id]['total'] += 1
            if deployment['status'] == 'success':
                device_stats[device_id]['success'] += 1
            else:
                device_stats[device_id]['failed'] += 1

        return {
            'report_type': 'deployment_summary',
            'time_range': time_range,
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'summary': {
                'total_deployments': total_deployments,
                'successful_deployments': successful_deployments,
                'failed_deployments': failed_deployments,
                'success_rate': round(success_rate, 2)
            },
            'device_statistics': device_stats,
            'deployments': deployments if include_details else [],
            'generated_at': datetime.now().isoformat()
        }

    async def _generate_device_health_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate device health report"""
        time_range = parameters.get('time_range', '7d')
        include_charts = parameters.get('include_charts', False)

        # Get device health data
        devices = await self._get_device_health_data()

        # Calculate health scores
        device_scores = []
        for device in devices:
            score = self._calculate_health_score(device)
            device_scores.append({
                'device_id': device['device_id'],
                'hostname': device['hostname'],
                'health_score': score,
                'cpu_avg': device['cpu_avg'],
                'memory_avg': device['memory_avg'],
                'interface_issues': device['interface_issues'],
                'bgp_issues': device['bgp_issues']
            })

        # Sort by health score
        device_scores.sort(key=lambda x: x['health_score'], reverse=True)

        # Overall statistics
        avg_score = sum(d['health_score'] for d in device_scores) / len(device_scores) if device_scores else 0
        healthy_devices = len([d for d in device_scores if d['health_score'] >= 80])
        critical_devices = len([d for d in device_scores if d['health_score'] < 50])

        report_data = {
            'report_type': 'device_health',
            'time_range': time_range,
            'summary': {
                'total_devices': len(device_scores),
                'average_health_score': round(avg_score, 2),
                'healthy_devices': healthy_devices,
                'critical_devices': critical_devices
            },
            'device_scores': device_scores,
            'generated_at': datetime.now().isoformat()
        }

        # Add chart data if requested
        if include_charts and MATPLOTLIB_AVAILABLE:
            report_data['charts'] = await self._generate_health_charts(device_scores)

        return report_data

    async def _generate_bgp_analysis(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate BGP analysis report"""
        time_range = parameters.get('time_range', '30d')
        include_peer_details = parameters.get('include_peer_details', False)

        # Get BGP data
        bgp_data = await self._get_bgp_analysis_data()

        # Calculate statistics
        total_peers = sum(len(device['peers']) for device in bgp_data)
        established_peers = sum(
            len([p for p in device['peers'] if p['state'] == 'Established'])
            for device in bgp_data
        )

        # Calculate uptime percentages
        peer_uptime = []
        for device in bgp_data:
            for peer in device['peers']:
                uptime_percent = (peer['uptime_seconds'] / (30 * 24 * 3600)) * 100  # Assume 30-day period
                peer_uptime.append(min(uptime_percent, 100))

        avg_uptime = sum(peer_uptime) / len(peer_uptime) if peer_uptime else 0

        # Group by peer AS
        peer_as_stats = {}
        for device in bgp_data:
            for peer in device['peers']:
                peer_as = peer['peer_as']
                if peer_as not in peer_as_stats:
                    peer_as_stats[peer_as] = {'peer_count': 0, 'established_count': 0}
                peer_as_stats[peer_as]['peer_count'] += 1
                if peer['state'] == 'Established':
                    peer_as_stats[peer_as]['established_count'] += 1

        return {
            'report_type': 'bgp_analysis',
            'time_range': time_range,
            'summary': {
                'total_devices': len(bgp_data),
                'total_peers': total_peers,
                'established_peers': established_peers,
                'peer_availability': round((established_peers / total_peers * 100), 2) if total_peers > 0 else 0,
                'average_uptime_percentage': round(avg_uptime, 2)
            },
            'peer_as_statistics': peer_as_stats,
            'device_bgp_data': bgp_data if include_peer_details else [],
            'generated_at': datetime.now().isoformat()
        }

    async def _generate_alert_summary(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate alert summary report"""
        time_range = parameters.get('time_range', '7d')
        include_resolved = parameters.get('include_resolved', False)

        # Get alert data
        alerts = await self._get_alert_data(include_resolved)

        # Calculate statistics
        total_alerts = len(alerts)
        critical_alerts = len([a for a in alerts if a['severity'] == 'critical'])
        warning_alerts = len([a for a in alerts if a['severity'] == 'warning'])
        acknowledged_alerts = len([a for a in alerts if a['acknowledged']])

        # Group by alert type
        alert_types = {}
        for alert in alerts:
            alert_type = alert['metric_type']
            if alert_type not in alert_types:
                alert_types[alert_type] = 0
            alert_types[alert_type] += 1

        # Group by device
        device_alerts = {}
        for alert in alerts:
            device_id = alert['device_id']
            if device_id not in device_alerts:
                device_alerts[device_id] = 0
            device_alerts[device_id] += 1

        return {
            'report_type': 'alert_summary',
            'time_range': time_range,
            'summary': {
                'total_alerts': total_alerts,
                'critical_alerts': critical_alerts,
                'warning_alerts': warning_alerts,
                'acknowledged_alerts': acknowledged_alerts,
                'unacknowledged_alerts': total_alerts - acknowledged_alerts
            },
            'alert_types': alert_types,
            'device_alert_counts': device_alerts,
            'recent_alerts': alerts[:50],  # Last 50 alerts
            'generated_at': datetime.now().isoformat()
        }

    async def _generate_performance_trends(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance trends report"""
        time_range = parameters.get('time_range', '30d')
        metrics = parameters.get('metrics', ['cpu', 'memory', 'interface_errors'])

        # Get trend data
        trend_data = await self._get_performance_trend_data(metrics, time_range)

        return {
            'report_type': 'performance_trends',
            'time_range': time_range,
            'metrics': metrics,
            'trend_data': trend_data,
            'generated_at': datetime.now().isoformat()
        }

    async def _export_report(self,
                           report_data: Dict[str, Any],
                           format: ReportFormat,
                           report_def: ReportDefinition,
                           execution_id: str) -> str:
        """Export report to specified format"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{report_def.report_id}_{timestamp}.{format.value}"
        filepath = self.output_dir / filename

        if format == ReportFormat.JSON:
            with open(filepath, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

        elif format == ReportFormat.CSV:
            await self._export_to_csv(report_data, filepath)

        elif format == ReportFormat.HTML:
            await self._export_to_html(report_data, filepath, report_def)

        elif format == ReportFormat.PDF:
            if REPORTLAB_AVAILABLE:
                await self._export_to_pdf(report_data, filepath, report_def)
            else:
                raise ValueError("PDF export not available - ReportLab not installed")

        else:
            raise ValueError(f"Unsupported export format: {format}")

        return str(filepath)

    async def _export_to_csv(self, report_data: Dict[str, Any], filepath: Path):
        """Export report to CSV format"""
        # This is a simplified CSV export - real implementation would be more sophisticated
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Write summary
            if 'summary' in report_data:
                writer.writerow(['Summary'])
                for key, value in report_data['summary'].items():
                    writer.writerow([key, value])
                writer.writerow([])

            # Write main data
            for key, value in report_data.items():
                if key not in ['summary', 'generated_at'] and isinstance(value, list):
                    writer.writerow([key])
                    if value and isinstance(value[0], dict):
                        # Write headers
                        headers = list(value[0].keys())
                        writer.writerow(headers)
                        # Write data
                        for item in value:
                            writer.writerow([str(item.get(h, '')) for h in headers])
                    writer.writerow([])

    async def _export_to_html(self,
                            report_data: Dict[str, Any],
                            filepath: Path,
                            report_def: ReportDefinition):
        """Export report to HTML format"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{report_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .critical {{ color: #d32f2f; }}
        .warning {{ color: #f57c00; }}
        .success {{ color: #388e3c; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report_name}</h1>
        <p>{report_description}</p>
        <p>Generated: {generated_time}</p>
    </div>

    <div class="summary">
        <h2>Summary</h2>
        {summary_table}
    </div>

    <div class="details">
        <h2>Details</h2>
        {details_section}
    </div>
</body>
</html>
        """

        # Generate summary table
        summary_html = ""
        if 'summary' in report_data:
            summary_html = "<table>"
            for key, value in report_data['summary'].items():
                summary_html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
            summary_html += "</table>"

        # Generate details section
        details_html = "<pre>" + json.dumps(report_data, indent=2, default=str) + "</pre>"

        # Format HTML
        html_content = html_template.format(
            report_name=report_def.name,
            report_description=report_def.description,
            generated_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            summary_table=summary_html,
            details_section=details_html
        )

        with open(filepath, 'w') as f:
            f.write(html_content)

    async def _export_to_pdf(self,
                           report_data: Dict[str, Any],
                           filepath: Path,
                           report_def: ReportDefinition):
        """Export report to PDF format"""
        doc = SimpleDocTemplate(str(filepath), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30
        )
        story.append(Paragraph(report_def.name, title_style))

        # Description
        story.append(Paragraph(f"<b>Description:</b> {report_def.description}", styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))

        # Summary
        if 'summary' in report_data:
            story.append(Paragraph("Summary", styles['Heading2']))

            summary_data = []
            for key, value in report_data['summary'].items():
                summary_data.append([key, str(value)])

            summary_table = Table(summary_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 20))

        # Add note about full data availability
        story.append(Paragraph("Full report data is available in JSON format.", styles['Normal']))
        story.append(Paragraph(f"Report Type: {report_data.get('report_type', 'Unknown')}", styles['Normal']))

        doc.build(story)

    # Mock data generation methods (would connect to real databases)
    async def _get_deployment_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Mock deployment data generation"""
        import random
        from datetime import timedelta

        deployments = []
        current_time = start_time

        while current_time < end_time:
            num_deployments = random.randint(0, 5)
            for _ in range(num_deployments):
                deployment = {
                    'deployment_id': f"deploy_{current_time.strftime('%Y%m%d%H%M')}_{random.randint(1000, 9999)}",
                    'device_id': f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}",
                    'timestamp': current_time.isoformat(),
                    'status': random.choice(['success', 'success', 'success', 'failed']),  # 75% success rate
                    'duration': random.uniform(5, 120),
                    'config_type': random.choice(['interface', 'bgp', 'system', 'security'])
                }
                deployments.append(deployment)

            current_time += timedelta(hours=random.randint(1, 6))

        return deployments

    async def _get_device_health_data(self) -> List[Dict[str, Any]]:
        """Mock device health data generation"""
        import random
        devices = []
        for i in range(10):
            device = {
                'device_id': f"192.168.1.{i+1}",
                'hostname': f"device-{i+1}",
                'cpu_avg': random.uniform(10, 80),
                'memory_avg': random.uniform(20, 90),
                'interface_issues': random.randint(0, 5),
                'bgp_issues': random.randint(0, 3),
                'uptime_percentage': random.uniform(85, 100)
            }
            devices.append(device)

        return devices

    def _calculate_health_score(self, device: Dict[str, Any]) -> float:
        """Calculate device health score"""
        cpu_score = max(0, 100 - device['cpu_avg'])
        memory_score = max(0, 100 - device['memory_avg'])
        interface_score = max(0, 100 - (device['interface_issues'] * 20))
        bgp_score = max(0, 100 - (device['bgp_issues'] * 25))

        # Weighted average
        health_score = (cpu_score * 0.3 + memory_score * 0.3 + interface_score * 0.2 + bgp_score * 0.2)
        return round(health_score, 2)

    async def _generate_health_charts(self, device_scores: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate health score charts"""
        if not MATPLOTLIB_AVAILABLE:
            return {}

        try:
            # Create health score distribution chart
            plt.figure(figsize=(10, 6))
            scores = [d['health_score'] for d in device_scores]
            plt.hist(scores, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
            plt.title('Device Health Score Distribution')
            plt.xlabel('Health Score')
            plt.ylabel('Number of Devices')
            plt.grid(True, alpha=0.3)

            # Convert to base64 for embedding
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()

            return {
                'health_distribution': f"data:image/png;base64,{chart_base64}"
            }

        except Exception as e:
            logger.error(f"Failed to generate charts: {e}")
            return {}

    async def _get_bgp_analysis_data(self) -> List[Dict[str, Any]]:
        """Mock BGP analysis data generation"""
        import random
        devices = []
        for i in range(8):
            peers = []
            for j in range(random.randint(2, 6)):
                peer = {
                    'peer_address': f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}",
                    'peer_as': random.choice([65001, 65002, 65003, 65100]),
                    'state': random.choice(['Established', 'Established', 'Active']),  # 66% established
                    'uptime_seconds': random.randint(3600, 30 * 24 * 3600),
                    'received_routes': random.randint(100, 10000)
                }
                peers.append(peer)

            device = {
                'device_id': f"192.168.{i+1}.1",
                'hostname': f"router-{i+1}",
                'peers': peers
            }
            devices.append(device)

        return devices

    async def _get_alert_data(self, include_resolved: bool = False) -> List[Dict[str, Any]]:
        """Mock alert data generation"""
        import random
        alerts = []
        for i in range(50):
            alert = {
                'alert_id': f"alert_{i+1:03d}",
                'device_id': f"192.168.{random.randint(1, 10)}.1",
                'metric_type': random.choice(['interface', 'bgp', 'system']),
                'severity': random.choice(['critical', 'warning', 'info']),
                'title': f"Alert {i+1}",
                'message': f"This is alert number {i+1}",
                'timestamp': (datetime.now() - timedelta(hours=random.randint(0, 168))).isoformat(),
                'acknowledged': random.choice([True, False])
            }
            alerts.append(alert)

        return alerts

    async def _get_performance_trend_data(self, metrics: List[str], time_range: str) -> Dict[str, Any]:
        """Mock performance trend data"""
        trend_data = {}
        for metric in metrics:
            trend_data[metric] = {
                'data_points': [
                    {
                        'timestamp': (datetime.now() - timedelta(hours=i*6)).isoformat(),
                        'value': random.uniform(10, 90)
                    }
                    for i in range(40)  # 40 data points over 10 days
                ]
            }

        return trend_data

    def _save_execution(self, execution: ReportExecution):
        """Save execution record to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO report_executions
            (execution_id, report_id, status, start_time, end_time, duration,
             output_file, format, parameters, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            execution.execution_id,
            execution.report_id,
            execution.status,
            execution.start_time.isoformat(),
            execution.end_time.isoformat() if execution.end_time else None,
            execution.duration,
            execution.output_file,
            execution.format.value,
            json.dumps(execution.parameters),
            execution.error_message
        ))

        conn.commit()
        conn.close()

    def get_report_definitions(self) -> List[ReportDefinition]:
        """Get all report definitions"""
        return list(self.report_definitions.values())

    def get_execution_history(self, report_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get report execution history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if report_id:
            cursor.execute('''
                SELECT * FROM report_executions
                WHERE report_id = ?
                ORDER BY start_time DESC
                LIMIT ?
            ''', (report_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM report_executions
                ORDER BY start_time DESC
                LIMIT ?
            ''', (limit,))

        executions = []
        for row in cursor.fetchall():
            execution = {
                'execution_id': row[0],
                'report_id': row[1],
                'status': row[2],
                'start_time': row[3],
                'end_time': row[4],
                'duration': row[5],
                'output_file': row[6],
                'format': row[7],
                'parameters': json.loads(row[8]) if row[8] else {},
                'error_message': row[9]
            }
            executions.append(execution)

        conn.close()
        return executions

    def get_active_executions(self) -> List[ReportExecution]:
        """Get currently active report executions"""
        return list(self.active_executions.values())

    def create_custom_report(self,
                           name: str,
                           description: str,
                           report_type: ReportType,
                           parameters: Dict[str, Any]) -> ReportDefinition:
        """Create a custom report definition"""
        report_id = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        report_def = ReportDefinition(
            report_id=report_id,
            name=name,
            description=description,
            report_type=report_type,
            parameters=parameters
        )

        self.report_definitions[report_id] = report_def
        self._save_report_definition(report_def)

        logger.info(f"Created custom report: {report_id}")
        return report_def

    def delete_report(self, report_id: str) -> bool:
        """Delete a report definition"""
        if report_id in self.report_definitions:
            del self.report_definitions[report_id]

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM report_definitions WHERE report_id = ?', (report_id,))
            cursor.execute('DELETE FROM report_executions WHERE report_id = ?', (report_id,))
            conn.commit()
            conn.close()

            logger.info(f"Deleted report: {report_id}")
            return True

        return False