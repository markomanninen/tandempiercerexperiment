
python run.py --pulse_source="Background"

python run.py --pulse_source="Cd-109 1mci" --headless_mode=1 --execution_time=400 --store_statistics=1

python run.py --pulse_source="Cd-109 1mci" --headless_mode=1 --execution_time=200 --store_waveforms=1 --store_waveforms_channels=ABCD

python run.py --pulse_source="Cd-109 1mci" --store_waveforms=1 --store_waveforms_channels=CD
