import tensorrt as trt

TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

def build_engine_from_etlt(etlt_model_path, tlt_key):
    with trt.Builder(TRT_LOGGER) as builder, \
         builder.create_network(1) as network, \
         trt.OnnxParser(network, TRT_LOGGER) as parser, \
         builder.create_builder_config() as config:  # Use config for TensorRT 8+

        # config.max_workspace_size = 1 << 30  # 1GB workspace size
        config.set_flag(trt.BuilderFlag.FP16)  # Enable FP16 mode

        with open(etlt_model_path, "rb") as f:
            parser.parse(f.read())

        engine = builder.build_engine(network, config)
        return engine

engine = build_engine_from_etlt(
    "/opt/nvidia/deepstream/deepstream-7.1/samples/models/LP/LPR/us_lprnet_baseline18_deployable.etlt",
    "nvidia_tlt"
)

with open("number_plate_detector.engine", "wb") as f:
    f.write(engine.serialize())

print("Engine file successfully created!")
