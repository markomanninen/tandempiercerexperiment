
python run.py --pulse_source="Background"

python run.py --pulse_source="Background" --store_statistics=1

python run.py --pulse_source="Cd-109 1μci" --headless_mode=1 --execution_time=400 --store_statistics=1

python run.py --pulse_source="Cd-109 1μci" --headless_mode=1 --execution_time=200 --store_waveforms=1 --store_waveforms_channels=ABCD

python run.py --pulse_source="Cd-109 1μci" --store_waveforms=1 --store_waveforms_channels=CD


#

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=0 --timebase=63 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=1400

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=1 --timebase=63 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=1400 --simple_trigger_alternate=1


# Detectors apart from each other - long run

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=1 --simple_trigger=0 --timebase=63 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=21600 --experiment_name="Detectors apart from each other - No trigger long run"

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=1 --simple_trigger=1 --timebase=63 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=21600 --experiment_name="Detectors apart from each other - Alternating trigger long run" --simple_trigger_alternate=1


# Alternating trigger 2ns

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=1 --simple_trigger=1 --timebase=2 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=10800 --experiment_name="Detectors apart from each other - Alternating trigger 2ns" --simple_trigger_alternate=1

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=1 --timebase=2 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=10800 --experiment_name="Detectors apart from each other - Alternating trigger 2ns" --simple_trigger_alternate=1


python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=1 --simple_trigger=1 --timebase=2 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=10800 --experiment_name="Detectors next to each other - Alternating trigger 2ns" --simple_trigger_alternate=1

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=1 --timebase=2 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=10800 --experiment_name="Detectors next to each other - Alternating trigger 2ns" --simple_trigger_alternate=1


python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=1 --simple_trigger=1 --timebase=2 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=10800 --experiment_name="Detectors on top of each other - Alternating trigger 2ns" --simple_trigger_alternate=1 --detector_geometry=top

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=1 --timebase=2 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=10800 --experiment_name="Detectors on top of each other - Alternating trigger 2ns" --simple_trigger_alternate=1 --detector_geometry=top

# Whole spectra

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=1 --timebase=2 --pre_trigger_samples=500 --post_trigger_samples=500 --execution_time=600 --experiment_name="Background whole spectrum" --simple_trigger_alternate=1 --detector_geometry=next --sca_module_settings_a=4.0,3.75,10.0,0.70 --sca_module_settings_b=4.0,10.0,10.0,0.4 --high_voltage=-1000 --spectrum_low_limits=4096,4096,842,576 --headless_mode=1

python run.py --pulse_source="Cd-109 1μci" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=1 --timebase=2 --pre_trigger_samples=500 --post_trigger_samples=500 --execution_time=600 --experiment_name="Cd-109 1μci whole spectrum" --simple_trigger_alternate=1 --detector_geometry=true --sca_module_settings_a=4.0,3.75,10.0,0.70 --sca_module_settings_b=4.0,10.0,10.0,0.4 --high_voltage=-1000 --spectrum_low_limits=4096,4096,842,576 --headless_mode=0

python run.py --pulse_source="Cd-109 10μci" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=1 --timebase=2 --pre_trigger_samples=500 --post_trigger_samples=500 --execution_time=600 --experiment_name="Cd-109 10μci whole spectrum" --simple_trigger_alternate=1 --detector_geometry=true --sca_module_settings_a=4.0,3.75,10.0,0.70 --sca_module_settings_b=4.0,10.0,10.0,0.4 --high_voltage=-1000 --spectrum_low_limits=4096,4096,842,576 --headless_mode=0

python run.py --pulse_source="Co-57 10μci" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=1 --timebase=2 --pre_trigger_samples=500 --post_trigger_samples=500 --execution_time=600 --experiment_name="Co-57 10μci whole spectrum" --simple_trigger_alternate=1 --detector_geometry=true --sca_module_settings_a=4.0,3.75,10.0,0.70 --sca_module_settings_b=4.0,10.0,10.0,0.4 --high_voltage=-1000 --spectrum_low_limits=4096,4096,842,576 --headless_mode=0
