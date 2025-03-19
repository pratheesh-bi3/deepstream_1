import tensorrt as trt

TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

def build_engine_from_etlt(etlt_model_path, tlt_key):
    with trt.Builder(TRT_LOGGER) as builder, \
         builder.create_network(1) as network, \
         trt.OnnxParser(network, TRT_LOGGER) as parser:

        builder.max_workspace_size = 1 << 30  # 1GB
        builder.fp16_mode = True  # Use FP16 for better performance

        with open(etlt_model_path, "rb") as f:
            parser.parse(f.read())

        engine = builder.build_cuda_engine(network)
        return engine

engine = build_engine_from_etlt("/opt/nvidia/deepstream/deepstream-7.1/samples/models/LP/LPR/us_lprnet_baseline18_deployable.etlt", "nvidia_tlt")

with open("number_plate_detector.engine", "wb") as f:
    f.write(engine.serialize())
