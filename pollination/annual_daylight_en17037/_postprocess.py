from pollination_dsl.dag import Inputs, GroupedDAG, task, Outputs
from dataclasses import dataclass
from pollination.honeybee_radiance_postprocess.post_process import AnnualDaylightEN17037Metrics
from pollination.honeybee_radiance_postprocess.post_process import AnnualDaylightMetrics

# input/output alias
from pollination.alias.inputs.radiancepar import daylight_thresholds_input
from pollination.alias.inputs.schedule import schedule_csv_input


@dataclass
class AnnualDaylightEN17037PostProcess(GroupedDAG):
    """Annual daylight EN17037 post-process."""

    # inputs
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

    @task(template=AnnualDaylightEN17037Metrics)
    def calculate_annual_metrics_en17037(
        self, folder=results, schedule=schedule
    ):
        return [
            {
                'from': AnnualDaylightEN17037Metrics()._outputs.annual_en17037_metrics,
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

    en17037 = Outputs.folder(
        source='en17037', description='Annual daylight EN17037 metrics folder.'
    )

    metrics = Outputs.folder(
        source='metrics', description='Annual daylight metrics folder. These '
        'metrics are the usual annual daylight metrics with the daylight '
        'hours occupancy schedule.'
    )
