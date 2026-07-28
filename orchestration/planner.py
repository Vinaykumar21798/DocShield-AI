from orchestration.execution_plan import (
    WorkflowExecutionPlan,
    WorkflowStep,
)


class WorkflowPlanner:
    """
    Builds the ordered execution plan for document processing.
    """

    def create_plan(self) -> WorkflowExecutionPlan:
        return WorkflowExecutionPlan(
            steps=(
                WorkflowStep.LOAD_DOCUMENT,
                WorkflowStep.UPDATE_PROCESSING_STATUS,
                WorkflowStep.DOCUMENT_CLASSIFICATION,
                WorkflowStep.OCR_DECISION,
                WorkflowStep.OCR_EXECUTION,
                WorkflowStep.STORE_OCR_RESULTS,
                WorkflowStep.DETECTION_EXECUTION,
                WorkflowStep.STORE_DETECTION_RESULTS,
                WorkflowStep.HUMAN_REVIEW,
                WorkflowStep.REDACTION,
                WorkflowStep.REPORT_GENERATION,
                WorkflowStep.COMPLETE_WORKFLOW,
            )
        )