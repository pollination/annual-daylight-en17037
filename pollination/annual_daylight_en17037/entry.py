from pollination_dsl.dag import Inputs, DAG, task, Outputs
from dataclasses import dataclass
from pollination.two_phase_daylight_coefficient import TwoPhaseDaylightCoefficientEntryPoint
from pollination.honeybee_display.translate import ModelToVis

# input/output alias
from pollination.alias.inputs.model import hbjson_model_grid_input
from pollination.alias.inputs.north import north_input
from pollination.alias.inputs.radiancepar import rad_par_annual_input, \
    daylight_thresholds_input
from pollination.alias.inputs.grid import grid_filter_input, \
    min_sensor_count_input, cpu_count
from pollination.alias.outputs.daylight import annual_daylight_results, \
    daylight_autonomy_results, continuous_daylight_autonomy_results, \
    udi_results, udi_lower_results, udi_upper_results

from ._process_epw import AnnualDaylightEN17037ProcessEPW
from ._postprocess import AnnualDaylightEN17037PostProcess


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
        'sensor grids.', default=500,
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

    @task(template=AnnualDaylightEN17037ProcessEPW)
    def annual_metrics_en17037_process_epw(
        self, epw=epw
    ):
        return [
            {
                'from': AnnualDaylightEN17037ProcessEPW()._outputs.wea,
                'to': 'wea.wea'
            },
            {
                'from': AnnualDaylightEN17037ProcessEPW()._outputs.daylight_hours,
                'to': 'daylight_hours.csv'
            }
        ]

    @task(
        template=TwoPhaseDaylightCoefficientEntryPoint,
        needs=[annual_metrics_en17037_process_epw]
    )
    def run_two_phase_daylight_coefficient(
            self, north=north, cpu_count=cpu_count, min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters, grid_filter=grid_filter,
            model=model, wea=annual_metrics_en17037_process_epw._outputs.wea
    ):
        pass

    @task(
        template=AnnualDaylightEN17037PostProcess,
        needs=[annual_metrics_en17037_process_epw, run_two_phase_daylight_coefficient]
    )
    def annual_metrics_en17037_postprocess(
        self, results='results',
        schedule=annual_metrics_en17037_process_epw._outputs.daylight_hours,
        thresholds=thresholds
    ):
        return [
            {
                'from': AnnualDaylightEN17037PostProcess()._outputs.en17037,
                'to': 'en17037'
            },
            {
                'from': AnnualDaylightEN17037PostProcess()._outputs.metrics,
                'to': 'metrics'
            }
        ]

    @task(
        template=ModelToVis,
        needs=[annual_metrics_en17037_postprocess],
        sub_paths={
            'grid_data': 'da'
        })
    def create_vsf_en17037(
        self, model=model, grid_data='en17037',
        active_grid_data='target_illuminance_300', output_format='vsf'
    ):
        return [
            {
                'from': ModelToVis()._outputs.output_file,
                'to': 'visualization_en17037.vsf'
            }
        ]

    @task(template=ModelToVis, needs=[annual_metrics_en17037_postprocess])
    def create_vsf_metrics(
        self, model=model, grid_data='metrics', active_grid_data='udi',
        output_format='vsf'
    ):
        return [
            {
                'from': ModelToVis()._outputs.output_file,
                'to': 'visualization_metrics.vsf'
            }
        ]

    visualization_en17037 = Outputs.file(
        source='visualization_en17037.vsf',
        description='Annual daylight EN17037 result visualization in '
        'VisualizationSet format.'
    )

    visualization_metrics = Outputs.file(
        source='visualization_metrics.vsf',
        description='Annual daylight result visualization in VisualizationSet format.'
    )

    results = Outputs.folder(
        source='results', description='Folder with raw result files (.ill) that '
        'contain illuminance matrices for each sensor at each timestep of the analysis.',
        alias=annual_daylight_results
    )

    en17037 = Outputs.folder(
        source='en17037', description='Annual daylight EN17037 metrics folder.'
    )

    metrics = Outputs.folder(
        source='metrics', description='Annual daylight metrics folder. These '
        'metrics are the usual annual daylight metrics with the daylight '
        'hours occupancy schedule.'
    )

    da = Outputs.folder(
        source='metrics/da', description='Daylight autonomy results.',
        alias=daylight_autonomy_results
    )

    cda = Outputs.folder(
        source='metrics/cda', description='Continuous daylight autonomy results.',
        alias=continuous_daylight_autonomy_results
    )

    udi = Outputs.folder(
        source='metrics/udi', description='Useful daylight illuminance results.',
        alias=udi_results
    )

    udi_lower = Outputs.folder(
        source='metrics/udi_lower', description='Results for the percent of time that '
        'is below the lower threshold of useful daylight illuminance.',
        alias=udi_lower_results
    )

    udi_upper = Outputs.folder(
        source='metrics/udi_upper', description='Results for the percent of time that '
        'is above the upper threshold of useful daylight illuminance.',
        alias=udi_upper_results
    )
