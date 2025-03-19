import tensorrt as trt

TRT_LOGGER = trt.Logger(trt.Logger.WARNING)

def build_engine_from_etlt(etlt_model_path, tlt_key):
    with trt.Builder(TRT_LOGGER) as builder, \
         builder.create_network(1) as network, \
         trt.OnnxParser(network, TRT_LOGGER) as parser, \
         builder.create_builder_config() as config:

        # config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB workspace
        config.set_flag(trt.BuilderFlag.FP16)  # Enable FP16 mode

        with open(etlt_model_path, "rb") as f:
            if not parser.parse(f.read()):
                print("Failed to parse the ETLT model!")
                for error in range(parser.num_errors):
                    print(parser.get_error(error))
                return None

        serialized_engine = builder.build_serialized_network(network, config)
        if serialized_engine is None:
            print("Failed to build serialized network!")
            return None

        with trt.Runtime(TRT_LOGGER) as runtime:
            engine = runtime.deserialize_cuda_engine(serialized_engine)
            return engine

engine = build_engine_from_etlt(
    "/opt/nvidia/deepstream/deepstream-7.1/samples/models/LP/LPR/us_lprnet_baseline18_deployable.etlt",
    "nvidia_tlt"
)

if engine:
    with open("number_plate_detector.engine", "wb") as f:
        f.write(engine.serialize())
    print("Engine file successfully created!")
else:
    print("Engine creation failed!")
