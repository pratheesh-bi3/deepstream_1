import sys
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib, GObject

MUXER_BATCH_TIMEOUT_USEC = 4000000
def decodebin_pad_added(decodebin, pad, streammux):
    print("Inside decodebin_pad_added")
    caps = pad.query_caps(None)
    caps_str = caps.to_string() if caps else "Unknown"
    print(f"Pad caps: {caps_str}")

    if caps and caps_str.startswith("video/x-raw"):
        sinkpad = streammux.get_request_pad("sink_0")
        if not sinkpad:
            sys.stderr.write("Error: Unable to get sink pad from streammux\n")
            return

        if pad.link(sinkpad) != Gst.PadLinkReturn.OK:
            sys.stderr.write("Error: Failed to link decodebin pad to streammux\n")
def main(args):
    if len(args) != 2:
        sys.stderr.write("Usage: %s <media file>\n" % args[0])
        sys.exit(1)

    Gst.init(None)

    print("Creating Pipeline\n")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write("Failed to create Pipeline\n")
        return

    source = Gst.ElementFactory.make("filesrc", "file-source")
    decodebin = Gst.ElementFactory.make("decodebin", "decoder")
    streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "converter")
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    encoder = Gst.ElementFactory.make("nvv4l2h264enc", "h264-encoder")
    parser = Gst.ElementFactory.make("h264parse", "h264-parser")
    muxer = Gst.ElementFactory.make("qtmux", "muxer")
    sink = Gst.ElementFactory.make("filesink", "file-output")

    if not all([source, decodebin, streammux, pgie, nvvidconv, nvosd, encoder, parser, muxer, sink]):
        sys.stderr.write("Failed to create one or more elements\n")
        return
    source.set_property("location", args[1])
    streammux.set_property("batch-size", 1)
    streammux.set_property("width", 1920)
    streammux.set_property("height", 1080)
    streammux.set_property("batched-push-timeout", MUXER_BATCH_TIMEOUT_USEC)
    pgie.set_property("config-file-path", "dstest1_pgie_config.txt")

    sink.set_property("location", "with_out_tracking.mp4")
    sink.set_property("sync", False)

    pipeline.add(source)
    pipeline.add(decodebin)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(encoder)
    pipeline.add(parser)
    pipeline.add(muxer)
    pipeline.add(sink)

    # Link static elements
    source.link(decodebin)
    streammux.link(pgie)
    pgie.link(nvvidconv)
    nvvidconv.link(nvosd)
    nvosd.link(encoder)
    encoder.link(parser)
    parser.link(muxer)
    muxer.link(sink)

    decodebin.connect("pad-added", decodebin_pad_added, streammux)

    print("Starting pipeline, saving output to hellow_output.mp4\n")
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        pass

    print("Stopping pipeline\n")
    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
