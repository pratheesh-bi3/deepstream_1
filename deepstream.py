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
    structure = caps.get_structure(0)
    media_type = structure.get_name()

    if media_type.startswith("video"):
        print("Linking demux to parser")
        pad.link(data.get_static_pad("sink"))

def main(video_path):
    Gst.init(None)

    # Create pipeline
    pipeline = Gst.Pipeline()

    # Create elements
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

    # Set properties
    source.set_property("location", video_path)
    streammux.set_property("batch-size", 1)
    streammux.set_property("width", 1280)
    streammux.set_property("height", 720)
    streammux.set_property("live-source", 0)
    streammux.set_property("nvbuf-memory-type", 0)  # Ensure correct memory type

    nvinfer.set_property("config-file-path", "dstest1_pgie_config.txt")
    sink.set_property("location", "output.mp4")

    capsfilter.set_property("caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=NV12"))

    # Set tracker properties (Ensure library exists)
    tracker.set_property("ll-lib-file", "/opt/nvidia/deepstream/deepstream-7.1/lib/libnvds_mot_klt.so")
    tracker.set_property("ll-config-file", "config_tracker_NvDCF_perf.yml")

    # Add elements to pipeline
    pipeline.add_many(source, demux, parser, decoder, streammux, nvinfer, tracker, nvvidconv, capsfilter, encoder, parser_out, muxer, sink)

    # Link static elements
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

    # Handle dynamic linking of demux output
    demux.connect("pad-added", demux_callback, parser)

    # Create streammux pad dynamically
    sinkpad = streammux.request_pad_simple("sink_0")
    if not sinkpad:
        print("Unable to create sink pad in nvstreammux")
        return

    decoder_src_pad = decoder.get_static_pad("src")
    if not decoder_src_pad:
        print("Unable to get decoder src pad")
        return

    decoder_src_pad.link(sinkpad)

    # Message bus
    bus = pipeline.get_bus()
    loop = GLib.MainLoop()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # Start pipeline
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass

    # Cleanup
    pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input_video>")
        sys.exit(1)

    main(sys.argv[1])
