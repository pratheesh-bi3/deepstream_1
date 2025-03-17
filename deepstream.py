import sys
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import pyds

def osd_sink_pad_buffer_probe(pad, info, u_data):
    """Metadata extraction probe function."""
    frame_number = 0
    num_rects = 0
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return Gst.PadProbeReturn.OK

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break
        frame_number = frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        print(f"Frame Number={frame_number} Number of Objects={num_rects}")
        try:
            l_frame = l_frame.next
        except StopIteration:
            break
    return Gst.PadProbeReturn.OK

def main(args):
    if len(args) != 2:
        print("Usage: python deepstream_app.py <video_file>")
        sys.exit(1)

    Gst.init(None)
    pipeline = Gst.parse_launch(
        f"filesrc location={args[1]} ! decodebin ! videoconvert ! video/x-raw,format=NV12 ! \
        nvvideoconvert ! m.sink_0 nvstreammux name=m batch-size=1 width=1920 height=1080 ! \
        nvinfer config-file-path=dstest1_pgie_config.txt ! nvdsosd ! nvv4l2h264enc ! \
        h264parse ! qtmux ! filesink location=hellow_output.mp4"
    )

    if not pipeline:
        print("Failed to create pipeline")
        sys.exit(1)

    osd = pipeline.get_by_name("nvdsosd0")
    if osd:
        osd_sink_pad = osd.get_static_pad("sink")
        osd_sink_pad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, None)

    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", lambda bus, msg: loop.quit() if msg.type == Gst.MessageType.EOS else None)

    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main(sys.argv)
