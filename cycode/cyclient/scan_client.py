import json
from typing import List

from requests import Response

from cycode.cli.zip_file import InMemoryZip
from . import models
from .cycode_client_base import CycodeClientBase
from .scan_config.scan_config_base import ScanConfigBase


class ScanClient:
    def __init__(self, scan_cycode_client: CycodeClientBase, scan_config: ScanConfigBase):
        self.scan_cycode_client = scan_cycode_client
        self.scan_config = scan_config
        self.SCAN_CONTROLLER_PATH = 'api/v1/scan'
        self.DETECTIONS_SERVICE_CONTROLLER_PATH = 'api/v1/detections'

    def content_scan(self, scan_type: str, file_name: str, content: str, is_git_diff: bool = True) -> models.ScanResult:
        path = f'{self.scan_config.get_service_name(scan_type)}/{self.SCAN_CONTROLLER_PATH}/content'
        body = {'name': file_name, 'content': content, 'is_git_diff': is_git_diff}
        response = self.scan_cycode_client.post(url_path=path, body=body)
        return self.parse_scan_response(response)

    def file_scan(self, scan_type: str, path: str) -> models.ScanResult:
        url_path = f'{self.scan_config.get_service_name(scan_type)}/{self.SCAN_CONTROLLER_PATH}'
        files = {'file': open(path, 'rb')}
        response = self.scan_cycode_client.post(url_path=url_path, files=files)
        return self.parse_scan_response(response)

    def zipped_file_scan(self, scan_type: str, zip_file: InMemoryZip, scan_id: str, scan_parameters: dict,
                         is_git_diff: bool = False) -> models.ZippedFileScanResult:
        url_path = f'{self.scan_config.get_service_name(scan_type)}/{self.SCAN_CONTROLLER_PATH}/zipped-file'
        files = {'file': ('multiple_files_scan.zip', zip_file.read())}

        response = self.scan_cycode_client.post(
            url_path=url_path,
            data={'scan_id': scan_id, 'is_git_diff': is_git_diff, 'scan_parameters': json.dumps(scan_parameters)},
            files=files
        )
        return self.parse_zipped_file_scan_response(response)

    def zipped_file_scan_async(self, zip_file: InMemoryZip, scan_type: str, scan_parameters: dict,
                               is_git_diff: bool = False) -> models.ScanInitializationResponse:
        url_path = f'{self.scan_config.get_scans_prefix()}/{self.SCAN_CONTROLLER_PATH}/{scan_type}/repository'
        files = {'file': ('multiple_files_scan.zip', zip_file.read())}
        response = self.scan_cycode_client.post(
            url_path=url_path,
            data={'is_git_diff': is_git_diff, 'scan_parameters': json.dumps(scan_parameters)},
            files=files
        )
        return models.ScanInitializationResponseSchema().load(response.json())

    def multiple_zipped_file_scan_async(self, from_commit_zip_file: InMemoryZip, to_commit_zip_file: InMemoryZip,
                                        scan_type: str, scan_parameters: dict,
                                        is_git_diff: bool = False) -> models.ScanInitializationResponse:
        url_path = f'{self.scan_config.get_scans_prefix()}/{self.SCAN_CONTROLLER_PATH}/{scan_type}/repository/commit-range'
        files = {
            'file_from_commit': ('multiple_files_scan.zip', from_commit_zip_file.read()),
            'file_to_commit': ('multiple_files_scan.zip', to_commit_zip_file.read())
        }
        response = self.scan_cycode_client.post(
            url_path=url_path,
            data={'is_git_diff': is_git_diff, 'scan_parameters': json.dumps(scan_parameters)},
            files=files
        )
        return models.ScanInitializationResponseSchema().load(response.json())

    def get_scan_details(self, scan_id: str) -> models.ScanDetailsResponse:
        url_path = f'{self.scan_config.get_scans_prefix()}/{self.SCAN_CONTROLLER_PATH}/{scan_id}'
        response = self.scan_cycode_client.get(url_path=url_path)
        return models.ScanDetailsResponseSchema().load(response.json())

    def get_scan_detections(self, scan_id: str) -> List[dict]:
        detections = []
        page_number = 0
        page_size = 200
        last_response_size = 0

        while page_number == 0 or last_response_size == page_size:
            url_path = f'{self.scan_config.get_detections_prefix()}/{self.DETECTIONS_SERVICE_CONTROLLER_PATH}?scan_id={scan_id}&page_size={page_size}&page_number={page_number}'
            response = self.scan_cycode_client.get(url_path=url_path).json()
            detections.extend(response)

            page_number += 1
            last_response_size = len(response)

        return detections

    def get_scan_detections_count(self, scan_id: str) -> int:
        url_path = f'{self.scan_config.get_detections_prefix()}/{self.DETECTIONS_SERVICE_CONTROLLER_PATH}/count?scan_id={scan_id}'
        response = self.scan_cycode_client.get(url_path=url_path)
        return response.json().get('count', 0)

    def commit_range_zipped_file_scan(
            self, scan_type: str, zip_file: InMemoryZip, scan_id: str
    ) -> models.ZippedFileScanResult:
        url_path = f'{self.scan_config.get_service_name(scan_type)}/{self.SCAN_CONTROLLER_PATH}/commit-range-zipped-file'
        files = {'file': ('multiple_files_scan.zip', zip_file.read())}
        response = self.scan_cycode_client.post(url_path=url_path, data={'scan_id': scan_id}, files=files)
        return self.parse_zipped_file_scan_response(response)

    def report_scan_status(self, scan_type: str, scan_id: str, scan_status: dict):
        url_path = f'{self.scan_config.get_service_name(scan_type)}/{self.SCAN_CONTROLLER_PATH}/{scan_id}/status'
        self.scan_cycode_client.post(url_path=url_path, body=scan_status)

    @staticmethod
    def parse_scan_response(response: Response) -> models.ScanResult:
        return models.ScanResultSchema().load(response.json())

    @staticmethod
    def parse_zipped_file_scan_response(response: Response) -> models.ZippedFileScanResult:
        return models.ZippedFileScanResultSchema().load(response.json())

    @staticmethod
    def get_service_name(scan_type: str) -> str:
        if scan_type == 'secret':
            return 'secret'
        elif scan_type == 'iac':
            return 'iac'
        elif scan_type == 'sca' or scan_type == 'sast':
            return 'scans'
