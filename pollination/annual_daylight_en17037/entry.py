from pollination_dsl.dag import Inputs, DAG, task, Outputs
from dataclasses import dataclass
from pollination.two_phase_daylight_coefficient import TwoPhaseDaylightCoefficientEntryPoint
from pollination.honeybee_radiance_postprocess.post_process import AnnualDaylightEN17037Metrics
from pollination.honeybee_radiance.schedule import EPWtoDaylightHours
from pollination.ladybug.translate import EpwToWea

# input/output alias
from pollination.alias.inputs.model import hbjson_model_grid_input
from pollination.alias.inputs.north import north_input
from pollination.alias.inputs.radiancepar import rad_par_annual_input, \
    daylight_thresholds_input
from pollination.alias.inputs.grid import grid_filter_input, \
    min_sensor_count_input, cpu_count
from pollination.alias.outputs.daylight import annual_daylight_results


@dataclass
class AnnualDaylightEN17037EntryPoint(DAG):
    """Annual daylight EN17037 entry point."""

    # inputs
    north = Inputs.float(
        default=0,
        description='A number for rotation from north.',
        spec={'type': 'number', 'minimum': 0, 'maximum': 360},
        alias=north_input
    )

    cpu_count = Inputs.int(
        default=50,
        description='The maximum number of CPUs for parallel execution. This will be '
        'used to determine the number of sensors run by each worker.',
        spec={'type': 'integer', 'minimum': 1},
        alias=cpu_count
    )

    min_sensor_count = Inputs.int(
        description='The minimum number of sensors in each sensor grid after '
        'redistributing the sensors based on cpu_count. This value takes '
        'precedence over the cpu_count and can be used to ensure that '
        'the parallelization does not result in generating unnecessarily small '
        'sensor grids. The default value is set to 1, which means that the '
        'cpu_count is always respected.', default=1,
        spec={'type': 'integer', 'minimum': 1},
        alias=min_sensor_count_input
    )

    radiance_parameters = Inputs.str(
        description='The radiance parameters for ray tracing.',
        default='-ab 2 -ad 5000 -lw 2e-05',
        alias=rad_par_annual_input
    )

    grid_filter = Inputs.str(
        description='Text for a grid identifier or a pattern to filter the sensor grids '
        'of the model that are simulated. For instance, first_floor_* will simulate '
        'only the sensor grids that have an identifier that starts with '
        'first_floor_. By default, all grids in the model will be simulated.',
        default='*',
        alias=grid_filter_input
    )

    model = Inputs.file(
        description='A Honeybee Model JSON file (HBJSON) or a Model pkl (HBpkl) file. '
        'This can also be a zipped version of a Radiance folder, in which case this '
        'recipe will simply unzip the file and simulate it as-is.',
        extensions=['json', 'hbjson', 'pkl', 'hbpkl', 'zip'],
        alias=hbjson_model_grid_input
    )

    epw = Inputs.file(
        description='EPW file.',
        extensions=['epw']
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

    @task(
        template=EPWtoDaylightHours
    )
    def create_daylight_hours(
        self, epw=epw
    ):
        return [
            {
                'from': EPWtoDaylightHours()._outputs.daylight_hours,
                'to': 'daylight_hours.csv'
            }
        ]

    @task(
        template=EpwToWea
    )
    def create_wea(
        self, epw=epw
    ):
        return [
            {
                'from': EpwToWea()._outputs.wea,
                'to': 'wea.wea'
            }
        ]

    @task(
        template=TwoPhaseDaylightCoefficientEntryPoint,
        needs=[create_daylight_hours, create_wea]
    )
    def run_two_phase_daylight_coefficient(
            self, north=north, cpu_count=cpu_count, min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters, grid_filter=grid_filter,
            model=model, wea=create_wea._outputs.wea
    ):
        pass

    @task(
        template=AnnualDaylightEN17037Metrics,
        needs=[create_daylight_hours, run_two_phase_daylight_coefficient]
    )
    def calculate_annual_metrics_en17037(
        self, folder='results',
        schedule=create_daylight_hours._outputs.daylight_hours
    ):
        return [
            {
                'from': AnnualDaylightEN17037Metrics()._outputs.annual_en17037_metrics,
                'to': 'metrics'
            }
        ]

    results = Outputs.folder(
        source='results', description='Folder with raw result files (.ill) that '
        'contain illuminance matrices for each sensor at each timestep of the analysis.',
        alias=annual_daylight_results
    )

    metrics = Outputs.folder(
        source='metrics', description='Annual EN 173037 metrics folder.'
    )
