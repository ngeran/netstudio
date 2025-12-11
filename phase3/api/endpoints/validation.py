"""
JSNAPy Validation API Endpoints

REST API endpoints for configuration validation using JSNAPy.
Provides pre/post deployment validation and test management.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

# Import Phase 3 services
from phase3.services.jsnapy_service import JSNAPyService, ValidationSuite, ValidationResult

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/validation", tags=["validation"])

# Global service instance (in production, would use dependency injection)
validation_service = JSNAPyService()


# Pydantic models for API
class ValidationTestRequest(BaseModel):
    """Request model for running validation tests"""
    device_info: Dict[str, Any] = Field(..., description="Device connection information")
    snapshot_name: str = Field(..., description="Snapshot name for pre/post validation")
    test_cases: List[str] = Field(..., description="List of test case names to run")


class ValidationSuiteRequest(BaseModel):
    """Request model for creating validation suite"""
    name: str = Field(..., description="Suite name")
    description: str = Field(..., description="Suite description")
    test_cases: List[str] = Field(..., description="List of test case names")
    devices: List[Dict[str, Any]] = Field(..., description="List of devices to test")


class PreSnapshotRequest(BaseModel):
    """Request model for creating pre-deployment snapshot"""
    device_info: Dict[str, Any] = Field(..., description="Device connection information")
    snapshot_name: str = Field(..., description="Snapshot name")


class PostSnapshotRequest(BaseModel):
    """Request model for creating post-deployment snapshot"""
    device_info: Dict[str, Any] = Field(..., description="Device connection information")
    snapshot_name: str = Field(..., description="Snapshot name")


class TestResponse(BaseModel):
    """Response model for validation test results"""
    test_name: str
    status: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime


class ValidationSuiteResponse(BaseModel):
    """Response model for validation suite"""
    suite_id: str
    name: str
    description: str
    overall_status: str
    execution_time: float
    test_count: int
    results: List[TestResponse]
    created_at: datetime


# Background task for running validation suites
async def run_validation_suite_background(suite_request: ValidationSuiteRequest):
    """Background task to run validation suite"""
    try:
        suite = await validation_service.create_validation_suite(
            name=suite_request.name,
            description=suite_request.description,
            test_cases=suite_request.test_cases,
            devices=suite_request.devices
        )
        logger.info(f"Background validation suite completed: {suite.suite_id}")
        return suite
    except Exception as e:
        logger.error(f"Background validation suite failed: {e}")
        raise


@router.get("/test-cases", response_model=List[str])
async def get_available_test_cases():
    """Get list of available test case files"""
    try:
        test_cases = validation_service.get_available_test_cases()
        return test_cases
    except Exception as e:
        logger.error(f"Failed to get test cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/pre")
async def create_pre_snapshot(request: PreSnapshotRequest):
    """Create pre-deployment snapshot"""
    try:
        success = await validation_service.create_pre_snapshot(
            device_info=request.device_info,
            snapshot_name=request.snapshot_name
        )

        if success:
            return {
                "status": "success",
                "message": f"Pre snapshot created: {request.snapshot_name}",
                "snapshot_name": request.snapshot_name
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to create pre snapshot"
            )

    except Exception as e:
        logger.error(f"Failed to create pre snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/post")
async def create_post_snapshot(request: PostSnapshotRequest):
    """Create post-deployment snapshot"""
    try:
        success = await validation_service.create_post_snapshot(
            device_info=request.device_info,
            snapshot_name=request.snapshot_name
        )

        if success:
            return {
                "status": "success",
                "message": f"Post snapshot created: {request.snapshot_name}",
                "snapshot_name": request.snapshot_name
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to create post snapshot"
            )

    except Exception as e:
        logger.error(f"Failed to create post snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=List[TestResponse])
async def run_validation_tests(request: ValidationTestRequest):
    """Run validation tests against snapshots"""
    try:
        results = await validation_service.run_validation_tests(
            device_info=request.device_info,
            snapshot_name=request.snapshot_name,
            test_cases=request.test_cases
        )

        test_responses = []
        for result in results:
            test_response = TestResponse(
                test_name=result.test_name,
                status=result.status,
                message=result.message,
                details=result.details,
                timestamp=result.timestamp
            )
            test_responses.append(test_response)

        return test_responses

    except Exception as e:
        logger.error(f"Failed to run validation tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suite", response_model=ValidationSuiteResponse)
async def create_validation_suite(request: ValidationSuiteRequest, background_tasks: BackgroundTasks):
    """Create and execute a complete validation suite"""
    try:
        # Run validation suite in background
        background_tasks.add_task(
            run_validation_suite_background,
            request
        )

        # Return immediate response
        return ValidationSuiteResponse(
            suite_id="pending",
            name=request.name,
            description=request.description,
            overall_status="pending",
            execution_time=0.0,
            test_count=len(request.test_cases) * len(request.devices),
            results=[],
            created_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"Failed to create validation suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suite/{suite_id}/report")
async def get_validation_report(suite_id: str):
    """Generate detailed validation report for a suite"""
    try:
        report = await validation_service.generate_validation_report(suite_id)
        return report

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Validation suite {suite_id} not found"
        )
    except Exception as e:
        logger.error(f"Failed to generate validation report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_validation_history(limit: int = 50):
    """Get recent validation suite results"""
    try:
        history = validation_service.get_validation_history(limit=limit)
        return {"history": history, "total": len(history)}

    except Exception as e:
        logger.error(f"Failed to get validation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_validation_service_status():
    """Get validation service status and capabilities"""
    try:
        test_cases = validation_service.get_available_test_cases()
        history = validation_service.get_validation_history(limit=5)

        return {
            "service": "jsnapy_validation",
            "status": "active",
            "available_test_cases": len(test_cases),
            "recent_executions": len(history),
            "jsnapy_available": True,  # Would check actual JSNAPy availability
            "capabilities": {
                "pre_post_snapshots": True,
                "custom_test_cases": True,
                "suite_execution": True,
                "detailed_reports": True,
                "batch_validation": True
            }
        }

    except Exception as e:
        logger.error(f"Failed to get validation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function to get validation service (for dependency injection)
def get_validation_service() -> JSNAPyService:
    """Dependency injection for validation service"""
    return validation_service