import sys
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib, GObject

def bus_call(bus, message, loop):
    """Handles messages from the GStreamer pipeline."""
    if message.type == Gst.MessageType.EOS:
        print("End of stream")
        loop.quit()
    elif message.type == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"Error: {err}, {debug}")
        loop.quit()
    return True

def demux_callback(demuxer, pad, data):
    """Dynamically links qtdemux pad to h264parse."""
    caps = pad.query_caps(None)
    if not caps or caps.get_size() == 0:
        print("No caps available on demux pad")
        return

    structure = caps.get_structure(0)
    if not structure:
        print("No structure available in caps")
        return

    media_type = structure.get_name()
    if media_type.startswith("video"):
        print("Linking demux to parser")
        sink_pad = data.get_static_pad("sink")
        if sink_pad:
            pad.link(sink_pad)

def stop_pipeline(pipeline):
    pipeline.set_state(Gst.State.NULL)
    print("Pipeline stopped")

def main(video_path):
    Gst.init(None)

    pipeline = Gst.Pipeline()

    source = Gst.ElementFactory.make("filesrc", "file-source")
    demux = Gst.ElementFactory.make("qtdemux", "demux")
    parser = Gst.ElementFactory.make("h264parse", "parser")
    decoder = Gst.ElementFactory.make("nvv4l2decoder", "decoder")
    streammux = Gst.ElementFactory.make("nvstreammux", "stream-mux")
    nvinfer = Gst.ElementFactory.make("nvinfer", "primary-inference")
    tracker = Gst.ElementFactory.make("nvtracker", "tracker")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "nvvidconv")
    capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
    encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
    parser_out = Gst.ElementFactory.make("h264parse", "parser_out")
    muxer = Gst.ElementFactory.make("qtmux", "muxer")
    sink = Gst.ElementFactory.make("filesink", "file-sink")

    if not all([source, demux, parser, decoder, streammux, nvinfer, tracker, nvvidconv, capsfilter, encoder, parser_out, muxer, sink]):
        print("Failed to create elements")
        return

    source.set_property("location", video_path)
    streammux.set_property("batch-size", 1)
    streammux.set_property("width", 1280)
    streammux.set_property("height", 720)
    streammux.set_property("live-source", 0)
    streammux.set_property("nvbuf-memory-type", 0)

    nvinfer.set_property("config-file-path", "dstest1_pgie_config.txt")
    sink.set_property("location", "nvdeepsort_tracker_test_1.mp4")

    capsfilter.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=NV12, width=1280, height=720"))

    tracker.set_property("ll-lib-file", "/opt/nvidia/deepstream/deepstream-7.1/lib/libnvds_nvmultiobjecttracker.so")
    tracker.set_property("ll-config-file", "/opt/nvidia/deepstream/deepstream-7.1/samples/configs/deepstream-app/config_tracker_NvSORT.yml")

    pipeline.add(source)
    pipeline.add(demux)
    pipeline.add(parser)
    pipeline.add(decoder)
    pipeline.add(streammux)
    pipeline.add(nvinfer)
    pipeline.add(tracker)
    pipeline.add(nvvidconv)
    pipeline.add(capsfilter)
    pipeline.add(encoder)
    pipeline.add(parser_out)
    pipeline.add(muxer)
    pipeline.add(sink)

    source.link(demux)
    parser.link(decoder)
    streammux.link(nvinfer)
    nvinfer.link(tracker)
    tracker.link(nvvidconv)
    nvvidconv.link(capsfilter)
    capsfilter.link(encoder)
    encoder.link(parser_out)
    parser_out.link(muxer)
    muxer.link(sink)

    demux.connect("pad-added", demux_callback, parser)

    sinkpad = streammux.get_request_pad("sink_0")
    if not sinkpad:
        print("Unable to create sink pad in nvstreammux")
        return

    decoder_src_pad = decoder.get_static_pad("src")
    if decoder_src_pad:
        decoder_src_pad.link(sinkpad)

    bus = pipeline.get_bus()
    loop = GLib.MainLoop()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except KeyboardInterrupt:
        stop_pipeline(pipeline)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_video>")
        sys.exit(1)

    main(sys.argv[1])
