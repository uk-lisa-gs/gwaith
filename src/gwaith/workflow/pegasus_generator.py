"""Pegasus workflow generator for GWAITH."""

from pathlib import Path
import logging

from gwaith import import_optional
import Pegasus
pegasus_api = import_optional("Pegasus.api")
logger = logging.getLogger('gwaith.workflow.pegasus_generator')


def build_pegasus_workflow(config, workflow_name, workflow_dir):
    """
    Builds a Pegasus workflow from a Gwaith configuration object.

    Args:
        config (GwaithConfigParser): The parsed and normalised config.
        workflow_name (str): The name for the workflow.
        workflow_dir (Path): The directory for workflow files.

    Returns:
        pegasus.api.Workflow: The constructed Pegasus workflow object.
    """
    logger.info("Building Pegasus workflow from configuration")

    # --- Catalogs ---    
    sc = pegasus_api.SiteCatalog()
    tc = pegasus_api.TransformationCatalog()
    rc = pegasus_api.ReplicaCatalog()

    # --- Workflow ---
    wf = pegasus_api.Workflow(workflow_name, infer_dependencies=True)

    # --- Input Data ---
    input_file_path = config.get("input", "data_file")
    input_file_lfn = Path(input_file_path).name
    input_file = File(input_file_lfn)
    rc.add_replica("local", input_file, f"file://{Path(input_file_path).resolve()}")
    wf.add_replica_catalog(rc)

    # --- Transformations ---
    # We assume executables are in the PATH on the execution site.
    # A more advanced version could get paths from the config.
    executables = config.get("executables", {})
    for name, path in executables.items():
        trans = pegasus_api.Transformation(name, site="local", pfn=path, is_stageable=False)
        tc.add_transformations(trans)

    modules = config.get("modules", {})
    for mod_name, mod_config in modules.items():
        if 'executable' in mod_config:
             # This assumes the executable name in the config matches a transformation name
            trans_name = mod_config['executable'].split('/')[-1]
            if trans_name not in tc.transformations:
                trans = pegasus_api.Transformation(trans_name, site="local", pfn=mod_config['executable'], is_stageable=False)
                tc.add_transformations(trans)

    wf.add_transformation_catalog(tc)

    # --- Jobs ---
    # This is a simplified example. The logic from the original `build_workflow_graph`
    # for rounds, streams, and dependencies would need to be translated here.
    # For now, let's create one job for each module as a demonstration.

    for mod_name, mod_config in modules.items():
        if 'executable' not in mod_config:
            continue

        trans_name = mod_config['executable'].split('/')[-1]
        output_file_lfn = f"{mod_name}_output.txt"
        output_file = pegasus_api.File(output_file_lfn)

        job = pegasus_api.Job(trans_name)
        job.add_args(
            "--input", input_file,
            "--output", output_file
        )
        job.add_inputs(input_file)
        job.add_outputs(output_file, stage_out=True)

        wf.add_jobs(job)

    # --- Properties ---
    # Optional: Set Pegasus properties if needed
    # props = Properties()
    # props["pegasus.monitord.encoding"] = "json"
    # props.write()
    # wf.add_properties(props)

    return wf