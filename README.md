
# Tandem Piercer Experiment

Library currently in alpha development state.

---

Run with built-in simulator:

$ python run.py

Run with playback file:

$ python run.py --playback_file=tpe_playback_2021_12_21_17_42.dat

Run with PicoScope model 2000a:

$ python run.py --picoscope_mode=block

---

## Usage

run.py [-h] [--file PLAYBACK_FILE] [--bins BIN_COUNT] [--headless_mode HEADLESS_MODE] [--chance_rate CHANCE_RATE] [--background_rate BACKGROUND_RATE] [--experiment_name EXPERIMENT_NAME] [--experiment_dir EXPERIMENT_DIR]
              [--experiments_dir EXPERIMENTS_DIR] [--measurement_step MEASUREMENT_STEP] [--generate_report GENERATE_REPORT] [--generate_summary GENERATE_SUMMARY] [--store_waveforms STORE_WAVEFORMS]
              [--store_waveforms_channels STORE_WAVEFORMS_CHANNELS] [--store_statistics STORE_STATISTICS] [--execution_time EXECUTION_TIME] [--pulse_source PULSE_SOURCE] [--spectrum_range SPECTRUM_RANGE]
              [--spectrum_queue_size SPECTRUM_QUEUE_SIZE] [--picoscope_mode PICOSCOPE_MODE] [--verbose VERBOSE]

Tandem Piercer Experiment simulator, playback and PicoScope data acquisition program. Do five measurements in steps, store data, and create a report file via Jupyter notebook document.

optional arguments:
  -h, --help            show this help message and exit
  --file PLAYBACK_FILE  Default playback file to run the application.
  --bins BIN_COUNT      Bin count for histograms
  --headless_mode HEADLESS_MODE
                        Headless mode to start and run application without GUI. Options are: true|false. Default is: False.
  --chance_rate CHANCE_RATE
                        Change rate measured in a separate measurement step 2.
  --background_rate BACKGROUND_RATE
                        Background rate measured in a separate measurement step 3.
  --experiment_name EXPERIMENT_NAME
                        Experiment name to identify it. Default is: Tandem Piercer Experiment
  --experiment_dir EXPERIMENT_DIR
                        Experiment sub directory. Default is: default
  --experiments_dir EXPERIMENTS_DIR
                        Experiments main directory. Default is: experiments
  --measurement_step MEASUREMENT_STEP
                        Measurement step 1-5. Default is: 1
  --generate_report GENERATE_REPORT
                        Generate report from the measurement. Measurement data must be in the sub directory defined by measurement_dir. Options are: true|false. Default is: False
  --generate_summary GENERATE_SUMMARY
                        Generate summary report from the measurements in all experiments. Measurement data is collected from the measurements_dir. Options are: true|false. Default is: False
  --store_waveforms STORE_WAVEFORMS
                        Store waveforms from buffers to csv files. Options are: 0=disabled, 1=only when coincident signals are found, 2=all triggered waveforms. Default is: 0
  --store_waveforms_channels STORE_WAVEFORMS_CHANNELS
                        When store_waveforms from buffers to csv files is used, this option defines what channels are stored to the file. Options are some of these characters: ABCD. Default is: ABCD
  --store_statistics STORE_STATISTICS
                        Store measurement statistics to csv files. Default is: False
  --execution_time EXECUTION_TIME
                        Automatic halt for execution of the experiment. Options are: 0=for non-interrupting execution of the expriment, else define time in seconds, for example 3600 for an hour. Default is: 0 seconds.
  --pulse_source PULSE_SOURCE
                        Pulse radiation source label. For example: Cd-109 10μCi. Default is: Background
  --spectrum_range SPECTRUM_RANGE
                        Voltage range for the spectrum histograms. Default is: 19661
  --spectrum_queue_size SPECTRUM_QUEUE_SIZE
                        Queue size for spectrum histogram. Default is: 30000
  --picoscope_mode PICOSCOPE_MODE
                        PicoScope mode for importing the data acquisition module. Options are: block, stream, None. Default is: block.
  --verbose VERBOSE     Verbose mode for showing for debug information in the console. Options are: true|false. Default is: False
