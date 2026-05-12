python generate_example_data.py \
  --verbose \
  --noise-psd amplitude:0.5 floor:0.0001 f_knee:0.0002 slope:-1.8 \
  --sine-waves 1.2:1.5e-4:0.1 0.85:3e-4:1.2 0.5:1.2e-3:-0.7 0.9:1e-2:2 0.65:4.5e-2:-1.4 \
  --offset 0.85 \
  --seed 12345 \
  --generate-plots \
  --output-directory example_data