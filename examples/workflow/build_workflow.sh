gwaith_build_example_workflow \
    --workflow-name test_workflow \
    --workflow-dir workflow_out \
    --config-files \
        config_files/workflow.yaml \
        config_files/central.yaml \
        config_files/noise.yaml \
        config_files/offset.yaml \
        config_files/sine_low.yaml \
        config_files/sine_high.yaml \
        config_files/sine_gaussian.yaml \
    --verbose --verbose \
    --submit-now