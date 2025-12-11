"""
Reporting API Endpoints

REST API endpoints for report generation, scheduling, and management.
Provides comprehensive reporting and analytics capabilities.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Import Phase 3 services
from phase3.services.reporting_service import (
    ReportingService, ReportDefinition, ReportExecution, ReportType, ReportFormat
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/reports", tags=["reports"])

# Global service instance (in production, would use dependency injection)
reporting_service = ReportingService()

# Pydantic models for API
class ReportGenerationRequest(BaseModel):
    """Request model for report generation"""
    report_id: str = Field(..., description="Report definition ID")
    format: ReportFormat = Field(ReportFormat.JSON, description="Export format")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")


class CustomReportRequest(BaseModel):
    """Request model for custom report creation"""
    name: str = Field(..., description="Report name")
    description: str = Field(..., description="Report description")
    report_type: ReportType = Field(..., description="Report type")
    parameters: Dict[str, Any] = Field(..., description="Report parameters")


class ReportDefinitionResponse(BaseModel):
    """Response model for report definition"""
    report_id: str
    name: str
    description: str
    report_type: str
    parameters: Dict[str, Any]
    schedule: Optional[str] = None
    recipients: List[str] = []
    created_at: datetime
    last_run: Optional[datetime] = None
    enabled: bool = True


class ReportExecutionResponse(BaseModel):
    """Response model for report execution"""
    execution_id: str
    report_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    output_file: Optional[str] = None
    format: str
    parameters: Dict[str, Any] = {}
    error_message: Optional[str] = None


# Background task for report generation
async def generate_report_background(report_request: ReportGenerationRequest):
    """Background task to generate report"""
    try:
        execution = await reporting_service.generate_report(
            report_id=report_request.report_id,
            format=report_request.format,
            parameters=report_request.parameters
        )
        logger.info(f"Background report generation completed: {execution.execution_id}")
        return execution
    except Exception as e:
        logger.error(f"Background report generation failed: {e}")
        raise


@router.get("/definitions", response_model=List[ReportDefinitionResponse])
async def get_report_definitions():
    """Get all available report definitions"""
    try:
        definitions = reporting_service.get_report_definitions()

        response = []
        for definition in definitions:
            def_response = ReportDefinitionResponse(
                report_id=definition.report_id,
                name=definition.name,
                description=definition.description,
                report_type=definition.report_type.value,
                parameters=definition.parameters,
                schedule=definition.schedule,
                recipients=definition.recipients,
                created_at=definition.created_at,
                last_run=definition.last_run,
                enabled=definition.enabled
            )
            response.append(def_response)

        return response

    except Exception as e:
        logger.error(f"Failed to get report definitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=ReportExecutionResponse)
async def generate_report(request: ReportGenerationRequest, background_tasks: BackgroundTasks):
    """Generate a report (runs in background)"""
    try:
        # Check if report definition exists
        definitions = reporting_service.get_report_definitions()
        report_def = next((d for d in definitions if d.report_id == request.report_id), None)

        if not report_def:
            raise HTTPException(
                status_code=404,
                detail=f"Report definition {request.report_id} not found"
            )

        # Start report generation in background
        background_tasks.add_task(generate_report_background, request)

        # Return immediate response
        return ReportExecutionResponse(
            execution_id="pending",
            report_id=request.report_id,
            status="running",
            start_time=datetime.now(),
            format=request.format.value,
            parameters=request.parameters or {}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions", response_model=List[ReportExecutionResponse])
async def get_execution_history(
    report_id: Optional[str] = Query(None, description="Filter by report ID"),
    limit: int = Query(50, description="Maximum number of executions to return")
):
    """Get report execution history"""
    try:
        history = reporting_service.get_execution_history(report_id=report_id, limit=limit)

        response = []
        for execution in history:
            exec_response = ReportExecutionResponse(
                execution_id=execution['execution_id'],
                report_id=execution['report_id'],
                status=execution['status'],
                start_time=datetime.fromisoformat(execution['start_time']),
                end_time=datetime.fromisoformat(execution['end_time']) if execution['end_time'] else None,
                duration=execution['duration'],
                output_file=execution['output_file'],
                format=execution['format'],
                parameters=execution['parameters'],
                error_message=execution['error_message']
            )
            response.append(exec_response)

        return response

    except Exception as e:
        logger.error(f"Failed to get execution history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}/download")
async def download_report(execution_id: str):
    """Download a generated report file"""
    try:
        history = reporting_service.get_execution_history(limit=1000)
        execution = next((e for e in history if e['execution_id'] == execution_id), None)

        if not execution:
            raise HTTPException(
                status_code=404,
                detail=f"Execution {execution_id} not found"
            )

        if not execution['output_file']:
            raise HTTPException(
                status_code=404,
                detail="No output file available for this execution"
            )

        # Return the file
        return FileResponse(
            execution['output_file'],
            filename=f"report_{execution_id}.{execution['format']}",
            media_type="application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/{execution_id}")
async def get_execution_details(execution_id: str):
    """Get detailed information about a specific execution"""
    try:
        history = reporting_service.get_execution_history(limit=1000)
        execution = next((e for e in history if e['execution_id'] == execution_id), None)

        if not execution:
            raise HTTPException(
                status_code=404,
                detail=f"Execution {execution_id} not found"
            )

        # Get report definition details
        definitions = reporting_service.get_report_definitions()
        report_def = next(
            (d for d in definitions if d.report_id == execution['report_id']),
            None
        )

        return {
            "execution": execution,
            "report_definition": {
                "report_id": report_def.report_id,
                "name": report_def.name,
                "description": report_def.description,
                "report_type": report_def.report_type.value
            } if report_def else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_executions():
    """Get currently running report executions"""
    try:
        active_executions = reporting_service.get_active_executions()

        response = []
        for execution in active_executions:
            exec_response = ReportExecutionResponse(
                execution_id=execution.execution_id,
                report_id=execution.report_id,
                status=execution.status,
                start_time=execution.start_time,
                format=execution.format.value,
                parameters=execution.parameters
            )
            response.append(exec_response)

        return response

    except Exception as e:
        logger.error(f"Failed to get active executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom", response_model=ReportDefinitionResponse)
async def create_custom_report(request: CustomReportRequest):
    """Create a custom report definition"""
    try:
        report_def = reporting_service.create_custom_report(
            name=request.name,
            description=request.description,
            report_type=request.report_type,
            parameters=request.parameters
        )

        return ReportDefinitionResponse(
            report_id=report_def.report_id,
            name=report_def.name,
            description=report_def.description,
            report_type=report_def.report_type.value,
            parameters=report_def.parameters,
            schedule=report_def.schedule,
            recipients=report_def.recipients,
            created_at=report_def.created_at,
            last_run=report_def.last_run,
            enabled=report_def.enabled
        )

    except Exception as e:
        logger.error(f"Failed to create custom report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/definitions/{report_id}")
async def delete_report_definition(report_id: str):
    """Delete a report definition"""
    try:
        success = reporting_service.delete_report(report_id)

        if success:
            return {
                "status": "success",
                "message": f"Report definition {report_id} deleted"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Report definition {report_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete report definition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_report_types():
    """Get available report types"""
    try:
        return {
            "report_types": [
                {
                    "value": ReportType.DEPLOYMENT_SUMMARY,
                    "label": "Deployment Summary",
                    "description": "Summary of configuration deployments"
                },
                {
                    "value": ReportType.DEVICE_HEALTH,
                    "label": "Device Health",
                    "description": "Device health and performance metrics"
                },
                {
                    "value": ReportType.BGP_ANALYSIS,
                    "label": "BGP Analysis",
                    "description": "BGP session analysis and stability"
                },
                {
                    "value": ReportType.ALERT_SUMMARY,
                    "label": "Alert Summary",
                    "description": "Summary of alerts and their status"
                },
                {
                    "value": ReportType.PERFORMANCE_TRENDS,
                    "label": "Performance Trends",
                    "description": "Performance metrics over time"
                },
                {
                    "value": ReportType.COMPLIANCE_AUDIT,
                    "label": "Compliance Audit",
                    "description": "Configuration compliance reports"
                },
                {
                    "value": ReportType.TOPOLOGY_ANALYSIS,
                    "label": "Topology Analysis",
                    "description": "Network topology and connectivity analysis"
                }
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get report types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/formats")
async def get_export_formats():
    """Get available export formats"""
    try:
        return {
            "formats": [
                {
                    "value": ReportFormat.JSON,
                    "label": "JSON",
                    "description": "Machine-readable JSON format"
                },
                {
                    "value": ReportFormat.CSV,
                    "label": "CSV",
                    "description": "Comma-separated values for spreadsheet import"
                },
                {
                    "value": ReportFormat.HTML,
                    "label": "HTML",
                    "description": "Interactive HTML report"
                },
                {
                    "value": ReportFormat.PDF,
                    "label": "PDF",
                    "description": "Printable PDF document"
                }
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get export formats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_reports_dashboard():
    """Get dashboard summary of reports"""
    try:
        # Get recent executions
        recent_executions = reporting_service.get_execution_history(limit=10)

        # Get all definitions
        definitions = reporting_service.get_report_definitions()

        # Calculate statistics
        total_reports = len(definitions)
        active_reports = len([d for d in definitions if d.enabled])
        recent_executions_count = len(recent_executions)

        # Status breakdown of recent executions
        status_counts = {}
        for execution in recent_executions:
            status = execution['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        # Most recent successful executions
        successful_executions = [
            e for e in recent_executions if e['status'] == 'completed'
        ][:5]

        # Currently running executions
        active_executions = reporting_service.get_active_executions()

        return {
            "summary": {
                "total_reports": total_reports,
                "active_reports": active_reports,
                "recent_executions": recent_executions_count,
                "running_executions": len(active_executions)
            },
            "execution_status_breakdown": status_counts,
            "recent_successful_executions": successful_executions,
            "active_executions": [
                {
                    "execution_id": exec.execution_id,
                    "report_id": exec.report_id,
                    "status": exec.status,
                    "start_time": exec.start_time.isoformat(),
                    "duration": (datetime.now() - exec.start_time).total_seconds()
                }
                for exec in active_executions
            ],
            "report_types": list(set(d.report_type.value for d in definitions))
        }

    except Exception as e:
        logger.error(f"Failed to get reports dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{report_id}")
async def preview_report_data(report_id: str, parameters: Optional[str] = None):
    """Preview report data without generating full report"""
    try:
        # Parse parameters if provided
        report_params = {}
        if parameters:
            import json
            report_params = json.loads(parameters)

        # Get report definition
        definitions = reporting_service.get_report_definitions()
        report_def = next((d for d in definitions if d.report_id == report_id), None)

        if not report_def:
            raise HTTPException(
                status_code=404,
                detail=f"Report definition {report_id} not found"
            )

        # Generate preview data (limited scope)
        preview_params = report_def.parameters.copy()
        preview_params.update(report_params)
        preview_params['preview_mode'] = True
        preview_params['limit'] = 10  # Limit data for preview

        # This would generate a smaller version of the report
        # For now, return mock preview data
        return {
            "report_id": report_id,
            "report_name": report_def.name,
            "report_type": report_def.report_type.value,
            "preview_data": {
                "sample_records": 10,
                "estimated_total_records": 150,
                "columns": ["timestamp", "device_id", "status", "metric"],
                "sample_rows": [
                    {"timestamp": "2024-01-15T10:00:00", "device_id": "192.168.1.1", "status": "success", "metric": "cpu"},
                    {"timestamp": "2024-01-15T10:05:00", "device_id": "192.168.1.2", "status": "warning", "metric": "memory"},
                ]
            },
            "parameters_used": preview_params
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preview report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function to get reporting service (for dependency injection)
def get_reporting_service() -> ReportingService:
    """Dependency injection for reporting service"""
    return reporting_service