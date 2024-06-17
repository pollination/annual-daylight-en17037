from pollination_dsl.dag import Inputs, GroupedDAG, task, Outputs
from dataclasses import dataclass
from pollination.honeybee_radiance_postprocess.post_process import AnnualDaylightEn17037Metrics
from pollination.honeybee_radiance_postprocess.post_process import AnnualDaylightMetrics
from pollination.honeybee_radiance_postprocess.post_process import GridSummaryMetrics

# input/output alias
from pollination.alias.inputs.radiancepar import daylight_thresholds_input
from pollination.alias.inputs.schedule import schedule_csv_input


@dataclass
class AnnualDaylightEN17037PostProcess(GroupedDAG):
    """Annual daylight EN17037 post-process."""

    # inputs
    model = Inputs.file(
        description='Input Honeybee model.',
        extensions=['json', 'hbjson', 'pkl', 'hbpkl', 'zip']
    )

    results = Inputs.folder(
        description='Annual daylight results folder.'
    )

    schedule = Inputs.file(
        description='Path to an annual schedule file. Values should be 0-1 separated '
        'by new line. If not provided an 8-5 annual schedule will be created.',
        extensions=['txt', 'csv'], optional=True, alias=schedule_csv_input
    )

    thresholds = Inputs.str(
        description='A string to change the threshold for daylight autonomy and useful '
        'daylight illuminance. Valid keys are -t for daylight autonomy threshold, -lt '
        'for the lower threshold for useful daylight illuminance and -ut for the upper '
        'threshold. The default is -t 300 -lt 100 -ut 3000. The order of the keys is '
        'not important and you can include one or all of them. For instance if you only '
        'want to change the upper threshold to 2000 lux you should use -ut 2000 as '
        'the input.', default='-t 300 -lt 100 -ut 3000',
        alias=daylight_thresholds_input
    )

    grid_metrics = Inputs.file(
        description='A JSON file with additional custom metrics to calculate.',
        path='grid_metrics.json', optional=True
    )

    @task(template=AnnualDaylightEn17037Metrics)
    def calculate_annual_metrics_en17037(
        self, folder=results, schedule=schedule
    ):
        return [
            {
                'from': AnnualDaylightEn17037Metrics()._outputs.annual_en17037_metrics,
                'to': 'en17037'
            }
        ]

    @task(template=AnnualDaylightMetrics)
    def calculate_annual_metrics(
        self, folder=results, schedule=schedule, thresholds=thresholds
    ):
        return [
            {
                'from': AnnualDaylightMetrics()._outputs.annual_metrics,
                'to': 'metrics'
            }
        ]

    @task(
        template=GridSummaryMetrics,
        needs=[calculate_annual_metrics]
    )
    def grid_summary_metrics(
        self, folder=calculate_annual_metrics._outputs.annual_metrics,
        model=model, grid_metrics=grid_metrics,
        folder_level='sub-folder'
    ):
        return [
            {
                'from': GridSummaryMetrics()._outputs.grid_summary,
                'to': 'grid_summary.csv'
            }
        ]

    en17037 = Outputs.folder(
        source='en17037', description='Annual daylight EN17037 metrics folder.'
    )

    metrics = Outputs.folder(
        source='metrics', description='Annual daylight metrics folder. These '
        'metrics are the usual annual daylight metrics with the daylight '
        'hours occupancy schedule.'
    )

    grid_summary = Outputs.file(
        source='grid_summary.csv', description='grid summary.'
    )
