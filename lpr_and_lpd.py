import sys
import gi
import time

gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

def bus_call(bus, message, loop):
    """Handle messages on the GStreamer bus."""
    msg_type = message.type
    if msg_type == Gst.MessageType.EOS:
        print("End of stream")
        loop.quit()
    elif msg_type == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"Error: {err}, {debug}")
        loop.quit()
    return True

def on_pad_added(demuxer, pad, parser):
    """Callback for dynamically linking qtdemux pad."""
    caps = pad.query_caps(None)
    structure = caps.get_structure(0)
    media_type = structure.get_name()
    if "video" in media_type:
        pad.link(parser.get_static_pad("sink"))

def create_pipeline(input_file, output_file):
    """Create the GStreamer pipeline manually and link elements."""
    pipeline = Gst.Pipeline.new("deepstream-pipeline")
    
    source = Gst.ElementFactory.make("filesrc", "file-source")
    source.set_property("location", input_file)
    
    demuxer = Gst.ElementFactory.make("qtdemux", "mp4-demuxer")
    parser = Gst.ElementFactory.make("h264parse", "h264-parser")
    decoder = Gst.ElementFactory.make("nvv4l2decoder", "video-decoder")
    
    streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")
    streammux.set_property("batch-size", 1)
    streammux.set_property("width", 1280)
    streammux.set_property("height", 720)
    
    pgie = Gst.ElementFactory.make("nvinfer", "primary-infer")
    pgie.set_property("config-file-path", "../../../configs/nvinfer/trafficcamnet_tao/pgie_trafficcamnet_config.txt")
    pgie.set_property("unique-id", 1)
    
    sgie1 = Gst.ElementFactory.make("nvinfer", "secondary-infer-1")
    sgie1.set_property("config-file-path", "../../../configs/nvinfer/LPD_us_tao/sgie_lpd_DetectNet2_us.txt")
    sgie1.set_property("unique-id", 2)
    sgie1.set_property("process-mode", 2)
    
    sgie2 = Gst.ElementFactory.make("nvinfer", "secondary-infer-2")
    sgie2.set_property("config-file-path", "../../../configs/nvinfer/lpr_us_tao/sgie_lpr_us_config.txt")
    sgie2.set_property("unique-id", 3)
    sgie2.set_property("process-mode", 2)
    
    converter = Gst.ElementFactory.make("nvvideoconvert", "video-converter")
    osd = Gst.ElementFactory.make("nvdsosd", "on-screen-display")
    encoder = Gst.ElementFactory.make("nvv4l2h264enc", "h264-encoder")
    parser_out = Gst.ElementFactory.make("h264parse", "h264-parser-out")
    muxer = Gst.ElementFactory.make("qtmux", "mp4-muxer")
    sink = Gst.ElementFactory.make("filesink", "file-sink")
    sink.set_property("location", output_file)
    
    if not pipeline or not source or not demuxer or not parser or not decoder or not streammux or not pgie or not sgie1 or not sgie2 or not converter or not osd or not encoder or not parser_out or not muxer or not sink:
        print("Failed to create elements")
        sys.exit(1)
    
    pipeline.add(source)
    pipeline.add(demuxer)
    pipeline.add(parser)
    pipeline.add(decoder)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(sgie1)
    pipeline.add(sgie2)
    pipeline.add(converter)
    pipeline.add(osd)
    pipeline.add(encoder)
    pipeline.add(parser_out)
    pipeline.add(muxer)
    pipeline.add(sink)
    
    source.link(demuxer)
    demuxer.connect("pad-added", on_pad_added, parser)
    parser.link(decoder)
    
    sinkpad = streammux.get_request_pad("sink_0")
    srcpad = decoder.get_static_pad("src")
    if not sinkpad or not srcpad:
        print("Failed to get sink or src pad")
        sys.exit(1)
    srcpad.link(sinkpad)
    
    streammux.link(pgie)
    pgie.link(sgie1)
    sgie1.link(sgie2)
    sgie2.link(converter)
    converter.link(osd)
    osd.link(encoder)
    encoder.link(parser_out)
    parser_out.link(muxer)
    muxer.link(sink)
    
    return pipeline

def main():
    if len(sys.argv) != 3:
        print("Usage: python deepstream_lpr.py <input_mp4> <output_mp4>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    loop = GLib.MainLoop()
    pipeline = create_pipeline(input_file, output_file)

    if not pipeline:
        print("Failed to create pipeline")
        sys.exit(1)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    pipeline.set_state(Gst.State.PLAYING)
    print("Pipeline running...")

    try:
        loop.run()
    except KeyboardInterrupt:
        print("Stopping pipeline...")
        pipeline.set_state(Gst.State.NULL)
        sys.exit(0)

if __name__ == "__main__":
    main()
