
python run.py --pulse_source="Background"

python run.py --pulse_source="Background" --store_statistics=1

python run.py --pulse_source="Cd-109 1mci" --headless_mode=1 --execution_time=400 --store_statistics=1

python run.py --pulse_source="Cd-109 1mci" --headless_mode=1 --execution_time=200 --store_waveforms=1 --store_waveforms_channels=ABCD

python run.py --pulse_source="Cd-109 1mci" --store_waveforms=1 --store_waveforms_channels=CD



python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=0 --timebase=63 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=1400

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=0 --simple_trigger=1 --timebase=63 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=1400 --simple_trigger_alternate=1


python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=1 --simple_trigger=0 --timebase=63 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=21600 --experiment_name="Detectors on top of each other - No trigger long run"

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=1 --simple_trigger=1 --timebase=63 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=21600 --experiment_name="Detectors on top of each other - Trigger long run" --simple_trigger_alternate=0

python run.py --pulse_source="Background" --store_statistics=2 --pulse_detection_mode=1 --simple_trigger=1 --timebase=63 --pre_trigger_samples=5000 --post_trigger_samples=5000 --execution_time=21600 --experiment_name="Detectors on top of each other - Alternating trigger long run" --simple_trigger_alternate=1
