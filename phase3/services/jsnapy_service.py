"""
JSNAPy Validation Service

Provides automated configuration validation using Juniper Snapshot Administrator.
Integrates with deployment workflow for pre/post validation.
"""

import asyncio
import logging
import yaml
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

try:
    from jnpr.junos import Device
    from jnpr.junos.utils.config import Config
    from jnpr.jsnapy import SnapAdmin, get_test_xml
    JSNAPY_AVAILABLE = True
except ImportError:
    JSNAPY_AVAILABLE = False
    logging.warning("JSNAPy not available, using mock implementation")

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Represents a validation result"""
    device_id: str
    test_name: str
    status: str  # 'pass', 'fail', 'error'
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    pre_snapshot: Optional[str] = None
    post_snapshot: Optional[str] = None


@dataclass
class ValidationSuite:
    """Represents a complete validation suite"""
    suite_id: str
    name: str
    description: str
    test_cases: List[str]
    devices: List[str]
    created_at: datetime
    results: List[ValidationResult]
    overall_status: str
    execution_time: float


class JSNAPyService:
    """JSNAPy validation service with mock support"""

    def __init__(self, config_dir: str = "phase3/templates/jsnapy"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir = self.config_dir / "snapshots"
        self.snapshots_dir.mkdir(exist_ok=True)
        self.test_cases_dir = self.config_dir / "test_cases"
        self.test_cases_dir.mkdir(exist_ok=True)

        # Initialize default test cases
        self._create_default_test_cases()

        if not JSNAPY_AVAILABLE:
            logger.warning("Running JSNAPy service in mock mode")

    def _create_default_test_cases(self):
        """Create default JSNAPy test case templates"""

        # Interface validation test case
        interface_test = {
            'tests': [
                {
                    'test_interface_operational': 'is_equal',
                    'args': {
                        'post_node': 'interface-information/physical-interface[name=\'ge-0/0/0\']/oper-status',
                        'pre_node': 'interface-information/physical-interface[name=\'ge-0/0/0\']/oper-status',
                        'test_op': 'eq'
                    },
                    'kwargs': {},
                    'id': 'Interface Operational Status'
                },
                {
                    'test_interface_admin_status': 'is_equal',
                    'args': {
                        'post_node': 'interface-information/physical-interface[name=\'ge-0/0/0\']/admin-status',
                        'pre_node': 'interface-information/physical-interface[name=\'ge-0/0/0\']/admin-status',
                        'test_op': 'eq'
                    },
                    'kwargs': {},
                    'id': 'Interface Admin Status'
                }
            ],
            'command': 'show interfaces extensive'
        }

        # BGP validation test case
        bgp_test = {
            'tests': [
                {
                    'test_bgp_neighbor_state': 'is_equal',
                    'args': {
                        'post_node': 'bgp-information/bgp-peer/peer-state',
                        'pre_node': 'bgp-information/bgp-peer/peer-state',
                        'test_op': 'eq'
                    },
                    'kwargs': {},
                    'id': 'BGP Neighbor State'
                },
                {
                    'test_bgp_session_count': 'no_diff',
                    'args': {
                        'pre_node': 'bgp-information/bgp-peer/peer-state',
                        'post_node': 'bgp-information/bgp-peer/peer-state',
                        'test_op': 'count'
                    },
                    'kwargs': {},
                    'id': 'BGP Session Count'
                }
            ],
            'command': 'show bgp summary'
        }

        # System validation test case
        system_test = {
            'tests': [
                {
                    'test_system_uptime': 'delta_percentage',
                    'args': {
                        'post_node': 'system-uptime-information/system-booted-time/time-length',
                        'pre_node': 'system-uptime-information/system-booted-time/time-length',
                        'test_op': 'delta',
                        'delta_percentage': 10
                    },
                    'kwargs': {},
                    'id': 'System Uptime (should not change significantly)'
                }
            ],
            'command': 'show system uptime'
        }

        # Save test cases
        with open(self.test_cases_dir / "interface_validation.yml", 'w') as f:
            yaml.dump(interface_test, f, default_flow_style=False)

        with open(self.test_cases_dir / "bgp_validation.yml", 'w') as f:
            yaml.dump(bgp_test, f, default_flow_style=False)

        with open(self.test_cases_dir / "system_validation.yml", 'w') as f:
            yaml.dump(system_test, f, default_flow_style=False)

    async def create_pre_snapshot(self, device_info: Dict[str, Any], snapshot_name: str) -> bool:
        """Create pre-deployment snapshot"""
        if JSNAPY_AVAILABLE:
            try:
                device = Device(
                    host=device_info['host_ip'],
                    user=device_info['username'],
                    password=device_info['password'],
                    gather_facts=False
                )

                device.open()
                logger.info(f"Connected to device {device_info['host_ip']}")

                # Create snapshot using JSNAPy
                snap_admin = SnapAdmin()

                config_data = {
                    'device': device_info['host_ip'],
                    'username': device_info['username'],
                    'password': device_info['password']
                }

                snapshot_file = str(self.snapshots_dir / f"{snapshot_name}_pre.xml")
                result = snap_admin.snap(data=config_data, file_name=snapshot_file)

                device.close()
                return result

            except Exception as e:
                logger.error(f"Failed to create pre snapshot for {device_info['host_ip']}: {e}")
                return False
        else:
            # Mock implementation
            mock_snapshot = {
                'device': device_info['host_ip'],
                'timestamp': datetime.now().isoformat(),
                'type': 'pre_deployment',
                'interfaces': {'ge-0/0/0': {'status': 'up', 'admin_status': 'up'}},
                'bgp': {'neighbors': 5, 'sessions_established': 4},
                'system': {'uptime': '30 days', 'load_average': '0.15, 0.12, 0.08'}
            }

            snapshot_file = self.snapshots_dir / f"{snapshot_name}_pre.json"
            with open(snapshot_file, 'w') as f:
                json.dump(mock_snapshot, f, indent=2)

            logger.info(f"Created mock pre snapshot: {snapshot_file}")
            return True

    async def create_post_snapshot(self, device_info: Dict[str, Any], snapshot_name: str) -> bool:
        """Create post-deployment snapshot"""
        if JSNAPY_AVAILABLE:
            try:
                device = Device(
                    host=device_info['host_ip'],
                    user=device_info['username'],
                    password=device_info['password'],
                    gather_facts=False
                )

                device.open()
                logger.info(f"Connected to device {device_info['host_ip']}")

                # Create snapshot using JSNAPy
                snap_admin = SnapAdmin()

                config_data = {
                    'device': device_info['host_ip'],
                    'username': device_info['username'],
                    'password': device_info['password']
                }

                snapshot_file = str(self.snapshots_dir / f"{snapshot_name}_post.xml")
                result = snap_admin.snap(data=config_data, file_name=snapshot_file)

                device.close()
                return result

            except Exception as e:
                logger.error(f"Failed to create post snapshot for {device_info['host_ip']}: {e}")
                return False
        else:
            # Mock implementation - simulate some changes
            mock_snapshot = {
                'device': device_info['host_ip'],
                'timestamp': datetime.now().isoformat(),
                'type': 'post_deployment',
                'interfaces': {'ge-0/0/0': {'status': 'up', 'admin_status': 'up'}},
                'bgp': {'neighbors': 5, 'sessions_established': 5},  # One new session
                'system': {'uptime': '30 days', 'load_average': '0.18, 0.14, 0.09'}
            }

            snapshot_file = self.snapshots_dir / f"{snapshot_name}_post.json"
            with open(snapshot_file, 'w') as f:
                json.dump(mock_snapshot, f, indent=2)

            logger.info(f"Created mock post snapshot: {snapshot_file}")
            return True

    async def run_validation_tests(self,
                                 device_info: Dict[str, Any],
                                 snapshot_name: str,
                                 test_cases: List[str]) -> List[ValidationResult]:
        """Run validation tests against pre/post snapshots"""
        results = []

        for test_case in test_cases:
            try:
                if JSNAPY_AVAILABLE:
                    # Real JSNAPy validation
                    result = await self._run_jsnapy_test(device_info, snapshot_name, test_case)
                else:
                    # Mock validation
                    result = await self._run_mock_validation(device_info, snapshot_name, test_case)

                results.append(result)

            except Exception as e:
                error_result = ValidationResult(
                    device_id=device_info['host_ip'],
                    test_name=test_case,
                    status='error',
                    message=f"Test execution failed: {str(e)}",
                    details={'error': str(e)},
                    timestamp=datetime.now(),
                    pre_snapshot=f"{snapshot_name}_pre",
                    post_snapshot=f"{snapshot_name}_post"
                )
                results.append(error_result)
                logger.error(f"Validation test failed for {test_case}: {e}")

        return results

    async def _run_jsnapy_test(self,
                              device_info: Dict[str, Any],
                              snapshot_name: str,
                              test_case: str) -> ValidationResult:
        """Run real JSNAPy test"""
        snap_admin = SnapAdmin()

        config_data = {
            'device': device_info['host_ip'],
            'username': device_info['username'],
            'password': device_info['password'],
            'test_file': str(self.test_cases_dir / f"{test_case}.yml"),
            'pre_file': str(self.snapshots_dir / f"{snapshot_name}_pre.xml"),
            'post_file': str(self.snapshots_dir / f"{snapshot_name}_post.xml")
        }

        # Run JSNAPy test
        test_results = snap_admin.check(data=config_data)

        # Parse results
        overall_status = 'pass' if all(test.get('result') == 'pass' for test in test_results) else 'fail'

        return ValidationResult(
            device_id=device_info['host_ip'],
            test_name=test_case,
            status=overall_status,
            message=f"JSNAPy test completed with {len(test_results)} checks",
            details={'test_results': test_results},
            timestamp=datetime.now(),
            pre_snapshot=f"{snapshot_name}_pre",
            post_snapshot=f"{snapshot_name}_post"
        )

    async def _run_mock_validation(self,
                                  device_info: Dict[str, Any],
                                  snapshot_name: str,
                                  test_case: str) -> ValidationResult:
        """Run mock validation test"""
        # Simulate validation results
        import random

        pre_snapshot_file = self.snapshots_dir / f"{snapshot_name}_pre.json"
        post_snapshot_file = self.snapshots_dir / f"{snapshot_name}_post.json"

        if not pre_snapshot_file.exists() or not post_snapshot_file.exists():
            raise FileNotFoundError(f"Snapshot files not found for {snapshot_name}")

        # Load snapshots
        with open(pre_snapshot_file) as f:
            pre_data = json.load(f)
        with open(post_snapshot_file) as f:
            post_data = json.load(f)

        # Mock validation based on test case type
        if 'interface' in test_case:
            status = 'pass'  # Interfaces typically stable
            message = "All interfaces operational and consistent"
            details = {
                'interface_count': len(pre_data.get('interfaces', {})),
                'changes_detected': 0,
                'test_details': [
                    {'interface': 'ge-0/0/0', 'pre_status': 'up', 'post_status': 'up', 'result': 'pass'}
                ]
            }
        elif 'bgp' in test_case:
            # Simulate BGP session change
            bgp_change = post_data['bgp']['sessions_established'] - pre_data['bgp']['sessions_established']
            if bgp_change == 0:
                status = 'pass'
                message = "BGP sessions stable"
            else:
                status = 'pass'  # Changes can be expected
                message = f"BGP session count changed by {bgp_change}"

            details = {
                'pre_sessions': pre_data['bgp']['sessions_established'],
                'post_sessions': post_data['bgp']['sessions_established'],
                'change': bgp_change,
                'test_details': [
                    {'metric': 'session_count', 'change': bgp_change, 'result': 'pass'}
                ]
            }
        else:
            # Default system validation
            status = 'pass'  # Assume pass for mock
            message = "System validation completed"
            details = {
                'uptime_consistent': True,
                'system_stable': True,
                'test_details': [
                    {'metric': 'uptime', 'result': 'pass'}
                ]
            }

        return ValidationResult(
            device_id=device_info['host_ip'],
            test_name=test_case,
            status=status,
            message=message,
            details=details,
            timestamp=datetime.now(),
            pre_snapshot=f"{snapshot_name}_pre",
            post_snapshot=f"{snapshot_name}_post"
        )

    async def create_validation_suite(self,
                                    name: str,
                                    description: str,
                                    test_cases: List[str],
                                    devices: List[Dict[str, Any]]) -> ValidationSuite:
        """Create and execute a complete validation suite"""
        suite_id = f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        snapshot_name = suite_id

        start_time = datetime.now()
        all_results = []

        # Create pre-snapshots for all devices
        for device_info in devices:
            await self.create_pre_snapshot(device_info, snapshot_name)

        # Run validation tests (this would typically be done post-deployment)
        for device_info in devices:
            device_results = await self.run_validation_tests(
                device_info, snapshot_name, test_cases
            )
            all_results.extend(device_results)

        # Create post-snapshots for all devices
        for device_info in devices:
            await self.create_post_snapshot(device_info, snapshot_name)

        # Calculate overall status
        overall_status = 'pass' if all(r.status == 'pass' for r in all_results) else 'fail'

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        suite = ValidationSuite(
            suite_id=suite_id,
            name=name,
            description=description,
            test_cases=test_cases,
            devices=[d['host_ip'] for d in devices],
            created_at=start_time,
            results=all_results,
            overall_status=overall_status,
            execution_time=execution_time
        )

        # Save suite results
        self._save_validation_suite(suite)

        logger.info(f"Validation suite {suite_id} completed with status: {overall_status}")
        return suite

    def _save_validation_suite(self, suite: ValidationSuite):
        """Save validation suite results to file"""
        results_dir = self.config_dir / "results"
        results_dir.mkdir(exist_ok=True)

        suite_file = results_dir / f"{suite.suite_id}.json"

        # Convert to dict for JSON serialization
        suite_dict = asdict(suite)
        # Convert datetime objects to ISO strings
        suite_dict['created_at'] = suite.created_at.isoformat()
        for result in suite_dict['results']:
            result['timestamp'] = datetime.fromisoformat(result['timestamp'].isoformat()).isoformat()

        with open(suite_file, 'w') as f:
            json.dump(suite_dict, f, indent=2)

        logger.info(f"Saved validation suite results: {suite_file}")

    def get_available_test_cases(self) -> List[str]:
        """Get list of available test case files"""
        test_cases = []
        for file_path in self.test_cases_dir.glob("*.yml"):
            test_cases.append(file_path.stem)
        return test_cases

    def get_validation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent validation suite results"""
        results_dir = self.config_dir / "results"
        if not results_dir.exists():
            return []

        suites = []
        for file_path in sorted(results_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                with open(file_path) as f:
                    suite_data = json.load(f)
                suites.append(suite_data)
            except Exception as e:
                logger.error(f"Failed to load validation suite {file_path}: {e}")

        return suites

    async def generate_validation_report(self, suite_id: str) -> Dict[str, Any]:
        """Generate detailed validation report"""
        results_dir = self.config_dir / "results"
        suite_file = results_dir / f"{suite_id}.json"

        if not suite_file.exists():
            raise FileNotFoundError(f"Validation suite {suite_id} not found")

        with open(suite_file) as f:
            suite_data = json.load(f)

        # Generate summary statistics
        total_tests = len(suite_data['results'])
        passed_tests = len([r for r in suite_data['results'] if r['status'] == 'pass'])
        failed_tests = len([r for r in suite_data['results'] if r['status'] == 'fail'])
        error_tests = len([r for r in suite_data['results'] if r['status'] == 'error'])

        # Group results by test case
        test_case_summary = {}
        for result in suite_data['results']:
            test_case = result['test_name']
            if test_case not in test_case_summary:
                test_case_summary[test_case] = {'pass': 0, 'fail': 0, 'error': 0}
            test_case_summary[test_case][result['status']] += 1

        report = {
            'suite_info': {
                'id': suite_data['suite_id'],
                'name': suite_data['name'],
                'description': suite_data['description'],
                'created_at': suite_data['created_at'],
                'execution_time': suite_data['execution_time'],
                'overall_status': suite_data['overall_status']
            },
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'errors': error_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'test_case_summary': test_case_summary,
            'detailed_results': suite_data['results'],
            'devices_tested': suite_data['devices']
        }

        return report