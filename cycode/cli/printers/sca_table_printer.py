from collections import defaultdict
from typing import List, Dict

import click
from texttable import Texttable

from cycode.cli.consts import LICENSE_COMPLIANCE_POLICY_ID, PACKAGE_VULNERABILITY_POLICY_ID
from cycode.cli.models import DocumentDetections, Detection
from cycode.cli.printers.base_table_printer import BaseTablePrinter

SEVERITY_COLUMN = 'Severity'
LICENSE_COLUMN = 'License'
UPGRADE_COLUMN = 'Upgrade'
REPOSITORY_COLUMN = 'Repository'
CVE_COLUMN = 'CVE'

PREVIEW_DETECTIONS_COMMON_HEADERS = [
    'File Path',
    'Ecosystem',
    'Dependency Name',
    'Direct Dependency',
    'Development Dependency'
]


class SCATablePrinter(BaseTablePrinter):
    def _print_results(self, results: List[DocumentDetections]) -> None:
        detections_per_detection_type_id = self._extract_detections_per_detection_type_id(results)
        self._print_detection_per_detection_type_id(detections_per_detection_type_id)

    @staticmethod
    def _extract_detections_per_detection_type_id(results: List[DocumentDetections]) -> Dict[str, List[Detection]]:
        detections_per_detection_type_id = defaultdict(list)

        for document_detection in results:
            for detection in document_detection.detections:
                detections_per_detection_type_id[detection.detection_type_id].append(detection)

        return detections_per_detection_type_id

    def _print_detection_per_detection_type_id(
            self, detections_per_detection_type_id: Dict[str, List[Detection]]
    ) -> None:
        for detection_type_id in detections_per_detection_type_id:
            detections = detections_per_detection_type_id[detection_type_id]
            headers = self._get_table_headers()

            title = None
            rows = []

            if detection_type_id == PACKAGE_VULNERABILITY_POLICY_ID:
                title = "Dependencies Vulnerabilities"

                headers = [SEVERITY_COLUMN] + headers
                headers.extend(PREVIEW_DETECTIONS_COMMON_HEADERS)
                headers.append(CVE_COLUMN)
                headers.append(UPGRADE_COLUMN)

                for detection in detections:
                    rows.append(self._get_upgrade_package_vulnerability(detection))
            elif detection_type_id == LICENSE_COMPLIANCE_POLICY_ID:
                title = "License Compliance"

                headers.extend(PREVIEW_DETECTIONS_COMMON_HEADERS)
                headers.append(LICENSE_COLUMN)

                for detection in detections:
                    rows.append(self._get_license(detection))

            if rows:
                self._print_table_detections(detections, headers, rows, title)

    def _get_table_headers(self) -> list:
        if self._is_git_repository():
            return [REPOSITORY_COLUMN]

        return []

    def _print_table_detections(
            self, detections: List[Detection], headers: List[str], rows, title: str
    ) -> None:
        self._print_summary_issues(detections, title)
        text_table = Texttable()
        text_table.header(headers)

        self.set_table_width(headers, text_table)

        for row in rows:
            text_table.add_row(row)

        click.echo(text_table.draw())

    @staticmethod
    def set_table_width(headers: List[str], text_table: Texttable) -> None:
        header_width_size_cols = []
        for header in headers:
            header_len = len(header)
            if header == CVE_COLUMN:
                header_width_size_cols.append(header_len * 5)
            elif header == UPGRADE_COLUMN:
                header_width_size_cols.append(header_len * 2)
            else:
                header_width_size_cols.append(header_len)
        text_table.set_cols_width(header_width_size_cols)

    @staticmethod
    def _print_summary_issues(detections: List, title: str) -> None:
        click.echo(f'⛔ Found {len(detections)} issues of type: {click.style(title, bold=True)}')

    def _get_common_detection_fields(self, detection: Detection) -> List[str]:
        row = [
            detection.detection_details.get('file_name'),
            detection.detection_details.get('ecosystem'),
            detection.detection_details.get('package_name'),
            detection.detection_details.get('is_direct_dependency_str'),
            detection.detection_details.get('is_dev_dependency_str')
        ]

        if self._is_git_repository():
            row = [detection.detection_details.get('repository_name')] + row

        return row

    def _get_upgrade_package_vulnerability(self, detection: Detection) -> List[str]:
        alert = detection.detection_details.get('alert')
        row = [
            detection.detection_details.get('advisory_severity'),
            *self._get_common_detection_fields(detection),
            detection.detection_details.get('vulnerability_id')
        ]

        upgrade = ''
        if alert.get("first_patched_version"):
            upgrade = f'{alert.get("vulnerable_requirements")} -> {alert.get("first_patched_version")}'
        row.append(upgrade)

        return row

    def _get_license(self, detection: Detection) -> List[str]:
        row = self._get_common_detection_fields(detection)
        row.append(f'{detection.detection_details.get("license")}')
        return row
